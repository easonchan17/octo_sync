import traceback
from core.registry import Registry
from core.types.enums import SiteName
from typing import Any, Dict, Optional, List
from core.services.league import league_service
from core.types.params import LeagueCrawlParams
from core.scheduler.tasks.poll_task import PollTask
from core.store.postgres.daos.pinnacle import LeagueDao

class LeagueParser:
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

@Registry.poll('parse.pinnacle.league')
class ParseLeague(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.league_dao = LeagueDao()
        self.parser = LeagueParser()

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.league_dao.get_pending_parse_items(
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
                            self.league_dao.mark_parse_failed(sport_id, "Parsed leagues is None")
                            continue

                        for league in parsed_leagues:
                            league_service.resolve(
                                SiteName.PINNACLE.value,
                                league["league_id"],
                                league["league_name"],
                                country_name=league["country_name"]
                            )

                        self.league_dao.mark_as_parsed(sport_id)
                        self.logger.info(f"Parsed raw leagues sport_id={sport_id} count={len(parsed_leagues)}")

                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.league_dao.mark_parse_failed(sport_id, full_stack_trace)
                        self.logger.error(f"Failed to parse raw leagues sport_id={sport_id}: {e}")


            except Exception as e:
                self.logger.error(f"Parse loop error: {e}", exc_info=True)
                self.idle_sleep()
