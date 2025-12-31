from datetime import datetime
from typing import List, Dict, Any
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
            assignment, where_clause = self.build_upsert_clauses(
                MarketOdds,
                insert_stmt,
                {'id', 'created_at', 'match_code', 'updated_at'}
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_code'],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {season_range} market odds completed. upserted: {upserted_count}")

            self.add_sync_flag(session, comp_code, season, CompSyncFlag.MARKET_ODDS.value)
            self.logger.info(f"Mark {season_range} market odds as synced")