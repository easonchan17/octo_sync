from typing import List
from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Shooting, Site, MatchStatsSyncFlag
from .team_level_synchronizer import TeamLevelSynchronizer


class ShootingSynchronizer(TeamLevelSynchronizer):
    def sync(self, site: Site, team_name: str, team_code: str, season: int, shootings: List[Shooting]) -> None:
        season_range = f"{season}-{season+1}"
        if not shootings:
            self.logger.warning(f"No {team_name} {season_range} shootings to sync from {site.name}")
            return

        shooting_dict = self.to_dict(
            shootings,
            ['match_code', 'team_code', 'goals', 'shots', 'shots_on_target', 'shots_on_target_pct',
             'shots_free_kicks', 'average_shot_distance', 'penalties_made', 'penalties_attempted', 'xg', 'npxg'],
            ['match_code', 'team_code']
        )

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Shooting).values(list(shooting_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_code', 'team_code'],
                set_={
                    'goals': insert_stmt.excluded.goals,
                    'shots': insert_stmt.excluded.shots,
                    'shots_on_target': insert_stmt.excluded.shots_on_target,
                    'shots_on_target_pct': insert_stmt.excluded.shots_on_target_pct,
                    'shots_free_kicks': insert_stmt.excluded.shots_free_kicks,
                    'average_shot_distance': insert_stmt.excluded.average_shot_distance,
                    'penalties_made': insert_stmt.excluded.penalties_made,
                    'penalties_attempted': insert_stmt.excluded.penalties_attempted,
                    'xg': insert_stmt.excluded.xg,
                    'npxg': insert_stmt.excluded.npxg,
                    'updated_at': func.now()
                },
                where=(
                    or_(
                        Shooting.goals != insert_stmt.excluded.goals,
                        Shooting.shots != insert_stmt.excluded.shots,
                        Shooting.shots_on_target != insert_stmt.excluded.shots_on_target,
                        Shooting.shots_on_target_pct != insert_stmt.excluded.shots_on_target_pct,
                        Shooting.shots_free_kicks != insert_stmt.excluded.shots_free_kicks,
                        Shooting.average_shot_distance != insert_stmt.excluded.average_shot_distance,
                        Shooting.penalties_made != insert_stmt.excluded.penalties_made,
                        Shooting.penalties_attempted != insert_stmt.excluded.penalties_attempted,
                        Shooting.xg != insert_stmt.excluded.xg,
                        Shooting.npxg != insert_stmt.excluded.npxg
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {team_name} {season_range} shootings from {site.name} completed. upserted: {upserted_count}")

            self.add_sync_flag(session, team_code, season, MatchStatsSyncFlag.SHOOTING.value)
            self.logger.info(f"Mark {site.name} {team_name} {season_range} shootings as synced")
