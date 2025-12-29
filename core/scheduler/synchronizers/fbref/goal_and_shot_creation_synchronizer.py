from typing import List
from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import GoalAndShotCreation, Site, MatchStatsSyncFlag
from .team_level_synchronizer import TeamLevelSynchronizer


class GoalAndShotCreationSynchronizer(TeamLevelSynchronizer):
    def sync(self, site: Site, team_name: str, team_code: str, season: int, goal_and_shot_creations: List[GoalAndShotCreation]) -> None:
        season_range = f"{season}-{season+1}"
        if not goal_and_shot_creations:
            self.logger.warning(f"No {team_name} {season_range} goal and shot creations to sync from {site.name}")
            return

        goal_and_shot_creation_dict = self.to_dict(
            goal_and_shot_creations,
            ['match_code', 'team_code', 'shot_creating_actions', 'sca_passes_live', 'sca_passes_dead', 'sca_take_ons',
             'sca_shots', 'sca_fouled', 'sca_defense', 'goal_creating_actions', 'gca_passes_live', 'gca_passes_dead', 'gca_take_ons',
             'gca_shots', 'gca_fouled', 'gca_defense'],
            ['match_code', 'team_code']
        )

        with self.db.get_session(site.get_namespace()) as session:
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
                    'updated_at': func.now()
                },
                where=(
                    or_(
                        GoalAndShotCreation.shot_creating_actions.is_distinct_from(insert_stmt.excluded.shot_creating_actions),
                        GoalAndShotCreation.sca_passes_live.is_distinct_from(insert_stmt.excluded.sca_passes_live),
                        GoalAndShotCreation.sca_passes_dead.is_distinct_from(insert_stmt.excluded.sca_passes_dead),
                        GoalAndShotCreation.sca_take_ons.is_distinct_from(insert_stmt.excluded.sca_take_ons),
                        GoalAndShotCreation.sca_shots.is_distinct_from(insert_stmt.excluded.sca_shots),
                        GoalAndShotCreation.sca_fouled.is_distinct_from(insert_stmt.excluded.sca_fouled),
                        GoalAndShotCreation.sca_defense.is_distinct_from(insert_stmt.excluded.sca_defense),
                        GoalAndShotCreation.goal_creating_actions.is_distinct_from(insert_stmt.excluded.goal_creating_actions),
                        GoalAndShotCreation.gca_passes_live.is_distinct_from(insert_stmt.excluded.gca_passes_live),
                        GoalAndShotCreation.gca_passes_dead.is_distinct_from(insert_stmt.excluded.gca_passes_dead),
                        GoalAndShotCreation.gca_take_ons.is_distinct_from(insert_stmt.excluded.gca_take_ons),
                        GoalAndShotCreation.gca_shots.is_distinct_from(insert_stmt.excluded.gca_shots),
                        GoalAndShotCreation.gca_fouled.is_distinct_from(insert_stmt.excluded.gca_fouled),
                        GoalAndShotCreation.gca_defense.is_distinct_from(insert_stmt.excluded.gca_defense)
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {team_name} {season_range} goal and shot creations from {site.name} completed. upserted: {upserted_count}")

            self.add_sync_flag(session, team_code, season, MatchStatsSyncFlag.GCA.value)
            self.logger.info(f"Mark {site.name} {team_name} {season_range} goal and shot creations as synced")
