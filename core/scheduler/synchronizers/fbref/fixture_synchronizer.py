from typing import List, Any
from sqlalchemy import func, update, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    Fixture, Site, Club, ClubSyncState, ClubSyncFlag
)
from ..base_synchronizer import BaseSynchronizer

class FixtureSynchronizer(BaseSynchronizer):
    def sync(self, site: Site, club: Club, season: int, fixtures: List[Fixture]) -> None:
        season_range = f"{season}-{season+1}"
        if not fixtures:
            self.logger.warning(f"No {club.name} {season_range} fixtures to sync from {site.name}")
            return

        fixture_dict = self.to_dict(
            fixtures,
            ['season', 'comp_name', 'comp_code', 'kickoff_time', 'code', 'round', 'venue', 'home_team', 'home_code', 'away_team', 'away_code',
             'home_gf', 'away_gf', 'home_xg', 'away_xg', 'home_possession', 'away_possession', 'home_formation', 'away_formation', 'match_status', 'notes', 'match_report'],
            ['code']
        )

        with self.postgresql_manager.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Fixture).values(list(fixture_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['code'],
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
                    'update_at': func.now()
                },
                where=(
                    or_(
                        Fixture.season != insert_stmt.excluded.season,
                        Fixture.comp_name != insert_stmt.excluded.comp_name,
                        Fixture.comp_code != insert_stmt.excluded.comp_code,
                        Fixture.kickoff_time != insert_stmt.excluded.kickoff_time,
                        Fixture.round != insert_stmt.excluded.round,
                        Fixture.venue != insert_stmt.excluded.venue,
                        Fixture.home_team != insert_stmt.excluded.home_team,
                        Fixture.home_code != insert_stmt.excluded.home_code,
                        Fixture.away_team != insert_stmt.excluded.away_team,
                        Fixture.away_code != insert_stmt.excluded.away_code,
                        Fixture.home_gf != insert_stmt.excluded.home_gf,
                        Fixture.away_gf != insert_stmt.excluded.away_gf,
                        Fixture.home_xg != insert_stmt.excluded.home_xg,
                        Fixture.away_xg != insert_stmt.excluded.away_xg,
                        Fixture.home_possession != insert_stmt.excluded.home_possession,
                        Fixture.away_possession != insert_stmt.excluded.away_possession,
                        Fixture.home_formation != insert_stmt.excluded.home_formation,
                        Fixture.away_formation != insert_stmt.excluded.away_formation,
                        Fixture.match_status != insert_stmt.excluded.match_status,
                        Fixture.notes != insert_stmt.excluded.notes,
                        Fixture.match_report != insert_stmt.excluded.match_report
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {club.name} {season_range} fixtures from {site.name} completed. upserted: {upserted_count}")

            insert_flag_stmt = insert(ClubSyncState).values(
                code=club.code,
                season=season,
                sync_flags=ClubSyncFlag.FIXTURE.value
            )
            insert_flag_stmt = insert_flag_stmt.on_conflict_do_update(
                index_elements=['code', 'season'],
                set_={
                    'sync_flags': ClubSyncState.sync_flags.op('|')(ClubSyncFlag.FIXTURE.value),
                    'update_at': func.now()
                }
            )
            session.execute(insert_flag_stmt)
            self.logger.info(f"Mark {site.name} {club.name} {season_range} fixtures as synced")