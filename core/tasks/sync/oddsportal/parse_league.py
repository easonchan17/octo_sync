from typing import Any, Dict, Optional, List
from core.scheduler.task_registry import TaskRegistry
from core.tasks.poll_task import PollTask, CrawlParams
from core.store.postgres.daos.oddsportal import LeagueDao
from core.logger.logger_manager import LoggerManager
from core.services.league import league_service
from core.types.enums import SiteName

class LeagueParser:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def parse(self, json_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        if not json_data:
            self.logger.error("json data is empty")
            return None

        football_all = json_data.get("d", {}).get("football_all")
        if not football_all:
            self.logger.error("football all is empty")
            return None

        seen = set()
        results = []
        for country_name, country_data in football_all.items():
            country_code = country_data.get("two-chart-code")
            tournaments = country_data.get("tournaments", [])

            for tournament in tournaments:
                league_id = str(tournament.get("tournament-id"))
                if league_id in seen:
                    continue

                seen.add(league_id)
                results.append({
                    "league_id": league_id,
                    "league_name": tournament.get("name"),
                    "page_url": tournament.get("url"),
                    "country_name": country_name,
                    "country_code": country_code,
                })

        return results


@TaskRegistry.poll('parse.oddsportal.league')
class ParseLeague(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.ODDSPORTAL.value)
        self.payload = payload or {}
        self.league_dao = LeagueDao()
        self.parser = LeagueParser()

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.league_dao.get_pending_parse_items(CrawlParams.PARSE_MAX_RETRIES, CrawlParams.RAW_DATA_QUERY_LIMIT)

                if not items:
                    self.idle_sleep()
                    continue

                for sport, json_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_leagues = self.parser.parse(json_body)
                        if parsed_leagues is None:
                            self.league_dao.mark_parse_failed(sport, "Parsed leagues is None")
                            continue

                        self.league_dao.sync_parsed_data(parsed_leagues)

                        for league in parsed_leagues:
                            league_service.resolve(
                                SiteName.ODDSPORTAL.value,
                                league["league_id"],
                                league["league_name"],
                                country_name=league["country_name"],
                                country_code=league["country_code"]
                            )

                        self.league_dao.mark_as_parsed(sport)
                        self.logger.debug(f"Parsed raw leagues sport={sport} count={len(parsed_leagues)}")

                    except Exception as e:
                        self.league_dao.mark_parse_failed(sport)
                        self.logger.error(f"Failed to parse raw leagues sport={sport}: {e}")

            except Exception as e:
                self.logger.error(f"Parse loop error: {e}", exc_info=True)
                self.idle_sleep()
