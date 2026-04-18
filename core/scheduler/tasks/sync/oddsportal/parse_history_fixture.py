from pathlib import PurePosixPath
from core.registry import Registry
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from core.types.params import CrawlParams
from core.scheduler.tasks.poll_task import PollTask
from core.store.postgres.daos.oddsportal import HistoryFixtureDao, FixtureDao
from core.logger.logger_manager import LoggerManager

class HistoryFixtureParser:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def parse(self, json_body: Dict[str, Any], league_id: int, season: int) -> Optional[List[Dict[str, Any]]]:
        rows = json_body.get("d", {}).get("rows", [])
        if not rows:
            self.logger.error("rows is empty")
            return None

        seen = set()
        results = []
        for row in rows:
            match_id = row.get("id")
            if not match_id:
                self.logger.error("match_id is missing in row")
                continue

            ts = row.get("date-start-timestamp")
            if not ts:
                self.logger.error(f"date-start-timestamp is missing for match_id={match_id}")
                continue

            if match_id in seen:
                continue

            seen.add(match_id)
            results.append({
                "match_id": match_id,
                "league_id": league_id,
                "season": season,
                "home_id": row.get("home"),
                "away_id": row.get("away"),
                "home_name": row.get("home-name"),
                "away_name": row.get("away-name"),
                "match_url": row.get("url"),
                "match_code": row.get("encodeEventId"),
                "home_url": row.get("homeParticipantUrl"),
                "home_code": PurePosixPath(row.get("homeParticipantUrl", "")).name,
                "away_url": row.get("awayParticipantUrl"),
                "away_code": PurePosixPath(row.get("awayParticipantUrl", "")).name,
                "kickoff_time": datetime.fromtimestamp(ts, tz=timezone.utc),
            })
        return results


@Registry.poll('parse.oddsportal.history_fixture')
class ParseHistoryFixture(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.history_fixture_dao = HistoryFixtureDao()
        self.fixture_dao = FixtureDao()
        self.parser = HistoryFixtureParser()

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.history_fixture_dao.get_pending_parse_items(CrawlParams.PARSE_MAX_RETRIES, CrawlParams.RAW_DATA_QUERY_LIMIT)

                if not items:
                    self.idle_sleep()
                    continue

                for league_id, season, page, json_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_fixtures = self.parser.parse(json_body, league_id, season)
                        if parsed_fixtures is None:
                            self.history_fixture_dao.mark_parse_failed(league_id, season, page, "Parsed fixtures is None")
                            self.logger.error(f"Failed to parse fixture league_id={league_id} season={season} page={page}: fixtures is None")
                            continue

                        if not parsed_fixtures:
                            self.history_fixture_dao.mark_parse_failed(league_id, season, page, "Parsed fixtures is empty")
                            self.logger.error(f"Failed to parse fixture league_id={league_id} season={season} page={page}: fixtures is empty")
                            continue

                        self.fixture_dao.sync_parsed_data(parsed_fixtures)
                        self.history_fixture_dao.mark_as_parsed(league_id, season, page)
                        self.logger.info(f"Parsed fixture league_id={league_id} season={season} page={page} count={len(parsed_fixtures)}")

                    except Exception as e:
                        self.history_fixture_dao.mark_parse_failed(league_id, season, page)
                        self.logger.error(f"Failed to parse fixture league_id={league_id} season={season} page={page}: {e}")

            except Exception as e:
                self.logger.error(f"Parse fixture loop error: {e}", exc_info=True)
                self.idle_sleep()
