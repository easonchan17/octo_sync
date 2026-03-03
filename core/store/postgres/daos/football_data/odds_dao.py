from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.football_data.odds import MarketOdds
from ..base_dao import BaseDao

class MarketOddsDao(BaseDao):
    def save_records(
        self,
        comp_code: str,
        season: int,
        last_synced_time: datetime,
        records: List[Dict[str, Any]],
        update_state: bool = False
    ) -> None:
        if not records:
            self.logger.warning(f"No market odds to sync for {season}-{season+1}")
            return

        with self.db.get_session() as session:
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
            self.logger.info(f"Sync {season}-{season+1} market odds completed. upserted: {result.rowcount}")
