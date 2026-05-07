from datetime import datetime
from typing import Any, Dict, List, Optional
from core.scheduler.task_registry import TaskRegistry
from core.tasks.poll_task import PollTask
from core.types.params import CrawlParams
from core.store.postgres.daos.fotmob import HistoryFixtureDao
from core.logger.logger_manager import LoggerManager
from core.tasks.sync.fotmob.utils import extract_status
from core.types.enums import SiteName


class HistoryFixtureParser:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def parse(self, json_data: Dict[str, Any], league_id: int, season: int) -> Optional[List[Dict[str, Any]]]:
        all_matches = json_data.get("fixtures", {}).get("allMatches", [])
        if not all_matches:
            self.logger.error("allMatches is empty")
            return None

        league_name = json_data.get("details", {}).get("name")

        seen = set()
        results = []
        for match in all_matches:
            match_id = match.get("id")
            if not match_id:
                self.logger.error("match_id is missing in match")
                continue

            match_id = int(match_id)
            if match_id in seen:
                continue

            status = match.get("status", {})
            match_status, kickoff_time, home_score, away_score = extract_status(status, CrawlParams.MATCH_LIFESPAN)
            if not kickoff_time:
                self.logger.error(f"kickoff_time is missing for match_id={match_id}")
                continue

            seen.add(match_id)
            results.append({
                "match_id": match_id,
                "league_id": league_id,
                "league_name": league_name,
                "season": season,
                "round": match.get("round"),
                "page_url": match.get("pageUrl"),
                "home_id": int(match["home"]["id"]),
                "home_team": match["home"]["name"],
                "away_id": int(match["away"]["id"]),
                "away_team": match["away"]["name"],
                "kickoff_time": datetime.fromisoformat(kickoff_time.replace("Z", "+00:00")),
                "home_score": home_score,
                "away_score": away_score,
                "match_status": match_status,
            })

        return results if results else None


@TaskRegistry.poll('parse.fotmob.history_fixture')
class ParseHistoryFixture(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.FOTMOB.value)
        self.payload = payload or {}
        self.history_fixture_dao = HistoryFixtureDao()
        self.parser = HistoryFixtureParser()

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.history_fixture_dao.get_pending_parse_items(CrawlParams.PARSE_MAX_RETRIES, CrawlParams.PARSE_BATCH_SIZE)

                if not items:
                    self.idle_sleep()
                    continue

                for league_id, season, json_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_fixtures = self.parser.parse(json_body, league_id, season)
                        if not parsed_fixtures:
                            self.history_fixture_dao.mark_parse_failed(league_id, season, "Parsed fixtures is empty")
                            self.logger.error(f"Failed to parse history fixture league_id={league_id} season={season}: fixtures is empty")
                            continue

                        self.history_fixture_dao.sync_parsed_data(league_id, parsed_fixtures)
                        self.history_fixture_dao.mark_as_parsed(league_id, season)
                        self.logger.info(f"Parsed history fixture league_id={league_id} season={season} count={len(parsed_fixtures)}")

                    except Exception as e:
                        self.history_fixture_dao.mark_parse_failed(league_id, season)
                        self.logger.error(f"Failed to parse history fixture league_id={league_id} season={season}: {e}")

            except Exception as e:
                self.logger.error(f"Parse history fixture loop error: {e}", exc_info=True)
                self.idle_sleep()
