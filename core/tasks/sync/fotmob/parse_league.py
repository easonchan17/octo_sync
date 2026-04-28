from typing import Any, Dict, Optional, List
from core.scheduler.task_registry import TaskRegistry
from core.tasks.poll_task import PollTask, CrawlParams
from core.store.postgres.daos.fotmob import LeagueDao
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

        seen = set()
        results = []

        for section_key, section_data in json_data.items():
            if section_key == "popular":
                continue

            for country_group in section_data:
                country_name = country_group.get("name")
                country_code = country_group.get("ccode")
                leagues = country_group.get("leagues", [])

                for league in leagues:
                    league_id = league.get("id")

                    if league_id is None or league_id in seen:
                        continue

                    seen.add(league_id)
                    results.append({
                        "league_id": league_id,
                        "league_name": league.get("name"),
                        "page_url": league.get("pageUrl", ""),
                        "country_name": country_name,
                        "country_code": country_code
                    })

        return results


@TaskRegistry.poll('parse.fotmob.league')
class ParseLeague(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.FOTMOB.value)
        self.payload = payload or {}
        self.league_dao = LeagueDao()
        self.parser = LeagueParser()

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.league_dao.get_pending_parse_items(CrawlParams.PARSE_MAX_RETRIES, CrawlParams.PARSE_BATCH_SIZE)

                if not items:
                    self.idle_sleep()
                    continue

                for sport, json_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_leagues = self.parser.parse(json_body)
                        if not parsed_leagues:
                            self.league_dao.mark_parse_failed(sport, "Parsed leagues is empty")
                            continue

                        self.league_dao.sync_parsed_data(parsed_leagues)

                        for league in parsed_leagues:
                            league_service.resolve(
                                SiteName.FOTMOB.value,
                                str(league["league_id"]),
                                league["league_name"],
                                country_name=league["country_name"],
                                country_code=league["country_code"]
                            )

                        self.league_dao.mark_as_parsed(sport)
                        self.logger.info(f"Parsed raw leagues sport={sport} count={len(parsed_leagues)}")

                    except Exception as e:
                        self.league_dao.mark_parse_failed(sport)
                        self.logger.error(f"Failed to parse raw leagues sport={sport}: {e}")

            except Exception as e:
                self.logger.error(f"Parse loop error: {e}", exc_info=True)
                self.idle_sleep()
