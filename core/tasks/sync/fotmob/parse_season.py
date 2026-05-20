import re
from typing import Any, Dict, List, Optional, Tuple
from core.scheduler.task_registry import TaskRegistry
from core.tasks.poll_task import PollTask
from core.types.params import CrawlParams
from core.store.postgres.daos.fotmob import SeasonDao
from core.logger.logger_manager import get_logger_manager
from core.types.enums import SiteName


class SeasonParser:
    SEASON_PATTERN = re.compile(r'^(\d{4})')

    def __init__(self) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)

    def parse(self, json_data: Dict[str, Any]) -> Optional[Tuple[int, int, List[int]]]:
        if not json_data:
            self.logger.error("json data is empty")
            return None

        available_seasons = json_data.get("allAvailableSeasons", [])
        if not available_seasons:
            self.logger.error("allAvailableSeasons is empty")
            return None

        seasons = sorted({int(m.group(1)) for season in available_seasons if (m := self.SEASON_PATTERN.match(season))})
        if not seasons:
            self.logger.error("no valid seasons found")
            return None

        return seasons[0], seasons[-1], seasons


@TaskRegistry.poll('parse.fotmob.season')
class ParseSeason(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.FOTMOB.value)
        self.payload = payload or {}
        self.season_dao = SeasonDao()
        self.parser = SeasonParser()

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.season_dao.get_pending_parse_items(
                    CrawlParams.PARSE_MAX_RETRIES, CrawlParams.PARSE_BATCH_SIZE
                )

                if not items:
                    self.idle_sleep()
                    continue

                for league_id, league_name, json_body in items:
                    if self.should_stop():
                        return

                    try:
                        season_range = self.parser.parse(json_body)
                        if season_range is None:
                            self.season_dao.mark_parse_failed(league_id, "No seasons found")
                            self.logger.error(f"Failed to parse season league_id={league_id} league_name={league_name}: no seasons found")
                            continue

                        min_season, max_season, valid_seasons = season_range
                        self.season_dao.sync_parsed_data(league_id, min_season, max_season, valid_seasons)
                        self.season_dao.mark_as_parsed(league_id)
                        self.logger.info(f"Parsed season league_id={league_id} min={min_season} max={max_season}")

                    except Exception as e:
                        self.season_dao.mark_parse_failed(league_id)
                        self.logger.error(f"Failed to parse season league_id={league_id}: {e}")

            except Exception as e:
                self.logger.error(f"Parse season loop error: {e}", exc_info=True)
                self.idle_sleep()
