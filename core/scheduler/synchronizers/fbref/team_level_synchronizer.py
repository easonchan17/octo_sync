from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Any, Optional
from sqlalchemy import func, and_, or_
from sqlalchemy.dialects.postgresql import insert, JSONB
from core.store.postgres.models import Site, CompTeam, MatchStatsSyncState
from core.store.postgres.models.fbref.match_stats_sync_state import MatchStatsSyncFlag
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

    def update_sync_state(
        self,
        session: Session,
        team_code: str,
        season: int,
        flag: MatchStatsSyncFlag,
        last_synced_time: datetime
    ) -> None:
        flag_value = flag.value
        flag_name = flag.name.lower()
        new_state_times = func.jsonb_build_object(flag_name, last_synced_time)

        insert_stmt = insert(MatchStatsSyncState).values(
            team_code=team_code,
            season=season,
            sync_flags=flag_value,
            last_synced_times=new_state_times
        )
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[MatchStatsSyncState.team_code.key, MatchStatsSyncState.season.key],
            set_={
                MatchStatsSyncState.sync_flags.key: MatchStatsSyncState.sync_flags.op('|')(flag_value),
                MatchStatsSyncState.last_synced_times.key: func.coalesce(
                    MatchStatsSyncState.last_synced_times,
                    func.cast('{}', JSONB)
                ).op('||')(new_state_times),
                MatchStatsSyncState.updated_at.key: func.now()
            }
        )
        session.execute(insert_stmt)

    def update_latest_match_time(
        self,
        session: Session,
        team_code: str,
        season: int,
        latest_match_time: datetime
    ) -> None:
        insert_stmt = insert(MatchStatsSyncState).values(
            team_code=team_code,
            season=season,
            latest_match_time=latest_match_time
        )
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[MatchStatsSyncState.team_code.key, MatchStatsSyncState.season.key],
            set_={
                MatchStatsSyncState.latest_match_time.key: latest_match_time,
                MatchStatsSyncState.updated_at.key: func.now()
            }
        )
        session.execute(insert_stmt)