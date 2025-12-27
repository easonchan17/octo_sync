from typing import List
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Site, CompTeam, CompTeamSyncState, CompTeamSyncFlag
from ..base_synchronizer import BaseSynchronizer


class CompTeamSynchronizer(BaseSynchronizer):
    def get_sync_targets(
        self, site: Site, comp_code: str, min_season: int, max_season: int, flag: int
    ) -> List[int]:
        with self.db.get_session(site.get_namespace()) as session:
            synced_seasons = {
                row[0] for row in session.query(CompTeamSyncState.season).filter(
                    CompTeamSyncState.comp_code == comp_code,
                    CompTeamSyncState.season >= min_season,
                    CompTeamSyncState.season <= max_season,
                    (CompTeamSyncState.sync_flags.op('&')(flag)) == flag
                ).all()
            }
            all_seasons = set(range(min_season, max_season + 1))
            return sorted(all_seasons - synced_seasons)

    def sync(self, site: Site, comp_code: str, comp_name: str, season: int, teams: List[CompTeam]) -> None:
        if not teams:
            self.logger.warning(f"No teams to sync for {site.name}")
            return

        team_dict = self.to_dict(
            teams,
            ['season', 'comp_name', 'comp_code', 'team_name', 'team_code'],
            ['season', 'comp_code', 'team_code']
        )

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(CompTeam).values(list(team_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['season', 'comp_code', 'team_code'],
                set_={
                    'team_name': insert_stmt.excluded.team_name,
                    'comp_name': insert_stmt.excluded.comp_name,
                    'updated_at': func.now()
                }
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} {comp_name} {season} teams completed. upserted: {upserted_count}")

            insert_flag_stmt = insert(CompTeamSyncState).values(
                season=season,
                comp_code=comp_code,
                sync_flags=CompTeamSyncFlag.TEAMS.value
            )
            insert_flag_stmt = insert_flag_stmt.on_conflict_do_update(
                index_elements=['season', 'comp_code'],
                set_={
                    'sync_flags': CompTeamSyncState.sync_flags.op('|')(CompTeamSyncFlag.TEAMS.value),
                    'updated_at': func.now()
                }
            )
            session.execute(insert_flag_stmt)
            self.logger.info(f"Mark {site.name} {comp_name} {season} teams as synced")
