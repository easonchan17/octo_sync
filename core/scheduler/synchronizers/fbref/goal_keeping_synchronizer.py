from typing import List
from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    GoalKeeping, Site, Club, ClubStatus, ClubSyncFlag
)
from ..base_synchronizer import BaseSynchronizer

class GoalKeepingSynchronizer(BaseSynchronizer):
    def sync(self, site: Site, club: Club, season: int, goal_keepings: List[GoalKeeping]) -> None:
        season_range = f"{season}-{season+1}"
        if not goal_keepings:
            self.logger.warning(f"No {club.name} {season_range} goal keepings to sync from {site.name}")
            return

        goal_keeping_dict = self.to_dict(
            goal_keepings,
            ['match_code', 'team_code', 'shots_on_target_against', 'saves', 'save_pct',
             'psxg', 'psxg_net', 'crosses', 'crosses_stopped',
             'crosses_stopped_pct', 'def_actions_outside_pen_area', 'avg_distance_def_actions'],
            ['match_code', 'team_code']
        )

        with self.postgresql_manager.get_session(site.get_namespace()) as session:
            insert_stmt = insert(GoalKeeping).values(list(goal_keeping_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_code', 'team_code'],
                set_={
                    'shots_on_target_against': insert_stmt.excluded.shots_on_target_against,
                    'saves': insert_stmt.excluded.saves,
                    'save_pct': insert_stmt.excluded.save_pct,
                    'psxg': insert_stmt.excluded.psxg,
                    'psxg_net': insert_stmt.excluded.psxg_net,
                    'crosses': insert_stmt.excluded.crosses,
                    'crosses_stopped': insert_stmt.excluded.crosses_stopped,
                    'crosses_stopped_pct': insert_stmt.excluded.crosses_stopped_pct,
                    'def_actions_outside_pen_area': insert_stmt.excluded.def_actions_outside_pen_area,
                    'avg_distance_def_actions': insert_stmt.excluded.avg_distance_def_actions,
                    'update_at': func.now()
                },
                where=(
                    or_(
                        GoalKeeping.shots_on_target_against != insert_stmt.excluded.shots_on_target_against,
                        GoalKeeping.saves != insert_stmt.excluded.saves,
                        GoalKeeping.save_pct != insert_stmt.excluded.save_pct,
                        GoalKeeping.psxg != insert_stmt.excluded.psxg,
                        GoalKeeping.psxg_net != insert_stmt.excluded.psxg_net,
                        GoalKeeping.crosses != insert_stmt.excluded.crosses,
                        GoalKeeping.crosses_stopped != insert_stmt.excluded.crosses_stopped,
                        GoalKeeping.crosses_stopped_pct != insert_stmt.excluded.crosses_stopped_pct,
                        GoalKeeping.def_actions_outside_pen_area != insert_stmt.excluded.def_actions_outside_pen_area,
                        GoalKeeping.avg_distance_def_actions != insert_stmt.excluded.avg_distance_def_actions
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {club.name} {season_range} goal keepings from {site.name} completed. upserted: {upserted_count}")

            insert_flag_stmt = insert(ClubStatus).values(
                code=club.code,
                season=season,
                sync_flags=ClubSyncFlag.GOAL_KEEPING.value
            )
            insert_flag_stmt = insert_flag_stmt.on_conflict_do_update(
                index_elements=['code', 'season'],
                set_={
                    'sync_flags': ClubStatus.sync_flags.op('|')(ClubSyncFlag.GOAL_KEEPING.value),
                    'update_at': func.now()
                }
            )
            session.execute(insert_flag_stmt)
            self.logger.info(f"Mark {site.name} {club.name} {season_range} goal keepings as synced")
