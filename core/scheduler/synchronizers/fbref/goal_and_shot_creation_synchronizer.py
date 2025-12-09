from typing import List, Any
from sqlalchemy import func, update, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    GoalAndShotCreation, Site, Status, Club, ClubSyncState, ClubSyncFlag
)
from ..base_synchronizer import BaseSynchronizer

class GoalAndShotCreationSynchronizer(BaseSynchronizer):
    def sync(self, site: Site, club: Club, season: int, goal_and_shot_creations: List[GoalAndShotCreation]) -> None:
        season_range = f"{season}-{season+1}"
        if not goal_and_shot_creations:
            self.logger.warning(f"No {club.name} {season_range} goal and shot creations to sync from {site.name}")
            return

        goal_and_shot_creation_dict = self.to_dict(
            goal_and_shot_creations,
            ['match_code', 'team_code', 'shot_creating_actions', 'sca_passes_live', 'sca_passes_dead', 'sca_take_ons',
             'sca_shots', 'sca_fouled', 'sca_defense', 'goal_creating_actions', 'gca_passes_live', 'gca_passes_dead', 'gca_take_ons',
             'gca_shots', 'gca_fouled', 'gca_defense'],
            ['match_code', 'team_code']
        )

        with self.postgresql_manager.get_session(site.get_namespace()) as session:
            insert_stmt = insert(GoalAndShotCreation).values(list(goal_and_shot_creation_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_code', 'team_code'],
                set_={
                    'shot_creating_actions': insert_stmt.excluded.shot_creating_actions,
                    'sca_passes_live': insert_stmt.excluded.sca_passes_live,
                    'sca_passes_dead': insert_stmt.excluded.sca_passes_dead,
                    'sca_take_ons': insert_stmt.excluded.sca_take_ons,
                    'sca_shots': insert_stmt.excluded.sca_shots,
                    'sca_fouled': insert_stmt.excluded.sca_fouled,
                    'sca_defense': insert_stmt.excluded.sca_defense,
                    'goal_creating_actions': insert_stmt.excluded.goal_creating_actions,
                    'gca_passes_live': insert_stmt.excluded.gca_passes_live,
                    'gca_passes_dead': insert_stmt.excluded.gca_passes_dead,
                    'gca_take_ons': insert_stmt.excluded.gca_take_ons,
                    'gca_shots': insert_stmt.excluded.gca_shots,
                    'gca_fouled': insert_stmt.excluded.gca_fouled,
                    'gca_defense': insert_stmt.excluded.gca_defense,
                    'update_at': func.now()
                },
                where=(
                    or_(
                        GoalAndShotCreation.shot_creating_actions != insert_stmt.excluded.shot_creating_actions,
                        GoalAndShotCreation.sca_passes_live != insert_stmt.excluded.sca_passes_live,
                        GoalAndShotCreation.sca_passes_dead != insert_stmt.excluded.sca_passes_dead,
                        GoalAndShotCreation.sca_take_ons != insert_stmt.excluded.sca_take_ons,
                        GoalAndShotCreation.sca_shots != insert_stmt.excluded.sca_shots,
                        GoalAndShotCreation.sca_fouled != insert_stmt.excluded.sca_fouled,
                        GoalAndShotCreation.sca_defense != insert_stmt.excluded.sca_defense,
                        GoalAndShotCreation.goal_creating_actions != insert_stmt.excluded.goal_creating_actions,
                        GoalAndShotCreation.gca_passes_live != insert_stmt.excluded.gca_passes_live,
                        GoalAndShotCreation.gca_passes_dead != insert_stmt.excluded.gca_passes_dead,
                        GoalAndShotCreation.gca_take_ons != insert_stmt.excluded.gca_take_ons,
                        GoalAndShotCreation.gca_shots != insert_stmt.excluded.gca_shots,
                        GoalAndShotCreation.gca_fouled != insert_stmt.excluded.gca_fouled,
                        GoalAndShotCreation.gca_defense != insert_stmt.excluded.gca_defense
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {club.name} {season_range} goal and shot creations from {site.name} completed. upserted: {upserted_count}")

            insert_flag_stmt = insert(ClubSyncState).values(
                code=club.code,
                season=season,
                sync_flags=ClubSyncFlag.GCA.value
            )
            insert_flag_stmt = insert_flag_stmt.on_conflict_do_update(
                index_elements=['code', 'season'],
                set_={
                    'sync_flags': ClubSyncState.sync_flags.op('|')(ClubSyncFlag.GCA.value),
                    'update_at': func.now()
                }
            )
            session.execute(insert_flag_stmt)
            self.logger.info(f"Mark {site.name} {club.name} {season_range} goal and shot creations as synced")
