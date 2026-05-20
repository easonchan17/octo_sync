import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import func, and_, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.fotmob.fixture import Fixture
from core.store.postgres.models.fotmob.match import MatchRaw, MatchLineup, MatchStat, MatchPlayerStat, ShotStat
from ..base_dao import BaseDao
from core.types.enums import MatchStatus

class MatchDao(BaseDao):
    def get_pending_fetch_items(self, kickoff_before: datetime, league_ids: List[int], limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                Fixture.match_id,
                Fixture.kickoff_time,
                Fixture.page_url,
                Fixture.league_id,
                Fixture.league_name,
                func.coalesce(MatchRaw.fetch_attempts, 0).label("fetch_attempts")
            ).outerjoin(
                MatchRaw, Fixture.match_id == MatchRaw.match_id
            ).filter(
                Fixture.kickoff_time < kickoff_before,
                Fixture.league_id.in_(league_ids),
                ~Fixture.match_status.in_([MatchStatus.POSTPONED.value, MatchStatus.CANCELLED.value]),
                or_(
                    MatchRaw.match_id.is_(None),
                    MatchRaw.next_fetch_at <= func.now()
                )
            ).order_by(
                Fixture.kickoff_time.desc()
            ).limit(limit).all()

    def get_pending_parse_items(self, max_retries: int, limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                MatchRaw.match_id,
                MatchRaw.kickoff_time,
                MatchRaw.json_body,
            ).join(
                Fixture, Fixture.match_id == MatchRaw.match_id
            ).filter(
                MatchRaw.is_fetched == True,
                MatchRaw.is_parsed == False,
                MatchRaw.parse_attempts < max_retries
            ).order_by(
                MatchRaw.created_at.asc()
            ).limit(limit).all()

    def mark_as_not_modified(self, match_id: int, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(MatchRaw).filter(
                MatchRaw.match_id == match_id
            ).update({
                MatchRaw.is_fetched: True,
                MatchRaw.last_fetch_error: None,
                MatchRaw.last_fetched_at: func.now(),
                MatchRaw.next_fetch_at: func.now() + fetch_interval if fetch_interval is not None else None,
                MatchRaw.total_fetch_count: MatchRaw.total_fetch_count + 1,
                MatchRaw.fetch_attempts: 0,
                MatchRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_as_fetched(self, match_id: int, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(MatchRaw).filter(
                MatchRaw.match_id == match_id
            ).update({
                MatchRaw.is_fetched: True,
                MatchRaw.last_fetch_error: None,
                MatchRaw.last_fetched_at: func.now(),
                MatchRaw.next_fetch_at: func.now() + fetch_interval if fetch_interval is not None else None,
                MatchRaw.fetch_attempts: 0,
                MatchRaw.total_fetch_count: MatchRaw.total_fetch_count + 1,
                MatchRaw.is_parsed: False,
                MatchRaw.last_parse_error: None,
                MatchRaw.parse_attempts: 0,
                MatchRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_fetch_failed(self, match_id: int, kickoff_time: datetime, error_msg: str, fetch_interval: Optional[timedelta]) -> None:
        next_fetch_at = func.now() + fetch_interval if fetch_interval is not None else None
        with self.db.get_session() as session:
            insert_stmt = insert(MatchRaw).values(
                match_id=match_id,
                kickoff_time=kickoff_time,
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or "")[:2000],
                total_fetch_count=1,
                next_fetch_at=next_fetch_at,
                json_body={}
            )

            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[MatchRaw.match_id],
                set_={
                    MatchRaw.is_fetched: False,
                    MatchRaw.last_fetch_error: (error_msg or "")[:2000],
                    MatchRaw.fetch_attempts: MatchRaw.fetch_attempts + 1,
                    MatchRaw.total_fetch_count: MatchRaw.total_fetch_count + 1,
                    MatchRaw.next_fetch_at: next_fetch_at,
                    MatchRaw.updated_at: func.now()
                }
            )

            session.execute(upsert_stmt)

    def mark_as_parsed(self, match_id: int, kickoff_time: datetime, match_status: int) -> None:
        with self.db.get_session() as session:
            session.query(MatchRaw).filter(
                MatchRaw.match_id == match_id
            ).update({
                MatchRaw.kickoff_time: kickoff_time,
                MatchRaw.match_status: match_status,
                MatchRaw.is_parsed: True,
                MatchRaw.last_parse_error: None,
                MatchRaw.parse_attempts: 0,
                MatchRaw.total_parse_count: MatchRaw.total_parse_count + 1,
                MatchRaw.last_parsed_at: func.now(),
                MatchRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_parse_failed(self, match_id: int, error_msg: Optional[str] = None) -> None:
        if error_msg is None:
            error_msg = traceback.format_exc()
        with self.db.get_session() as session:
            session.query(MatchRaw).filter(
                MatchRaw.match_id == match_id
            ).update({
                MatchRaw.is_parsed: False,
                MatchRaw.last_parse_error: error_msg[:2000],
                MatchRaw.parse_attempts: MatchRaw.parse_attempts + 1,
                MatchRaw.total_parse_count: MatchRaw.total_parse_count + 1,
                MatchRaw.updated_at: func.now()
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(MatchRaw).values(raw_data)

            update_values = {
                MatchRaw.source_url.key: raw_data["source_url"],
                MatchRaw.kickoff_time.key: raw_data["kickoff_time"],
                MatchRaw.json_body.key: raw_data["json_body"],
                MatchRaw.updated_at.key: func.now()
            }

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[MatchRaw.match_id.key],
                set_=update_values
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.debug(f"Sync match raw data completed. upserted: {upserted_count}")

    def sync_parsed_data(self, parsed_data: Dict[str, Any]) -> None:
        match_id = parsed_data.get("match_id")
        lineup = parsed_data.get("lineup")
        match_stats = parsed_data.get("match_stats")
        player_stats = parsed_data.get("player_stats")
        shot_stats = parsed_data.get('shot_stats')

        with self.db.get_session() as session:
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

            if shot_stats:
                self._sync_shot_stats(session, match_id, shot_stats)

    def _sync_lineup(self, session, match_id: int, venue: str, lineup: List[Dict[str, Any]]) -> None:
        insert_stmt = insert(MatchLineup).values(lineup)
        assignment, where_clause = self.build_upsert_clauses(
            MatchLineup,
            insert_stmt,
            {
                MatchLineup.id.key,
                MatchLineup.created_at.key,
                MatchLineup.match_id.key,
                MatchLineup.team_id.key,
                MatchLineup.member_id.key,
                MatchLineup.updated_at.key
            }
        )
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[MatchLineup.match_id.key, MatchLineup.team_id.key, MatchLineup.member_id.key],
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

    def _sync_shot_stats(self, session, match_id: int, shot_stats: List[Dict[str, Any]]) -> None:
        insert_stmt = insert(ShotStat).values(shot_stats)
        assignment, where_clause = self.build_upsert_clauses(
            ShotStat,
            insert_stmt,
            {
                ShotStat.id.key,
                ShotStat.created_at.key,
                ShotStat.match_id.key,
                ShotStat.event_id.key,
                ShotStat.updated_at.key
            }
        )
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[ShotStat.match_id.key, ShotStat.event_id.key],
            set_=assignment,
            where=where_clause
        )
        result = session.execute(insert_stmt)
        upserted_count = result.rowcount
        self.logger.debug(f"Sync match {match_id} shot stats completed. upserted: {upserted_count}")

    def get_match_detail(self, match_code: str) -> Dict[str, Any]:
        with self.db.get_session() as session:
            row = session.query(
                Fixture.match_code,
                Fixture.league_id,
                Fixture.kickoff_time,
                Fixture.round,
                Fixture.home_team,
                Fixture.home_code,
                Fixture.away_team,
                Fixture.away_code,
                Fixture.home_score,
                Fixture.away_score,
                Fixture.match_status,
                MatchRaw.json_body,
            ).join(
                Fixture, Fixture.match_id == MatchRaw.match_id
            ).filter(Fixture.match_code == match_code).first()

            if not row:
                raise ValueError("Match not found")

            return row._asdict()
