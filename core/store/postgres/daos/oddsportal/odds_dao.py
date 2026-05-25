import traceback
from sqlalchemy import func, or_, and_, text, delete
from typing import List, Any, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.oddsportal.fixture import Fixture
from core.store.postgres.models.oddsportal.odds import OddsRaw, Odds1x2, OddsAh
from core.types.enums import SHARP_BOOKMAKER_NAMES
from ..base_dao import BaseDao


class OddsDao(BaseDao):
    def get_pending_fetch_items(self, betting_type_id: int, scope_id: int, limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                Fixture.league_id,
                Fixture.match_code,
                Fixture.home_name,
                Fixture.home_code,
                Fixture.away_name,
                Fixture.away_code,
                Fixture.kickoff_time,
                Fixture.match_url,
                OddsRaw.fetch_attempts
            ).outerjoin(
                OddsRaw,
                and_(
                    OddsRaw.match_code == Fixture.match_code,
                    OddsRaw.betting_type_id == betting_type_id,
                    OddsRaw.scope_id == scope_id,
                )
            ).filter(
                or_(
                    OddsRaw.match_code.is_(None),
                    OddsRaw.next_fetch_at <= func.now()
                )
            ).order_by(
                Fixture.kickoff_time.desc()
            ).limit(limit).all()

    def mark_as_fetched(self, match_code: str, betting_type_id: int, scope_id: int, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(OddsRaw).filter(
                OddsRaw.match_code == match_code,
                OddsRaw.betting_type_id == betting_type_id,
                OddsRaw.scope_id == scope_id,
            ).update({
                OddsRaw.is_fetched.key: True,
                OddsRaw.last_fetch_error.key: None,
                OddsRaw.last_fetched_at.key: func.now(),
                OddsRaw.next_fetch_at.key: func.now() + fetch_interval if fetch_interval is not None else None,
                OddsRaw.total_fetch_count.key: OddsRaw.total_fetch_count + 1,
                OddsRaw.fetch_attempts.key: 0,
                OddsRaw.is_parsed.key: False,
                OddsRaw.last_parse_error.key: None,
                OddsRaw.parse_attempts.key: 0,
                OddsRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_fetch_failed(self, match_code: str, betting_type_id: int, scope_id: int, kickoff_time: Optional[datetime], fetch_interval: Optional[timedelta], error_msg: Optional[str] = None) -> None:
        next_fetch_at = func.now() + fetch_interval if fetch_interval is not None else None
        if error_msg is None:
            error_msg = traceback.format_exc()

        with self.db.get_session() as session:
            insert_stmt = insert(OddsRaw).values(
                match_code=match_code,
                betting_type_id=betting_type_id,
                scope_id=scope_id,
                kickoff_time=kickoff_time,
                json_body={},
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or '')[:2000],
                total_fetch_count=1,
                next_fetch_at=next_fetch_at,
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[OddsRaw.match_code.key, OddsRaw.betting_type_id.key, OddsRaw.scope_id.key],
                set_={
                    OddsRaw.kickoff_time.key: func.coalesce(OddsRaw.kickoff_time, insert_stmt.excluded.kickoff_time),
                    OddsRaw.is_fetched.key: False,
                    OddsRaw.last_fetch_error.key: (error_msg or '')[:2000],
                    OddsRaw.fetch_attempts.key: OddsRaw.fetch_attempts + 1,
                    OddsRaw.total_fetch_count.key: OddsRaw.total_fetch_count + 1,
                    OddsRaw.next_fetch_at.key: next_fetch_at,
                    OddsRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def sync_raw_data(self, raw_data: dict) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(OddsRaw).values(raw_data)
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[OddsRaw.match_code.key, OddsRaw.betting_type_id.key, OddsRaw.scope_id.key],
                set_={
                    OddsRaw.kickoff_time.key: insert_stmt.excluded.kickoff_time,
                    OddsRaw.source_url.key: insert_stmt.excluded.source_url,
                    OddsRaw.json_body.key: insert_stmt.excluded.json_body,
                    OddsRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def get_pending_parse_items(self, betting_type_id: int, scope_id: int, max_retries: int, limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                OddsRaw.match_code,
                OddsRaw.json_body,
            ).filter(
                OddsRaw.betting_type_id == betting_type_id,
                OddsRaw.scope_id == scope_id,
                OddsRaw.is_fetched == True,
                OddsRaw.is_parsed == False,
                OddsRaw.parse_attempts < max_retries,
            ).order_by(
                OddsRaw.created_at.asc()
            ).limit(limit).all()

    def mark_as_parsed(self, match_code: str, betting_type_id: int, scope_id: int) -> None:
        with self.db.get_session() as session:
            session.query(OddsRaw).filter(
                OddsRaw.match_code == match_code,
                OddsRaw.betting_type_id == betting_type_id,
                OddsRaw.scope_id == scope_id,
            ).update({
                OddsRaw.is_parsed.key: True,
                OddsRaw.last_parse_error.key: None,
                OddsRaw.parse_attempts.key: 0,
                OddsRaw.total_parse_count.key: OddsRaw.total_parse_count + 1,
                OddsRaw.last_parsed_at.key: func.now(),
                OddsRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_parse_failed(self, match_code: str, betting_type_id: int, scope_id: int, error_msg: Optional[str] = None) -> None:
        if error_msg is None:
            error_msg = traceback.format_exc()
        with self.db.get_session() as session:
            session.query(OddsRaw).filter(
                OddsRaw.match_code == match_code,
                OddsRaw.betting_type_id == betting_type_id,
                OddsRaw.scope_id == scope_id,
            ).update({
                OddsRaw.is_parsed.key: False,
                OddsRaw.last_parse_error.key: error_msg[:2000],
                OddsRaw.parse_attempts.key: OddsRaw.parse_attempts + 1,
                OddsRaw.total_parse_count.key: OddsRaw.total_parse_count + 1,
                OddsRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def sync_parsed_1x2_data(self, records: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(Odds1x2).values(records)
            assignment, where_clause = self.build_upsert_clauses(
                Odds1x2,
                insert_stmt,
                {
                    Odds1x2.id.key,
                    Odds1x2.match_code.key,
                    Odds1x2.betting_type_id.key,
                    Odds1x2.scope_id.key,
                    Odds1x2.quote_type.key,
                    Odds1x2.bookmaker_id.key,
                    Odds1x2.created_at.key,
                    Odds1x2.updated_at.key,
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[Odds1x2.match_code.key, Odds1x2.betting_type_id.key, Odds1x2.scope_id.key, Odds1x2.bookmaker_id.key, Odds1x2.quote_type.key],
                set_=assignment,
                where=where_clause,
            )
            session.execute(insert_stmt)

    def get_match_odds_summary(self, match_ids: List[int]) -> Dict[int, Any]:
        with self.db.get_session() as session:
            result = session.execute(text("""
                WITH ah_main_per_bk AS (
                    SELECT op.ref_match_id AS match_id,
                           ah.handicap,
                           ah.closing_home_odds,
                           ah.closing_away_odds,
                           ROW_NUMBER() OVER (
                               PARTITION BY ah.match_code, ah.bookmaker_id
                               ORDER BY ABS(1.0 / ah.closing_home_odds - 1.0 / ah.closing_away_odds)
                           ) AS rn
                    FROM oddsportal.fixtures op
                    JOIN oddsportal.odds_ah ah ON ah.match_code = op.match_code
                        AND ah.betting_type_id = 5 AND ah.scope_id = 2 AND ah.quote_type = 'back'
                        AND ah.closing_home_odds > 1.0 AND ah.closing_away_odds > 1.0
                    WHERE op.ref_match_id = ANY(:match_ids)
                ),
                ah_main AS (
                    SELECT * FROM ah_main_per_bk WHERE rn = 1
                ),
                ah_mode AS (
                    SELECT match_id,
                           handicap AS main_line,
                           ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY COUNT(*) DESC) AS rn
                    FROM ah_main
                    GROUP BY match_id, handicap
                ),
                odds_1x2_agg AS (
                    SELECT op.ref_match_id AS match_id,
                           ROUND(AVG(ox.closing_home_odds)::numeric, 2) AS avg_home_odds,
                           ROUND(AVG(ox.closing_draw_odds)::numeric,  2) AS avg_draw_odds,
                           ROUND(AVG(ox.closing_away_odds)::numeric,  2) AS avg_away_odds
                    FROM oddsportal.fixtures op
                    JOIN oddsportal.odds_1x2 ox ON ox.match_code = op.match_code
                        AND ox.betting_type_id = 1 AND ox.scope_id = 2 AND ox.quote_type = 'back'
                        AND ox.closing_home_odds > 1.0 AND ox.closing_draw_odds > 1.0 AND ox.closing_away_odds > 1.0
                    WHERE op.ref_match_id = ANY(:match_ids)
                    GROUP BY op.ref_match_id
                ),
                ah_agg AS (
                    SELECT m.match_id,
                           m.main_line AS ah_main_line,
                           ROUND(AVG(a.closing_home_odds)::numeric, 2) AS avg_ah_home_odds,
                           ROUND(AVG(a.closing_away_odds)::numeric,  2) AS avg_ah_away_odds
                    FROM ah_mode m
                    JOIN ah_main a ON a.match_id = m.match_id AND a.handicap = m.main_line
                    WHERE m.rn = 1
                    GROUP BY m.match_id, m.main_line
                )
                SELECT o.match_id,
                       o.avg_home_odds,
                       o.avg_draw_odds,
                       o.avg_away_odds,
                       a.ah_main_line,
                       a.avg_ah_home_odds,
                       a.avg_ah_away_odds
                FROM odds_1x2_agg o
                LEFT JOIN ah_agg a ON a.match_id = o.match_id
            """), {"match_ids": match_ids})
            return {row.match_id: row._asdict() for row in result.fetchall()}

    def sync_parsed_ah_data(self, match_code: str, betting_type_id: int, scope_id: int, records: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
            session.execute(
                delete(OddsAh).where(
                    OddsAh.match_code == match_code,
                    OddsAh.betting_type_id == betting_type_id,
                    OddsAh.scope_id == scope_id,
                )
            )
            session.execute(insert(OddsAh).values(records))

    def get_match_odds_detail(self, match_id: int) -> Optional[Dict[str, Any]]:
        sharp_ids = list(SHARP_BOOKMAKER_NAMES.keys())
        with self.db.get_session() as session:
            match_code_row = session.execute(
                text("SELECT match_code FROM oddsportal.fixtures WHERE ref_match_id = :match_id"),
                {"match_id": match_id}
            ).fetchone()
            if match_code_row is None:
                return None
            match_code = match_code_row[0]

            one_x_two_avg_row = session.execute(text("""
                SELECT
                    ROUND(AVG(opening_home_odds)::numeric, 2) AS avg_open_home,
                    ROUND(AVG(opening_draw_odds)::numeric, 2) AS avg_open_draw,
                    ROUND(AVG(opening_away_odds)::numeric, 2) AS avg_open_away,
                    ROUND(AVG(closing_home_odds)::numeric, 2) AS avg_close_home,
                    ROUND(AVG(closing_draw_odds)::numeric, 2) AS avg_close_draw,
                    ROUND(AVG(closing_away_odds)::numeric, 2) AS avg_close_away
                FROM oddsportal.odds_1x2
                WHERE match_code = :match_code
                    AND betting_type_id = 1 AND scope_id = 2 AND quote_type = 'back'
                    AND closing_home_odds > 1.0 AND closing_draw_odds > 1.0 AND closing_away_odds > 1.0
            """), {"match_code": match_code}).fetchone()

            one_x_two_sharp_rows = session.execute(text("""
                SELECT
                    bookmaker_id,
                    ROUND(opening_home_odds::numeric, 2) AS open_home,
                    ROUND(opening_draw_odds::numeric, 2) AS open_draw,
                    ROUND(opening_away_odds::numeric, 2) AS open_away,
                    ROUND(closing_home_odds::numeric, 2) AS close_home,
                    ROUND(closing_draw_odds::numeric, 2) AS close_draw,
                    ROUND(closing_away_odds::numeric, 2) AS close_away,
                    home_movement,
                    draw_movement,
                    away_movement,
                    closing_home_change_time AS home_change_time,
                    closing_draw_change_time AS draw_change_time,
                    closing_away_change_time AS away_change_time
                FROM oddsportal.odds_1x2
                WHERE match_code = :match_code
                    AND betting_type_id = 1 AND scope_id = 2 AND quote_type = 'back'
                    AND bookmaker_id = ANY(:sharp_ids)
                ORDER BY bookmaker_id
            """), {"match_code": match_code, "sharp_ids": sharp_ids}).fetchall()

            ah_market_row = session.execute(text("""
                WITH ah_close_main_per_bk AS (
                    SELECT
                        bookmaker_id,
                        handicap,
                        ROW_NUMBER() OVER (
                            PARTITION BY bookmaker_id
                            ORDER BY ABS(1.0 / closing_home_odds - 1.0 / closing_away_odds)
                        ) AS rn
                    FROM oddsportal.odds_ah
                    WHERE match_code = :match_code
                        AND betting_type_id = 5 AND scope_id = 2 AND quote_type = 'back'
                        AND closing_home_odds > 1.0 AND closing_away_odds > 1.0
                ),
                global_main_line AS (
                    SELECT handicap AS main_line
                    FROM ah_close_main_per_bk
                    WHERE rn = 1
                    GROUP BY handicap
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                )
                SELECT
                    (SELECT main_line FROM global_main_line) AS main_line,
                    ROUND(AVG(ah.opening_home_odds)::numeric, 2) AS avg_open_home,
                    ROUND(AVG(ah.opening_away_odds)::numeric, 2) AS avg_open_away,
                    ROUND(AVG(ah.closing_home_odds)::numeric, 2) AS avg_close_home,
                    ROUND(AVG(ah.closing_away_odds)::numeric, 2) AS avg_close_away
                FROM oddsportal.odds_ah ah
                WHERE ah.match_code = :match_code
                    AND ah.betting_type_id = 5 AND ah.scope_id = 2 AND ah.quote_type = 'back'
                    AND ah.handicap = (SELECT main_line FROM global_main_line)
                    AND ah.closing_home_odds > 1.0 AND ah.closing_away_odds > 1.0
            """), {"match_code": match_code}).fetchone()

            ah_sharp_rows = session.execute(text("""
                WITH ah_close_main AS (
                    SELECT
                        bookmaker_id,
                        handicap AS close_line,
                        closing_home_odds,
                        closing_away_odds,
                        home_movement,
                        away_movement,
                        closing_home_change_time,
                        closing_away_change_time,
                        ROW_NUMBER() OVER (
                            PARTITION BY bookmaker_id
                            ORDER BY ABS(1.0 / closing_home_odds - 1.0 / closing_away_odds)
                        ) AS rn
                    FROM oddsportal.odds_ah
                    WHERE match_code = :match_code
                        AND betting_type_id = 5 AND scope_id = 2 AND quote_type = 'back'
                        AND bookmaker_id = ANY(:sharp_ids)
                        AND closing_home_odds > 1.0 AND closing_away_odds > 1.0
                ),
                ah_open_main AS (
                    SELECT
                        bookmaker_id,
                        handicap AS open_line,
                        opening_home_odds,
                        opening_away_odds,
                        ROW_NUMBER() OVER (
                            PARTITION BY bookmaker_id
                            ORDER BY ABS(1.0 / opening_home_odds - 1.0 / opening_away_odds)
                        ) AS rn
                    FROM oddsportal.odds_ah
                    WHERE match_code = :match_code
                        AND betting_type_id = 5 AND scope_id = 2 AND quote_type = 'back'
                        AND bookmaker_id = ANY(:sharp_ids)
                        AND opening_home_odds > 1.0 AND opening_away_odds > 1.0
                )
                SELECT
                    c.bookmaker_id,
                    o.open_line,
                    ROUND(o.opening_home_odds::numeric, 2) AS open_home,
                    ROUND(o.opening_away_odds::numeric, 2) AS open_away,
                    c.close_line,
                    ROUND(c.closing_home_odds::numeric, 2) AS close_home,
                    ROUND(c.closing_away_odds::numeric, 2) AS close_away,
                    c.home_movement,
                    c.away_movement,
                    c.closing_home_change_time AS home_change_time,
                    c.closing_away_change_time AS away_change_time
                FROM ah_close_main c
                LEFT JOIN ah_open_main o ON o.bookmaker_id = c.bookmaker_id AND o.rn = 1
                WHERE c.rn = 1
                ORDER BY c.bookmaker_id
            """), {"match_code": match_code, "sharp_ids": sharp_ids}).fetchall()

            one_x_two_bookmakers = [
                {
                    "name": SHARP_BOOKMAKER_NAMES[row.bookmaker_id],
                    "open_home": row.open_home,
                    "open_draw": row.open_draw,
                    "open_away": row.open_away,
                    "close_home": row.close_home,
                    "close_draw": row.close_draw,
                    "close_away": row.close_away,
                    "home_movement": row.home_movement,
                    "draw_movement": row.draw_movement,
                    "away_movement": row.away_movement,
                    "home_change_time": row.home_change_time,
                    "draw_change_time": row.draw_change_time,
                    "away_change_time": row.away_change_time,
                }
                for row in one_x_two_sharp_rows
            ]

            ah_bookmakers = [
                {
                    "name": SHARP_BOOKMAKER_NAMES[row.bookmaker_id],
                    "open_line": row.open_line,
                    "open_home": row.open_home,
                    "open_away": row.open_away,
                    "close_line": row.close_line,
                    "close_home": row.close_home,
                    "close_away": row.close_away,
                    "home_movement": row.home_movement,
                    "away_movement": row.away_movement,
                    "home_change_time": row.home_change_time,
                    "away_change_time": row.away_change_time,
                }
                for row in ah_sharp_rows
            ]

            one_x_two = None
            if one_x_two_avg_row and one_x_two_avg_row.avg_close_home is not None:
                one_x_two = {
                    "avg_open_home": one_x_two_avg_row.avg_open_home,
                    "avg_open_draw": one_x_two_avg_row.avg_open_draw,
                    "avg_open_away": one_x_two_avg_row.avg_open_away,
                    "avg_close_home": one_x_two_avg_row.avg_close_home,
                    "avg_close_draw": one_x_two_avg_row.avg_close_draw,
                    "avg_close_away": one_x_two_avg_row.avg_close_away,
                    "bookmakers": one_x_two_bookmakers,
                }

            ah = None
            if ah_market_row and ah_market_row.main_line is not None:
                ah = {
                    "main_line": ah_market_row.main_line,
                    "avg_open_home": ah_market_row.avg_open_home,
                    "avg_open_away": ah_market_row.avg_open_away,
                    "avg_close_home": ah_market_row.avg_close_home,
                    "avg_close_away": ah_market_row.avg_close_away,
                    "bookmakers": ah_bookmakers,
                }

            if one_x_two is None and ah is None:
                return None
            return {"one_x_two": one_x_two, "ah": ah}
