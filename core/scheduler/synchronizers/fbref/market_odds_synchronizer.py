from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import MarketOdds, Site, CompSyncFlag
from core.store.postgres.models.fbref.match_result import MatchResult
from core.domain.enums import SiteName
from .comp_level_synchronizer import CompLevelSynchronizer


class MarketOddsSynchronizer(CompLevelSynchronizer):
    def sync(
        self,
        site: Site,
        comp_code: str,
        season: int,
        last_synced_time: datetime,
        records: List[Dict[str, Any]]
    ) -> None:
        season_range = f"{season}-{season+1}"
        if not records:
            self.logger.warning(f"No market odds to sync for {site.name} {season_range}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(MarketOdds).values(records)
            assignment, where_clause = self.build_upsert_clauses(
                MarketOdds,
                insert_stmt,
                {
                    MarketOdds.id.key,
                    MarketOdds.created_at.key,
                    MarketOdds.match_code.key,
                    MarketOdds.updated_at.key
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[MarketOdds.match_code.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {season_range} market odds completed. upserted: {upserted_count}")

            self.update_sync_state(
                session, comp_code, season, CompSyncFlag.MARKET_ODDS, last_synced_time
            )
            self.logger.info(f"Mark {season_range} market odds as synced")