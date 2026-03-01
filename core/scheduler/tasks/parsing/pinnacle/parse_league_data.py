import traceback
from core.registry import Registry
from core.types.enums import SiteName
from core.store.postgres.models import Site
from typing import Any, Dict, Optional, List
from core.services.league import league_service
from core.types.params import LeagueCrawlParams
from core.scheduler.tasks.poll_task import PollTask
from core.scheduler.synchronizers.pinnacle.league_data_synchronizer import LeagueDataSynchronizer

class LeagueDataParser:
    def parse(self, raw_data: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        if not raw_data:
            return None

        results = []
        for item in raw_data:
            results.append({
                "league_id": item.get("id"),
                "league_name": item.get("name"),
                "country_name": item.get("group")
            })
        return results

@Registry.poll('parse.pinnacle.league_data')
class ParseLeagueData(PollTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = LeagueDataSynchronizer()
        self.parser = LeagueDataParser()

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.synchronizer.get_pending_parse_items(
                    self.site,
                    LeagueCrawlParams.PARSE_MAX_RETRIES
                )

                if not items:
                    self.idle_sleep()
                    continue

                for sport_id, json_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_leagues = self.parser.parse(json_body)
                        if parsed_leagues is None:
                            self.synchronizer.mark_parse_failed(self.site, sport_id, "Parsed leagues is None")
                            continue

                        for league in parsed_leagues:
                            league_service.resolve(
                                SiteName.PINNACLE.value,
                                league["league_id"],
                                league["league_name"],
                                country_name=league["country_name"]
                            )

                        self.synchronizer.mark_as_parsed(self.site, sport_id)
                        self.logger.info(f"Parsed raw leagues sport_id={sport_id} count={len(parsed_leagues)}")

                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.synchronizer.mark_parse_failed(self.site, sport_id, full_stack_trace)
                        self.logger.error(f"Failed to parse raw leagues sport_id={sport_id}: {e}")


            except Exception as e:
                self.logger.error(f"Parse loop error: {e}", exc_info=True)
                self.idle_sleep()
