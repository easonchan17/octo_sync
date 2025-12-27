from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import MarketOdds, Site, CompSyncFlag
from core.store.postgres.models.fbref.match_result import MatchResult
from .comp_level_synchronizer import CompLevelSynchronizer


class MarketOddsSynchronizer(CompLevelSynchronizer):
    TARGET_SITE = 'fbref'

    def get_target_matches(self, comp_code: str, start_time: datetime) -> List[MatchResult]:
        target_site = self.get_site(self.TARGET_SITE)
        if not target_site:
            self.logger.error(f"Target site not found: {self.TARGET_SITE}")
            return []

        with self.db.get_session(target_site.get_namespace()) as session:
            matches = session.query(MatchResult).filter(
                MatchResult.comp_code == comp_code,
                MatchResult.kickoff_time >= start_time
            ).order_by(MatchResult.kickoff_time).all()

            if matches:
                session.expunge_all()

            return matches

    def sync(self, site: Site, comp_code: str, season: int, records: List[Dict[str, Any]]) -> None:
        season_range = f"{season}-{season+1}"
        if not records:
            self.logger.warning(f"No market odds to sync for {site.name} {season_range}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(MarketOdds).values(records)
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_code'],
                set_={
                    'kickoff_time': insert_stmt.excluded.kickoff_time,
                    'home_team': insert_stmt.excluded.home_team,
                    'away_team': insert_stmt.excluded.away_team,
                    'home_open': insert_stmt.excluded.home_open,
                    'draw_open': insert_stmt.excluded.draw_open,
                    'away_open': insert_stmt.excluded.away_open,
                    'home_close': insert_stmt.excluded.home_close,
                    'draw_close': insert_stmt.excluded.draw_close,
                    'away_close': insert_stmt.excluded.away_close,
                    'ah_line_open': insert_stmt.excluded.ah_line_open,
                    'ah_home_open': insert_stmt.excluded.ah_home_open,
                    'ah_away_open': insert_stmt.excluded.ah_away_open,
                    'ah_line_close': insert_stmt.excluded.ah_line_close,
                    'ah_home_close': insert_stmt.excluded.ah_home_close,
                    'ah_away_close': insert_stmt.excluded.ah_away_close,
                    'updated_at': func.now()
                },
                where=(
                    or_(
                        MarketOdds.kickoff_time != insert_stmt.excluded.kickoff_time,
                        MarketOdds.home_team != insert_stmt.excluded.home_team,
                        MarketOdds.away_team != insert_stmt.excluded.away_team,
                        MarketOdds.home_open != insert_stmt.excluded.home_open,
                        MarketOdds.draw_open != insert_stmt.excluded.draw_open,
                        MarketOdds.away_open != insert_stmt.excluded.away_open,
                        MarketOdds.home_close != insert_stmt.excluded.home_close,
                        MarketOdds.draw_close != insert_stmt.excluded.draw_close,
                        MarketOdds.away_close != insert_stmt.excluded.away_close,
                        MarketOdds.ah_line_open != insert_stmt.excluded.ah_line_open,
                        MarketOdds.ah_home_open != insert_stmt.excluded.ah_home_open,
                        MarketOdds.ah_away_open != insert_stmt.excluded.ah_away_open,
                        MarketOdds.ah_line_close != insert_stmt.excluded.ah_line_close,
                        MarketOdds.ah_home_close != insert_stmt.excluded.ah_home_close,
                        MarketOdds.ah_away_close != insert_stmt.excluded.ah_away_close,
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {season_range} market odds completed. upserted: {upserted_count}")

            self.add_sync_flag(session, comp_code, season, CompSyncFlag.MARKET_ODDS.value)
            self.logger.info(f"Mark {season_range} market odds as synced")