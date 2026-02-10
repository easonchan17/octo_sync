from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy import func, and_, or_
from core.store.postgres.models import Site
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.fotmob.fixture_data import Fixture, FixtureRawData
from core.store.postgres.models.fotmob.match_data import MatchRawData, MatchLineup, MatchStat, MatchPlayerStat
from ..base_synchronizer import BaseSynchronizer
from core.types.enums import MatchStatus

class MatchDataSynchronizer(BaseSynchronizer):
    def get_pending_fetch_items(
        self,
        site: Site,
        start_time: datetime,
        end_time: datetime,
        max_retries: int,
        limit: int
    ) -> List[Any]:
        with self.db.get_session(site.get_namespace()) as session:
            query = session.query(
                Fixture.match_id,
                Fixture.kickoff_time,
                Fixture.page_url
            ).outerjoin(
                MatchRawData, Fixture.match_id == MatchRawData.match_id
            ).filter(
                or_(
                    MatchRawData.match_id.is_(None),
                    and_(
                        MatchRawData.is_fetched == False,
                        MatchRawData.fetch_attempts < max_retries
                    )
                ),
                Fixture.kickoff_time >= start_time,
                Fixture.kickoff_time < end_time,
                ~Fixture.match_status.in_([MatchStatus.POSTPONED.value, MatchStatus.CANCELLED.value])
            ).order_by(
                Fixture.kickoff_time.desc()
            ).limit(limit)

            return query.all()

    def get_pending_parse_items(
        self,
        site: Site,
        start_time: datetime,
        end_time: datetime,
        max_retries: int,
        limit: int
    ) -> List[Any]:
        with self.db.get_session(site.get_namespace()) as session:
            query = session.query(
                MatchRawData.match_id,
                Fixture.kickoff_time,
                MatchRawData.last_fetched_at,
                MatchRawData.json_body
            ).join(
                Fixture, MatchRawData.match_id == Fixture.match_id
            ).filter(
                Fixture.kickoff_time >= start_time,
                Fixture.kickoff_time < end_time,
                MatchRawData.is_fetched == True,
                MatchRawData.is_parsed == False,
                MatchRawData.parse_attempts < max_retries
            ).order_by(
                Fixture.kickoff_time.asc()
            ).limit(limit)

            return query.all()

    def get_pending_refetch_items(
        self,
        site: Site,
        start_time: datetime,
        end_time: datetime,
        required_confirm_count: int,
        limit: int
    ) -> List[Any]:
        with self.db.get_session(site.get_namespace()) as session:
            query = session.query(
                MatchRawData.match_id,
                Fixture.kickoff_time,
                Fixture.match_status,
                MatchRawData.confirm_count,
                MatchRawData.last_fetched_at,
                Fixture.page_url
            ).join(
                Fixture, MatchRawData.match_id == Fixture.match_id
            ).filter(
                Fixture.kickoff_time >= start_time,
                Fixture.kickoff_time < end_time,
                MatchRawData.is_parsed == True,
                MatchRawData.confirm_count < required_confirm_count,
                ~Fixture.match_status.in_([MatchStatus.POSTPONED.value, MatchStatus.CANCELLED.value])
            ).order_by(
                Fixture.kickoff_time.asc()
            ).limit(limit)

            return query.all()

    def mark_as_fetched(self, site: Site, match_id: int) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(MatchRawData).filter(
                MatchRawData.match_id == match_id
            ).update({
                MatchRawData.is_fetched: True,
                MatchRawData.last_fetch_error: None,
                MatchRawData.last_fetched_at: func.now(),
                MatchRawData.total_fetch_count: MatchRawData.total_fetch_count + 1,
                MatchRawData.is_parsed: False,
                MatchRawData.last_parse_error: None,
                MatchRawData.fetch_attempts: 0,
                MatchRawData.parse_attempts: 0,
                MatchRawData.updated_at: func.now()
            }, synchronize_session=False)

    def mark_fetch_failed(self, site: Site, match_id: int, kickoff_time: datetime, error_msg: str) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(MatchRawData).values(
                match_id=match_id,
                kickoff_time=kickoff_time,
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or "")[:2000],
                total_fetch_count=1,
                json_body={}
            )

            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[MatchRawData.match_id],
                set_={
                    MatchRawData.is_fetched: False,
                    MatchRawData.last_fetch_error: (error_msg or "")[:2000],
                    MatchRawData.fetch_attempts: MatchRawData.fetch_attempts + 1,
                    MatchRawData.total_fetch_count: MatchRawData.total_fetch_count + 1,
                    MatchRawData.updated_at: func.now()
                }
            )

            session.execute(upsert_stmt)

    def mark_as_parsed(self, site: Site, match_id: int, kickoff_time: datetime, match_status: int) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(MatchRawData).filter(
                MatchRawData.match_id == match_id
            ).update({
                MatchRawData.kickoff_time: kickoff_time,
                MatchRawData.match_status: match_status,
                MatchRawData.is_parsed: True,
                MatchRawData.last_parse_error: None,
                MatchRawData.parse_attempts: 0,
                MatchRawData.total_parse_count: MatchRawData.total_parse_count + 1,
                MatchRawData.last_parsed_at: func.now(),
                MatchRawData.updated_at: func.now()
            }, synchronize_session=False)

    def mark_parse_failed(self, site: Site, match_id: int, error_msg: str) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(MatchRawData).filter(
                MatchRawData.match_id == match_id
            ).update({
                MatchRawData.is_parsed: False,
                MatchRawData.last_parse_error: (error_msg or "")[:2000],
                MatchRawData.parse_attempts: MatchRawData.parse_attempts + 1,
                MatchRawData.total_parse_count: MatchRawData.total_parse_count + 1,
                MatchRawData.updated_at: func.now()
            }, synchronize_session=False)

    def set_confirm_count(self, site: Site, match_id: int, count: int) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(MatchRawData).filter(
                MatchRawData.match_id == match_id
            ).update({
                MatchRawData.confirm_count: count,
                MatchRawData.updated_at: func.now()
            }, synchronize_session=False)

    def sync_raw_data(self, site: Site, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(MatchRawData).values(raw_data)
            assignment, where_clause = self.build_upsert_clauses(
                MatchRawData,
                insert_stmt,
                {
                    MatchRawData.id.key,
                    MatchRawData.created_at.key,
                    MatchRawData.match_id.key,
                    MatchRawData.updated_at.key,
                    MatchRawData.last_fetched_at.key,
                    MatchRawData.last_parsed_at.key,
                    MatchRawData.total_fetch_count.key,
                    MatchRawData.total_parse_count.key,
                    MatchRawData.confirm_count.key
                }
            )

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[MatchRawData.match_id.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.debug(f"Sync {site.name} match raw data completed. upserted: {upserted_count}")

    def sync_parsed_data(self, site: Site, parsed_data: Dict[str, Any]) -> None:
        match_id = parsed_data.get("match_id")
        lineup = parsed_data.get("lineup")
        match_stats = parsed_data.get("match_stats")
        player_stats = parsed_data.get("player_stats")

        with self.db.get_session(site.get_namespace()) as session:
            if lineup:
                home_lineup = lineup.get("home_lineup")
                away_lineup = lineup.get("away_lineup")
                if home_lineup and away_lineup:
                    self._sync_lineup(session, match_id, "home", home_lineup)
                    self._sync_lineup(session, match_id, "away", away_lineup)

                    lineup_type = lineup.get("lineup_type")
                    home_formation = lineup.get("home_formation")
                    away_formation = lineup.get("away_formation")
                    self._sync_match_stats(
                        session,
                        match_id, {
                            "match_id": match_id,
                            "lineup_type": lineup_type,
                            "home_formation": home_formation,
                            "away_formation": away_formation
                        })

            if match_stats:
                self._sync_match_stats(session, match_id, match_stats)

            if player_stats:
                self._sync_player_stats(session, match_id, player_stats)

    def _sync_lineup(self, session, match_id: int, venue: str, lineup: List[Dict[str, Any]]) -> None:
        insert_stmt = insert(MatchLineup).values(lineup)
        assignment, where_clause = self.build_upsert_clauses(
            MatchLineup,
            insert_stmt,
            {
                MatchLineup.id.key,
                MatchLineup.created_at.key,
                MatchLineup.match_id.key,
                MatchLineup.member_id.key,
                MatchLineup.updated_at.key
            }
        )
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[MatchLineup.match_id.key, MatchLineup.team_id.key, MatchLineup.opta_id.key, MatchLineup.member_id.key, MatchLineup.member_name.key],
            set_=assignment,
            where=where_clause
        )
        result = session.execute(insert_stmt)
        upserted_count = result.rowcount
        self.logger.debug(f"Sync match {match_id} {venue} lineup completed. upserted: {upserted_count}")

    def _sync_match_stats(self, session, match_id: int, match_stats: Dict[str, Any]) -> None:
        insert_stmt = insert(MatchStat).values(match_stats)
        assignment, where_clause = self.build_upsert_clauses(
            MatchStat,
            insert_stmt,
            {
                MatchStat.id.key,
                MatchStat.created_at.key,
                MatchStat.match_id.key,
                MatchStat.updated_at.key
            }
        )
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[MatchStat.match_id.key],
            set_=assignment,
            where=where_clause
        )
        result = session.execute(insert_stmt)
        upserted_count = result.rowcount
        self.logger.debug(f"Sync match {match_id} stats completed. upserted: {upserted_count}")

    def _sync_player_stats(self, session, match_id: int, player_stats: List[Dict[str, Any]]) -> None:
        insert_stmt = insert(MatchPlayerStat).values(player_stats)
        assignment, where_clause = self.build_upsert_clauses(
            MatchPlayerStat,
            insert_stmt,
            {
                MatchPlayerStat.id.key,
                MatchPlayerStat.created_at.key,
                MatchPlayerStat.match_id.key,
                MatchPlayerStat.player_id.key,
                MatchPlayerStat.updated_at.key
            }
        )
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[MatchPlayerStat.match_id.key, MatchPlayerStat.opta_id.key, MatchPlayerStat.player_id.key, MatchPlayerStat.player_name.key],
            set_=assignment,
            where=where_clause
        )
        result = session.execute(insert_stmt)
        upserted_count = result.rowcount
        self.logger.debug(f"Sync match {match_id} player stats completed. upserted: {upserted_count}")
