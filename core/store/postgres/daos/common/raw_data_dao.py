from typing import List, Dict, Any, Optional
from core.store.postgres.models.fotmob.match import MatchRaw
from core.store.postgres.models.oddsportal.fixture import Fixture as OddsportalFixture
from core.store.postgres.models.fotmob.fixture import Fixture as FotmobFixture, HistoryFixtureRaw, ActiveFixtureRaw
from core.store.postgres.models.oddsportal.odds import OddsRaw
from ..base_dao import BaseDao


class RawDataDao(BaseDao):
    def get_match_raw_by_code(self, match_code: str) -> Optional[Dict[str, Any]]:
        with self.db.get_session() as session:
            row = session.query(MatchRaw).join(
                FotmobFixture, FotmobFixture.match_id == MatchRaw.match_id
            ).filter(FotmobFixture.match_code == match_code).first()
            if row is None:
                return None

            return {
                "match_id":       row.match_id,
                "kickoff_time":   str(row.kickoff_time),
                "match_status":   row.match_status,
                "is_fetched":     row.is_fetched,
                "fetch_attempts": row.fetch_attempts,
                "last_fetch_error": row.last_fetch_error,
                "last_fetched_at":  row.last_fetched_at,
                "next_fetch_at":    row.next_fetch_at,
                "is_parsed":        row.is_parsed,
                "parse_attempts":   row.parse_attempts,
                "last_parse_error": row.last_parse_error,
                "last_parsed_at":   row.last_parsed_at,
                "json_body":        row.json_body,
            }

    def get_fixture_raw_by_code(self, match_code: str) -> Optional[Dict[str, Any]]:
        with self.db.get_session() as session:
            fixture = session.query(
                FotmobFixture.league_id,
                FotmobFixture.season,
                FotmobFixture.kickoff_time,
            ).filter(FotmobFixture.match_code == match_code).first()

            if fixture is None:
                return None

            active = session.query(ActiveFixtureRaw).filter(
                ActiveFixtureRaw.match_date == fixture.kickoff_time.date()
            ).first()

            history = session.query(HistoryFixtureRaw).filter(
                HistoryFixtureRaw.league_id == fixture.league_id,
                HistoryFixtureRaw.season == fixture.season,
            ).first()

            return {
                "active_fixture_raw": None if active is None else {
                    "match_date":       str(active.match_date),
                    "is_fetched":       active.is_fetched,
                    "fetch_attempts":   active.fetch_attempts,
                    "last_fetch_error": active.last_fetch_error,
                    "last_fetched_at":  active.last_fetched_at,
                    "next_fetch_at":    active.next_fetch_at,
                    "is_parsed":        active.is_parsed,
                    "parse_attempts":   active.parse_attempts,
                    "last_parse_error": active.last_parse_error,
                    "last_parsed_at":   active.last_parsed_at,
                    "json_body":        active.json_body,
                },
                "history_fixture_raw": None if history is None else {
                    "league_id":        history.league_id,
                    "season":           history.season,
                    "is_fetched":       history.is_fetched,
                    "fetch_attempts":   history.fetch_attempts,
                    "last_fetch_error": history.last_fetch_error,
                    "last_fetched_at":  history.last_fetched_at,
                    "next_fetch_at":    history.next_fetch_at,
                    "is_parsed":        history.is_parsed,
                    "parse_attempts":   history.parse_attempts,
                    "last_parse_error": history.last_parse_error,
                    "last_parsed_at":   history.last_parsed_at,
                    "json_body":        history.json_body,
                },
            }

    def get_odds_raw_by_match_code(self, match_code: str) -> Optional[List[Dict[str, Any]]]:
        with self.db.get_session() as session:
            fotmob_fixture = session.query(FotmobFixture.match_id).filter(
                FotmobFixture.match_code == match_code
            ).first()
            if fotmob_fixture is None:
                return None

            oddsportal_fixture = session.query(OddsportalFixture.match_code).filter(
                OddsportalFixture.ref_match_id == fotmob_fixture.match_id
            ).first()
            if oddsportal_fixture is None:
                return None

            raws = session.query(
                OddsRaw.match_code,
                OddsRaw.betting_type_id,
                OddsRaw.scope_id,
                OddsRaw.is_fetched,
                OddsRaw.fetch_attempts,
                OddsRaw.last_fetch_error,
                OddsRaw.last_fetched_at,
                OddsRaw.next_fetch_at,
                OddsRaw.is_parsed,
                OddsRaw.parse_attempts,
                OddsRaw.last_parse_error,
                OddsRaw.last_parsed_at,
                OddsRaw.json_body,
            ).filter(OddsRaw.match_code == oddsportal_fixture.match_code).all()
            return [row._asdict() for row in raws]
