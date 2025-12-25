from typing import List, Any
from sqlalchemy import func, update, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    MatchResult, Site, Club, MatchStatsSyncState, MatchStatsSyncFlag
)
from ..base_synchronizer import BaseSynchronizer

class MatchResultSynchronizer(BaseSynchronizer):
    def sync(self, site: Site, club: Club, season: int, results: List[MatchResult]) -> None:
        season_range = f"{season}-{season+1}"
        if not results:
            self.logger.warning(f"No {club.name} {season_range} match results to sync from {site.name}")
            return

        result_dict = self.to_dict(
            results,
            ['season', 'comp_name', 'comp_code', 'kickoff_time', 'match_code', 'round', 'venue', 'home_team', 'home_code', 'away_team', 'away_code',
             'home_gf', 'away_gf', 'home_xg', 'away_xg', 'home_possession', 'away_possession', 'home_formation', 'away_formation', 'match_status', 'notes', 'match_report'],
            ['match_code']
        )

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(MatchResult).values(list(result_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_code'],
                set_={
                    'season': insert_stmt.excluded.season,
                    'comp_name': insert_stmt.excluded.comp_name,
                    'comp_code': insert_stmt.excluded.comp_code,
                    'kickoff_time': insert_stmt.excluded.kickoff_time,
                    'round': insert_stmt.excluded.round,
                    'venue': insert_stmt.excluded.venue,
                    'home_team': insert_stmt.excluded.home_team,
                    'home_code': insert_stmt.excluded.home_code,
                    'away_team': insert_stmt.excluded.away_team,
                    'away_code': insert_stmt.excluded.away_code,
                    'home_gf': insert_stmt.excluded.home_gf,
                    'away_gf': insert_stmt.excluded.away_gf,
                    'home_xg': insert_stmt.excluded.home_xg,
                    'away_xg': insert_stmt.excluded.away_xg,
                    'home_possession': insert_stmt.excluded.home_possession,
                    'away_possession': insert_stmt.excluded.away_possession,
                    'home_formation': insert_stmt.excluded.home_formation,
                    'away_formation': insert_stmt.excluded.away_formation,
                    'match_status': insert_stmt.excluded.match_status,
                    'notes': insert_stmt.excluded.notes,
                    'match_report': insert_stmt.excluded.match_report,
                    'updated_at': func.now()
                },
                where=(
                    or_(
                        MatchResult.season != insert_stmt.excluded.season,
                        MatchResult.comp_name != insert_stmt.excluded.comp_name,
                        MatchResult.comp_code != insert_stmt.excluded.comp_code,
                        MatchResult.kickoff_time != insert_stmt.excluded.kickoff_time,
                        MatchResult.round != insert_stmt.excluded.round,
                        MatchResult.venue != insert_stmt.excluded.venue,
                        MatchResult.home_team != insert_stmt.excluded.home_team,
                        MatchResult.home_code != insert_stmt.excluded.home_code,
                        MatchResult.away_team != insert_stmt.excluded.away_team,
                        MatchResult.away_code != insert_stmt.excluded.away_code,
                        MatchResult.home_gf != insert_stmt.excluded.home_gf,
                        MatchResult.away_gf != insert_stmt.excluded.away_gf,
                        MatchResult.home_xg != insert_stmt.excluded.home_xg,
                        MatchResult.away_xg != insert_stmt.excluded.away_xg,
                        MatchResult.home_possession != insert_stmt.excluded.home_possession,
                        MatchResult.away_possession != insert_stmt.excluded.away_possession,
                        MatchResult.home_formation != insert_stmt.excluded.home_formation,
                        MatchResult.away_formation != insert_stmt.excluded.away_formation,
                        MatchResult.match_status != insert_stmt.excluded.match_status,
                        MatchResult.notes != insert_stmt.excluded.notes,
                        MatchResult.match_report != insert_stmt.excluded.match_report
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {club.name} {season_range} match results from {site.name} completed. upserted: {upserted_count}")

            insert_flag_stmt = insert(MatchStatsSyncState).values(
                team_code=club.code,
                season=season,
                sync_flags=MatchStatsSyncFlag.MATCH_RESULT.value
            )
            insert_flag_stmt = insert_flag_stmt.on_conflict_do_update(
                index_elements=['team_code', 'season'],
                set_={
                    'sync_flags': MatchStatsSyncState.sync_flags.op('|')(MatchStatsSyncFlag.MATCH_RESULT.value),
                    'updated_at': func.now()
                }
            )
            session.execute(insert_flag_stmt)
            self.logger.info(f"Mark {site.name} {club.name} {season_range} match results as synced")
