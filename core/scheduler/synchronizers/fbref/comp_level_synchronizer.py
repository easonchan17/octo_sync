from datetime import datetime
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB, insert
from ..base_synchronizer import BaseSynchronizer
from core.store.postgres.models import Site, CompSyncState
from core.store.postgres.models.fbref.comp_sync_state import CompSyncFlag

class CompLevelSynchronizer(BaseSynchronizer):
    def get_pending_tasks(
        self,
        site: Site,
        comp_code: str,
        min_season: int,
        max_season: int,
        flag: int
    ) -> List[int]:
        with self.db.get_session(site.get_namespace()) as session:
            synced_seasons = {
                row[0] for row in session.query(CompSyncState.season).filter(
                    CompSyncState.comp_code == comp_code,
                    CompSyncState.season >= min_season,
                    CompSyncState.season <= max_season,
                    (CompSyncState.sync_flags.op('&')(flag)) == flag
                ).all()
            }
            all_seasons = set(range(min_season, max_season + 1))
            return sorted(all_seasons - synced_seasons)

    def update_sync_state(
        self,
        session: Session,
        comp_code: str,
        season: int,
        flag: CompSyncFlag,
        last_synced_time: Optional[datetime] = None
    ) -> None:
        flag_value = flag.value

        insert_values = {
            CompSyncState.comp_code.key: comp_code,
            CompSyncState.season.key: season,
            CompSyncState.sync_flags.key: flag_value
        }

        update_set = {
            CompSyncState.sync_flags.key: CompSyncState.sync_flags.op('|')(flag_value),
            CompSyncState.updated_at.key: func.now()
        }

        if last_synced_time is not None:
            new_state_times = func.jsonb_build_object(flag.name.lower(), last_synced_time)
            insert_values[CompSyncState.last_synced_times.key] = new_state_times

            update_set[CompSyncState.last_synced_times.key] = func.coalesce(
                CompSyncState.last_synced_times,
                func.cast('{}', JSONB)
            ).op('||')(new_state_times)

        insert_stmt = insert(CompSyncState).values(insert_values)
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[CompSyncState.season.key, CompSyncState.comp_code.key],
            set_=update_set
        )

        session.execute(insert_stmt)