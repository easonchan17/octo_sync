import re
import traceback
from typing import Any, Dict, Optional, Tuple
from core.registry import Registry
from core.types.params import CrawlParams
from core.scheduler.tasks.poll_task import PollTask
from core.store.postgres.daos.oddsportal import SeasonDao
from core.logger.logger_manager import LoggerManager


class SeasonParser:
    SEASON_PATTERN = re.compile(r'<a\s[^>]*href="https://www\.oddsportal\.com/football/[^"]+/results/"[^>]*>\s*(\d{4})/\d{4}\s*</a>')

    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def parse(self, html_body: str) -> Optional[Tuple[int, int]]:
        if not html_body:
            self.logger.error("html body is empty")
            return None

        seasons = [int(m.group(1)) for m in self.SEASON_PATTERN.finditer(html_body)]
        if not seasons:
            self.logger.error("no season links found in html")
            return None

        return min(seasons), max(seasons)


@Registry.poll('parse.oddsportal.season')
class ParseSeason(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.season_dao = SeasonDao()
        self.parser = SeasonParser()

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.season_dao.get_pending_parse_items(
                    CrawlParams.PARSE_MAX_RETRIES, CrawlParams.RAW_DATA_QUERY_LIMIT
                )

                if not items:
                    self.idle_sleep()
                    continue

                for league_id, league_name, html_body in items:
                    if self.should_stop():
                        return

                    try:
                        season_range = self.parser.parse(html_body)
                        if season_range is None:
                            self.season_dao.mark_parse_failed(league_id, "No seasons found")
                            self.logger.error(f"Failed to parse season league_id={league_id} league_name={league_name}: no seasons found")
                            continue

                        min_season, max_season = season_range
                        self.season_dao.sync_parsed_data(league_id, min_season, max_season)
                        self.season_dao.mark_as_parsed(league_id)
                        self.logger.info(f"Parsed season league_id={league_id} min={min_season} max={max_season}")

                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.season_dao.mark_parse_failed(league_id, full_stack_trace)
                        self.logger.error(f"Failed to parse season league_id={league_id}: {e}")

            except Exception as e:
                self.logger.error(f"Parse season loop error: {e}", exc_info=True)
                self.idle_sleep()
