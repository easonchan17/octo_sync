from typing import List, Any
from sqlalchemy import func, update, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    DefensiveAction, Site, Status, Club, ClubStatus, ClubSyncFlag
)
from ..base_synchronizer import BaseSynchronizer

class DefensiveActionSynchronizer(BaseSynchronizer):
    def sync(self, site: Site, club: Club, season: int, defensive_actions: List[DefensiveAction]) -> None:
        season_range = f"{season}-{season+1}"
        if not defensive_actions:
            self.logger.warning(f"No {club.name} {season_range} defensive actions to sync from {site.name}")
            return

        defensive_action_dict = self.to_dict(
            defensive_actions,
            ['match_code', 'team_code', 'tackles', 'tackles_won', 'tackles_def_third', 'tackles_mid_third', 'tackles_att_third',
             'challenge_tackles', 'challenges', 'challenge_tackles_pct', 'challenges_lost',
             'blocks', 'blocked_shots', 'blocked_passes', 'interceptions', 'clearances', 'errors_shot'],
            ['match_code', 'team_code']
        )

        with self.postgresql_manager.get_session(site.get_namespace()) as session:
            insert_stmt = insert(DefensiveAction).values(list(defensive_action_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_code', 'team_code'],
                set_={
                    'tackles': insert_stmt.excluded.tackles,
                    'tackles_won': insert_stmt.excluded.tackles_won,
                    'tackles_def_third': insert_stmt.excluded.tackles_def_third,
                    'tackles_mid_third': insert_stmt.excluded.tackles_mid_third,
                    'tackles_att_third': insert_stmt.excluded.tackles_att_third,
                    'challenge_tackles': insert_stmt.excluded.challenge_tackles,
                    'challenges': insert_stmt.excluded.challenges,
                    'challenge_tackles_pct': insert_stmt.excluded.challenge_tackles_pct,
                    'challenges_lost': insert_stmt.excluded.challenges_lost,
                    'blocks': insert_stmt.excluded.blocks,
                    'blocked_shots': insert_stmt.excluded.blocked_shots,
                    'blocked_passes': insert_stmt.excluded.blocked_passes,
                    'interceptions': insert_stmt.excluded.interceptions,
                    'clearances': insert_stmt.excluded.clearances,
                    'errors_shot': insert_stmt.excluded.errors_shot,
                    'update_at': func.now()
                },
                where=(
                    or_(
                        DefensiveAction.tackles != insert_stmt.excluded.tackles,
                        DefensiveAction.tackles_won != insert_stmt.excluded.tackles_won,
                        DefensiveAction.tackles_def_third != insert_stmt.excluded.tackles_def_third,
                        DefensiveAction.tackles_mid_third != insert_stmt.excluded.tackles_mid_third,
                        DefensiveAction.tackles_att_third != insert_stmt.excluded.tackles_att_third,
                        DefensiveAction.challenge_tackles != insert_stmt.excluded.challenge_tackles,
                        DefensiveAction.challenges != insert_stmt.excluded.challenges,
                        DefensiveAction.challenge_tackles_pct != insert_stmt.excluded.challenge_tackles_pct,
                        DefensiveAction.challenges_lost != insert_stmt.excluded.challenges_lost,
                        DefensiveAction.blocks != insert_stmt.excluded.blocks,
                        DefensiveAction.blocked_shots != insert_stmt.excluded.blocked_shots,
                        DefensiveAction.blocked_passes != insert_stmt.excluded.blocked_passes,
                        DefensiveAction.interceptions != insert_stmt.excluded.interceptions,
                        DefensiveAction.clearances != insert_stmt.excluded.clearances,
                        DefensiveAction.errors_shot != insert_stmt.excluded.errors_shot
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {club.name} {season_range} defensive actions from {site.name} completed. upserted: {upserted_count}")

            insert_flag_stmt = insert(ClubStatus).values(
                code=club.code,
                season=season,
                sync_flags=ClubSyncFlag.DEFENSIVE_ACTION.value
            )
            insert_flag_stmt = insert_flag_stmt.on_conflict_do_update(
                index_elements=['code', 'season'],
                set_={
                    'sync_flags': ClubStatus.sync_flags.op('|')(ClubSyncFlag.DEFENSIVE_ACTION.value),
                    'update_at': func.now()
                }
            )
            session.execute(insert_flag_stmt)
            self.logger.info(f"Mark {site.name} {club.name} {season_range} defensive actions as synced")
