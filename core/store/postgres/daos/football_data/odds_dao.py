from sqlalchemy import func
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from typing import List, Dict, Any, Optional
from core.store.postgres.models.football_data.odds import OddsRaw, Odds
from core.store.postgres.models.football_data.league import LeagueOdds
from ..base_dao import BaseDao

class OddsDao(BaseDao):
    def get_pending_fetch_item(self, season: int, league_id: str) -> Optional[Any]:
        with self.db.get_session() as session:
            return session.query(
                LeagueOdds.season,
                LeagueOdds.league_id,
                OddsRaw.last_fetched_at,
                LeagueOdds.odds_url
            ).outerjoin(
                OddsRaw,
                (LeagueOdds.season == OddsRaw.season) &
                (LeagueOdds.league_id == OddsRaw.league_id)
            ).filter(
                LeagueOdds.season == season,
                LeagueOdds.league_id == league_id,
                (OddsRaw.id == None) | (OddsRaw.is_fetched == False)
            ).first()

    def mark_fetch_failed(self, season: int, league_id: str, error_msg: str) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(OddsRaw).values(
                season=season,
                league_id=league_id,
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or '')[:2000],
                total_fetch_count=1,
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[OddsRaw.season.key, OddsRaw.league_id.key],
                set_={
                    OddsRaw.is_fetched.key: False,
                    OddsRaw.last_fetch_error.key: (error_msg or '')[:2000],
                    OddsRaw.fetch_attempts.key: OddsRaw.fetch_attempts + 1,
                    OddsRaw.total_fetch_count.key: OddsRaw.total_fetch_count + 1,
                    OddsRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def mark_as_fetched(self, season: int, league_id: str) -> None:
        with self.db.get_session() as session:
            session.query(OddsRaw).filter(
                OddsRaw.season == season,
                OddsRaw.league_id == league_id,
            ).update({
                OddsRaw.is_fetched.key: True,
                OddsRaw.last_fetch_error.key: None,
                OddsRaw.last_fetched_at.key: func.now(),
                OddsRaw.total_fetch_count.key: OddsRaw.total_fetch_count + 1,
                OddsRaw.fetch_attempts.key: 0,
                OddsRaw.is_parsed.key: False,
                OddsRaw.last_parse_error.key: None,
                OddsRaw.parse_attempts.key: 0,
                OddsRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(OddsRaw).values(raw_data)

            update_values = {
                OddsRaw.source_url.key: raw_data.get('source_url'),
                OddsRaw.updated_at.key: func.now(),
            }

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[OddsRaw.season.key, OddsRaw.league_id.key],
                set_=update_values
            )

            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.debug(f"Synced odds raw data completed. upserted: {upserted_count}")

    def save_records(
        self,
        comp_code: str,
        season: int,
        last_synced_time: datetime,
        records: List[Dict[str, Any]],
        update_state: bool = False
    ) -> None:
        if not records:
            self.logger.warning(f"No match odds to sync for {season}-{season+1}")
            return

        with self.db.get_session() as session:
            insert_stmt = insert(Odds).values(records)
            assignment, where_clause = self.build_upsert_clauses(
                Odds,
                insert_stmt,
                {
                    Odds.id.key,
                    Odds.created_at.key,
                    Odds.match_id.key,
                    Odds.updated_at.key
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[Odds.match_id.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            self.logger.info(f"Sync {season}-{season+1} match odds completed. upserted: {result.rowcount}")
