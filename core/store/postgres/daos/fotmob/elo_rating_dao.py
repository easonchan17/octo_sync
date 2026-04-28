from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.fotmob.elo_rating import EloRating, EloRatingBuildLog
from core.store.postgres.models.fotmob.fixture import Fixture
from ..base_dao import BaseDao


class EloRatingDao(BaseDao):
    def get_latest_build_log(self) -> Optional[Any]:
        with self.db.get_session() as session:
            return (
                session.query(
                    EloRatingBuildLog.checkpoint,
                    EloRatingBuildLog.next_build_at,
                    EloRatingBuildLog.created_at,
                )
                .order_by(EloRatingBuildLog.checkpoint.desc())
                .first()
            )

    def get_rebuild_time(self, built_time: datetime, checkpoint: datetime, min_season: int) -> Optional[datetime]:
        with self.db.get_session() as session:
            return (
                session.query(func.min(Fixture.kickoff_time))
                .filter(
                    Fixture.updated_at > built_time,
                    Fixture.kickoff_time <= checkpoint,
                    Fixture.season >= min_season,
                )
                .scalar()
            )

    def get_pending_build_items(self, from_checkpoint: datetime, checkpoint: datetime, min_season: int) -> List[Any]:
        with self.db.get_session() as session:
            return (
                session.query(
                    Fixture.match_id,
                    Fixture.home_id,
                    Fixture.away_id,
                    Fixture.kickoff_time,
                    Fixture.season,
                    Fixture.home_score,
                    Fixture.away_score,
                    Fixture.match_status,
                )
                .filter(
                    Fixture.kickoff_time >= from_checkpoint,
                    Fixture.kickoff_time <= checkpoint,
                    Fixture.season >= min_season,
                )
                .order_by(Fixture.kickoff_time.asc())
                .all()
            )

    def get_prior_states(self, checkpoint: datetime) -> List[Any]:
        with self.db.get_session() as session:
            return (
                session.query(
                    EloRating.team_id,
                    EloRating.post_rating,
                    EloRating.season,
                    EloRating.game_count,
                )
                .filter(EloRating.kickoff_time < checkpoint)
                .distinct(EloRating.team_id)
                .order_by(
                    EloRating.team_id,
                    EloRating.kickoff_time.desc()
                )
                .all()
            )

    def add_build_log(self, from_checkpoint: datetime, checkpoint: datetime, match_count: int, interval: Optional[timedelta]) -> None:
        now = datetime.now(timezone.utc)
        with self.db.get_session() as session:
            session.add(EloRatingBuildLog(
                from_checkpoint=from_checkpoint,
                checkpoint=checkpoint,
                next_build_at=now + interval if interval is not None else None,
                match_count=match_count,
            ))

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
