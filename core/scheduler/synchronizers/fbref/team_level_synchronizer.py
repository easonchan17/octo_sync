from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from sqlalchemy import func, and_, or_, update
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Site, CompTeam, MatchStatsSyncState
from ..base_synchronizer import BaseSynchronizer


class TeamLevelSynchronizer(BaseSynchronizer):
    def get_pending_tasks(
        self,
        site: Site,
        min_season: int,
        max_season: int,
        flag: int,
        comp_code: Optional[str] = None,
        team_code: Optional[str] = None
    ) -> List[Any]:
        if not comp_code and not team_code:
            raise ValueError("Either comp_code or team_code must be provided")

        with self.db.get_session(site.get_namespace()) as session:
            query = session.query(
                CompTeam.season,
                CompTeam.team_name,
                CompTeam.team_code
            ).outerjoin(
                MatchStatsSyncState,
                and_(
                    MatchStatsSyncState.team_code == CompTeam.team_code,
                    MatchStatsSyncState.season == CompTeam.season
                )
            ).filter(
                CompTeam.season >= min_season,
                CompTeam.season <= max_season,
                or_(
                    MatchStatsSyncState.team_code.is_(None),
                    (MatchStatsSyncState.sync_flags.op('&')(flag)) != flag
                )
            )

            if comp_code:
                query = query.filter(CompTeam.comp_code == comp_code)
            if team_code:
                query = query.filter(CompTeam.team_code == team_code)

            return query.order_by(CompTeam.season, CompTeam.team_code).all()

    def add_sync_flag(
        self,
        session: Session,
        team_code: str,
        season: int,
        flag: int
    ) -> bool:
        insert_flag_stmt = insert(MatchStatsSyncState).values(
            team_code=team_code,
            season=season,
            sync_flags=flag
        )
        insert_flag_stmt = insert_flag_stmt.on_conflict_do_update(
            index_elements=['team_code', 'season'],
            set_={
                'sync_flags': MatchStatsSyncState.sync_flags.op('|')(flag),
                'updated_at': func.now()
            }
        )
        session.execute(insert_flag_stmt)

    def update_sync_state(
        self,
        session,
        team_code: str,
        season: int,
        values: Dict[str, Any]
    ) -> bool:
        if not values:
            raise ValueError("Values cannot be empty")

        valid_columns = {col.key for col in MatchStatsSyncState.columns}
        pending_values = {key: val for key, val in values.items() if key in valid_columns}

        if not pending_values:
            raise ValueError("No valid columns found to update")

        update_stmt = update(MatchStatsSyncState).where(
            and_(
                MatchStatsSyncState.team_code == team_code,
                MatchStatsSyncState.season == season
            )
        ).values(
            pending_values
        ).execution_options(synchronize_session="fetch")

        result = session.execute(update_stmt)
        return result.rowcount > 0