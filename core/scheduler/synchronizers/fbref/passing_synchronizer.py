from typing import List, Any
from sqlalchemy import func, update, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    Passing, Site, Status, Club, ClubSyncState, ClubSyncFlag
)
from ..base_synchronizer import BaseSynchronizer

class PassingSynchronizer(BaseSynchronizer):
    def sync(self, site: Site, club: Club, season: int, passings: List[Passing]) -> None:
        season_range = f"{season}-{season+1}"
        if not passings:
            self.logger.warning(f"No {club.name} {season_range} passings to sync from {site.name}")
            return

        passing_dict = self.to_dict(
            passings,
            ['match_code', 'team_code', 'passes_completed', 'passes', 'passes_pct',
             'passes_total_distance', 'passes_progressive_distance', 'passes_completed_short', 'passes_short', 'passes_pct_short',
             'passes_completed_medium', 'passes_medium', 'passes_pct_medium', 'passes_completed_long', 'passes_long', 'passes_pct_long',
             'assists', 'xg_assist', 'pass_xa', 'assisted_shots', 'passes_into_final_third', 'passes_into_penalty_area', 'crosses_into_penalty_area', 'progressive_passes'],
            ['match_code', 'team_code']
        )

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Passing).values(list(passing_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_code', 'team_code'],
                set_={
                    'passes_completed': insert_stmt.excluded.passes_completed,
                    'passes': insert_stmt.excluded.passes,
                    'passes_pct': insert_stmt.excluded.passes_pct,
                    'passes_total_distance': insert_stmt.excluded.passes_total_distance,
                    'passes_progressive_distance': insert_stmt.excluded.passes_progressive_distance,
                    'passes_completed_short': insert_stmt.excluded.passes_completed_short,
                    'passes_short': insert_stmt.excluded.passes_short,
                    'passes_pct_short': insert_stmt.excluded.passes_pct_short,
                    'passes_completed_medium': insert_stmt.excluded.passes_completed_medium,
                    'passes_medium': insert_stmt.excluded.passes_medium,
                    'passes_pct_medium': insert_stmt.excluded.passes_pct_medium,
                    'passes_completed_long': insert_stmt.excluded.passes_completed_long,
                    'passes_long': insert_stmt.excluded.passes_long,
                    'passes_pct_long': insert_stmt.excluded.passes_pct_long,
                    'assists': insert_stmt.excluded.assists,
                    'xg_assist': insert_stmt.excluded.xg_assist,
                    'pass_xa': insert_stmt.excluded.pass_xa,
                    'assisted_shots': insert_stmt.excluded.assisted_shots,
                    'passes_into_final_third': insert_stmt.excluded.passes_into_final_third,
                    'passes_into_penalty_area': insert_stmt.excluded.passes_into_penalty_area,
                    'crosses_into_penalty_area': insert_stmt.excluded.crosses_into_penalty_area,
                    'progressive_passes': insert_stmt.excluded.progressive_passes,
                    'update_at': func.now()
                },
                where=(
                    or_(
                        Passing.passes_completed != insert_stmt.excluded.passes_completed,
                        Passing.passes != insert_stmt.excluded.passes,
                        Passing.passes_pct != insert_stmt.excluded.passes_pct,
                        Passing.passes_total_distance != insert_stmt.excluded.passes_total_distance,
                        Passing.passes_progressive_distance != insert_stmt.excluded.passes_progressive_distance,
                        Passing.passes_completed_short != insert_stmt.excluded.passes_completed_short,
                        Passing.passes_short != insert_stmt.excluded.passes_short,
                        Passing.passes_pct_short != insert_stmt.excluded.passes_pct_short,
                        Passing.passes_completed_medium != insert_stmt.excluded.passes_completed_medium,
                        Passing.passes_medium != insert_stmt.excluded.passes_medium,
                        Passing.passes_pct_medium != insert_stmt.excluded.passes_pct_medium,
                        Passing.passes_completed_long != insert_stmt.excluded.passes_completed_long,
                        Passing.passes_long != insert_stmt.excluded.passes_long,
                        Passing.passes_pct_long != insert_stmt.excluded.passes_pct_long,
                        Passing.assists != insert_stmt.excluded.assists,
                        Passing.xg_assist != insert_stmt.excluded.xg_assist,
                        Passing.pass_xa != insert_stmt.excluded.pass_xa,
                        Passing.assisted_shots != insert_stmt.excluded.assisted_shots,
                        Passing.passes_into_final_third != insert_stmt.excluded.passes_into_final_third,
                        Passing.passes_into_penalty_area != insert_stmt.excluded.passes_into_penalty_area,
                        Passing.crosses_into_penalty_area != insert_stmt.excluded.crosses_into_penalty_area,
                        Passing.progressive_passes != insert_stmt.excluded.progressive_passes
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {club.name} {season_range} passings from {site.name} completed. upserted: {upserted_count}")

            insert_flag_stmt = insert(ClubSyncState).values(
                code=club.code,
                season=season,
                sync_flags=ClubSyncFlag.PASSING.value
            )
            insert_flag_stmt = insert_flag_stmt.on_conflict_do_update(
                index_elements=['code', 'season'],
                set_={
                    'sync_flags': ClubSyncState.sync_flags.op('|')(ClubSyncFlag.PASSING.value),
                    'update_at': func.now()
                }
            )
            session.execute(insert_flag_stmt)
            self.logger.info(f"Mark {site.name} {club.name} {season_range} passings as synced")