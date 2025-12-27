from typing import List
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Site, CompSyncState
from ..base_synchronizer import BaseSynchronizer


class CompLevelSynchronizer(BaseSynchronizer):
    def get_sync_targets(
        self, site: Site, comp_code: str, min_season: int, max_season: int, flag: int
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

    def add_sync_flag(self, session, comp_code: str, season: int, flag: int) -> None:
        insert_flag_stmt = insert(CompSyncState).values(
            season=season,
            comp_code=comp_code,
            sync_flags=flag
        )
        insert_flag_stmt = insert_flag_stmt.on_conflict_do_update(
            index_elements=['season', 'comp_code'],
            set_={
                'sync_flags': CompSyncState.sync_flags.op('|')(flag),
                'updated_at': func.now()
            }
        )
        session.execute(insert_flag_stmt)
