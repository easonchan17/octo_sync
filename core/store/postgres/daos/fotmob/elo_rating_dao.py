from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple
from sqlalchemy import and_, func, desc
from sqlalchemy.engine import Row
from sqlalchemy.dialects.postgresql import insert
from core.types.enums import MatchStatus
from core.store.postgres.models.fotmob.elo_rating import EloRating, EloRatingProgress
from core.store.postgres.models.fotmob.fixture import Fixture
from ..base_dao import BaseDao


class EloRatingDao(BaseDao):
    def get_pending_build_items(self, league_ids: List[int]) -> List[Row]:
        with self.db.get_session() as session:
            return (
                session.query(
                    EloRatingProgress.league_id,
                    EloRatingProgress.season
                )
                .filter(EloRatingProgress.league_id.in_(league_ids))
                .all()
            )

    def get_pending_fixtures(self, league_id: int, season: int) -> List[Row]:
        finished_statuses = MatchStatus.natural_finals()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        with self.db.get_session() as session:
            return (
                session.query(
                    Fixture.match_id,
                    Fixture.home_id,
                    Fixture.away_id,
                    Fixture.kickoff_time,
                    Fixture.season,
                    Fixture.home_score,
                    Fixture.away_score
                )
                .outerjoin(
                    EloRating,
                    and_(EloRating.match_id == Fixture.match_id, EloRating.team_id == Fixture.home_id)
                )
                .filter(
                    Fixture.league_id == league_id,
                    Fixture.season == season,
                    Fixture.match_status.in_(finished_statuses),
                    Fixture.home_score.isnot(None),
                    Fixture.away_score.isnot(None),
                    Fixture.kickoff_time < cutoff,
                    EloRating.id.is_(None)
                )
                .order_by(Fixture.kickoff_time.asc(), Fixture.match_id.asc())
                .all()
            )

    def get_elo_snapshot(self, as_of: datetime) -> Tuple[Dict[int, float], Dict[int, int], Dict[int, int]]:
        with self.db.get_session() as session:
            subquery = (
                session.query(
                    EloRating.team_id,
                    EloRating.post_rating,
                    EloRating.season,
                    func.count().over(partition_by=EloRating.team_id).label('total_count'),
                    func.row_number().over(
                        partition_by=EloRating.team_id,
                        order_by=(desc(EloRating.kickoff_time), desc(EloRating.id))
                    ).label('rn')
                )
                .filter(EloRating.kickoff_time < as_of)
                .subquery()
            )

            latest_records = session.query(subquery).filter(subquery.c.rn == 1).all()

            ratings: Dict[int, float] = {}
            seasons: Dict[int, int] = {}
            game_counts: Dict[int, int] = {}
            for row in latest_records:
                ratings[row.team_id] = float(row.post_rating)
                seasons[row.team_id] = row.season
                game_counts[row.team_id] = row.total_count

            return ratings, seasons, game_counts

    def sync_built_data(self, records: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(EloRating).values(records)
            assignment, where_clause = self.build_upsert_clauses(
                EloRating,
                insert_stmt,
                {
                    EloRating.id.key,
                    EloRating.created_at.key,
                    EloRating.match_id.key,
                    EloRating.team_id.key,
                    EloRating.updated_at.key
                }
            )

            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[EloRating.team_id.key, EloRating.match_id.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(upsert_stmt)
            self.logger.info(f"Upserted {result.rowcount} elo ratings")
