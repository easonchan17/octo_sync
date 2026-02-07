from datetime import datetime
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from core.types.enums import UpsertStrategy
from sqlalchemy.dialects.postgresql import insert
from typing import List, Dict, Any, Optional, Tuple
from core.domain.calculators import EloRatingCalculator
from core.store.postgres.models import Site, EloRating, MatchResult, Status
from ..base_synchronizer import BaseSynchronizer
from ..common import SysValSynchronizer

class EloRatingSynchronizer(BaseSynchronizer):
    ELO_IMPACT_TIME_KEY = 'elo_impact_time'

    def __init__(self) -> None:
        super().__init__()
        self.sys_val_synchronizer = SysValSynchronizer()

    def lock_impact_time(self, session: Session) -> Optional[datetime]:
        return self.sys_val_synchronizer.get_val(self.ELO_IMPACT_TIME_KEY, session, for_update=True)

    def set_impact_time(self, session: Session, impact_time: datetime, strategy: UpsertStrategy) -> bool:
        if not impact_time:
            return False

        return self.sys_val_synchronizer.set_val(self.ELO_IMPACT_TIME_KEY, impact_time, strategy, session)

    def sync(self, site: Site) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            impact_time = self.lock_impact_time(session)
            if not impact_time:
                self.logger.warning(f"No impact time found. Skipping Elo rating sync")
                return

            matches = self._get_impact_matches(session, impact_time)
            if not matches:
                self.logger.warning(f"No pending match results found. Skipping Elo rating sync")
                return

            self.logger.info(f"Found {len(matches)} match results to calculate Elo ratings since {impact_time}")

            ratings, seasons, game_counts = self._get_elo_snapshot(session, impact_time)
            elo_ratings = EloRatingCalculator(ratings, seasons, game_counts, matches).calculate()

            if not elo_ratings:
                self.logger.warning(f"No Elo ratings calculated. Skipping Elo rating sync")
                return

            self._upsert_elo_ratings(session, elo_ratings)
            self.set_impact_time(session, matches[-1].kickoff_time, UpsertStrategy.OVERWRITE)

    def _get_impact_matches(self, session, impact_time: datetime) -> List[MatchResult]:
        return session.query(MatchResult).filter(
            MatchResult.kickoff_time >= impact_time,
            MatchResult.status.op('&')(Status.ACTIVE.value) == Status.ACTIVE.value
        ).order_by(MatchResult.kickoff_time.asc()).all()

    def _get_elo_snapshot(self, session, as_of: datetime) -> Tuple[Dict[str, float], Dict[str, int], Dict[str, int]]:
        subquery = (
            session.query(
                EloRating.team_code,
                EloRating.post_rating,
                EloRating.season,
                func.count().over(
                    partition_by=EloRating.team_code
                ).label('total_count'),
                func.row_number().over(
                    partition_by=EloRating.team_code,
                    order_by=(desc(EloRating.kickoff_time), desc(EloRating.id))
                ).label('rn')
            )
            .filter(EloRating.kickoff_time < as_of)
            .subquery()
        )

        latest_records = session.query(subquery).filter(subquery.c.rn == 1).all()

        ratings = {}
        seasons = {}
        game_counts = {}

        for row in latest_records:
            ratings[row.team_code] = float(row.post_rating)
            seasons[row.team_code] = row.season
            game_counts[row.team_code] = row.total_count

        return ratings, seasons, game_counts

    def _upsert_elo_ratings(self, session, elo_ratings: List[Dict[str, Any]]) -> None:
        insert_stmt = insert(EloRating).values(elo_ratings)
        assignment, where_clause = self.build_upsert_clauses(
            EloRating,
            insert_stmt,
            {
                EloRating.id.key,
                EloRating.created_at.key,
                EloRating.match_code.key,
                EloRating.team_code.key,
                EloRating.updated_at.key
            }
        )

        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[EloRating.team_code.key, EloRating.match_code.key],
            set_=assignment,
            where=where_clause
        )
        result = session.execute(insert_stmt)
        self.logger.info(f"Upserted {result.rowcount} elo ratings")