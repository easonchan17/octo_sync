from typing import List
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Site, CompTeam, CompSyncFlag
from .comp_level_synchronizer import CompLevelSynchronizer


class CompTeamSynchronizer(CompLevelSynchronizer):
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
                },
                where=(
                    (CompTeam.team_name != insert_stmt.excluded.team_name) |
                    (CompTeam.comp_name != insert_stmt.excluded.comp_name)
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} {comp_name} {season} teams completed. upserted: {upserted_count}")

            self.add_sync_flag(session, comp_code, season, CompSyncFlag.TEAMS.value)
            self.logger.info(f"Mark {site.name} {comp_name} {season} teams as synced")
