import re
import traceback
from core.registry import Registry
from core.types.enums import SiteName
from core.store.postgres.models import Site
from core.browser.interceptor import TaskType
from typing import Any, Dict, Optional, List
from core.services.league import league_service
from datetime import datetime, timedelta, timezone
from core.scheduler.tasks.poll_task import PollTask
from core.browser.intercept_policy import InterceptPolicy
from core.browser.intercept_result_set import InterceptResultSet
from core.scheduler.synchronizers.pinnacle.match_odds_synchronizer import MatchOddsSynchronizer
from core.scheduler.synchronizers.fotmob.fixture_data_synchronizer import FixtureDataSynchronizer
from core.browser.components.receivers.common.json_receiver import JsonReceiver
from core.types.enums import LeaguePriority
from core.types.params import OddsCrawlParams


@Registry.poll('sync.pinnacle.odds')
class SyncUpcomingOdds(PollTask):
    POLICY_CONFIG = {
        "url_template": "https://www.pinnacle.com/en/soccer/{league_slug}/matchups/#all",
        "debug": False,
        "rules": [
            {
                "type": "http",
                "pattern": "https://guest.api.arcadia.pinnacle.com/.*/leagues/.*/matchups",
                "receiver": JsonReceiver
            },
            {
                "type": "http",
                "pattern": "https://guest.api.arcadia.pinnacle.com/.*/leagues/.*/markets/straight",
                "receiver": JsonReceiver
            }
        ]
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = MatchOddsSynchronizer()
        self.fixture_synchronizer = FixtureDataSynchronizer()
        self.intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

    def build_league_slug(self, league_name: str) -> str:
        return re.sub(r'[^a-z0-9]+', '-', league_name.lower()).strip('-')

    def get_pending_fetch_items(self) -> List[Any]:
        fotmob_leagues = league_service.get_site_leagues(
            SiteName.FOTMOB.value, LeaguePriority.LEVEL_REGIONAL.value
        )
        fotmob_league_id_map = {int(league.league_id): league.ref_league_id for league in fotmob_leagues}

        fotmob_fixtures = self.fixture_synchronizer.get_league_next_fixtures(
            SiteName.FOTMOB.value,
            league_ids=list(fotmob_league_id_map.keys()),
            lookahead_hours=OddsCrawlParams.EARLY_HOURS_TO_KICKOFF
        )
        sys_league_id_to_fixture = {
            fotmob_league_id_map[int(record.league_id)]: record
            for record in fotmob_fixtures
        }

        pinnacle_leagues = league_service.get_site_leagues(
            SiteName.PINNACLE.value, LeaguePriority.LEVEL_REGIONAL.value
        )
        pinnacle_league_id_map  = {int(league.league_id): league.ref_league_id for league in pinnacle_leagues}
        pinnacle_league_map = {league.ref_league_id: league for league in pinnacle_leagues}

        odds_records = self.synchronizer.get_synced_items(
            self.site,
            league_ids=list(pinnacle_league_id_map.keys())
        )
        sys_league_id_to_odds = {
            pinnacle_league_id_map[int(record.league_id)]: record
            for record in odds_records
        }

        now = datetime.now(timezone.utc)

        early_phase_checkpoint = now + timedelta(hours=OddsCrawlParams.EARLY_HOURS_TO_KICKOFF)
        observation_phase_checkpoint = now + timedelta(hours=OddsCrawlParams.OBSERVATION_HOURS_TO_KICKOFF)
        active_phase_checkpoint = now + timedelta(hours=OddsCrawlParams.ACTIVE_HOURS_TO_KICKOFF)

        early_refresh_checkpoint = now - timedelta(hours=OddsCrawlParams.EARLY_REFRESH_INTERVAL_HOURS)
        observation_refresh_checkpoint = now - timedelta(hours=OddsCrawlParams.OBSERVATION_REFRESH_INTERVAL_HOURS)
        active_refresh_checkpoint = now - timedelta(minutes=OddsCrawlParams.ACTIVE_REFRESH_INTERVAL_MINUTES)

        items = []

        for sys_league_id, fixture in sys_league_id_to_fixture.items():
            pinnacle_league = pinnacle_league_map.get(sys_league_id)
            if pinnacle_league is None:
                continue

            need_fetch = False

            odds = sys_league_id_to_odds.get(sys_league_id)
            if odds is None or odds.last_fetched_at is None:
                need_fetch = True
            else:
                if fixture.kickoff_time < active_phase_checkpoint:
                    if odds.last_fetched_at < active_refresh_checkpoint:
                        need_fetch = True
                elif fixture.kickoff_time < observation_phase_checkpoint:
                    if odds.last_fetched_at < observation_refresh_checkpoint:
                        need_fetch = True
                elif fixture.kickoff_time < early_phase_checkpoint:
                    if odds.last_fetched_at < early_refresh_checkpoint:
                        need_fetch = True

            if need_fetch:
                items.append(pinnacle_league)

        return items

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.get_pending_fetch_items()
                if not items:
                    self.idle_sleep()
                    continue

                for item in items:
                    if self.should_stop():
                        return

                    league_id = item.league_id
                    league_name = item.league_name

                    league_slug = self.build_league_slug(league_name)
                    page_url = self.intercept_policy.url.format(league_slug=league_slug)

                    try:
                        future = self.interceptor.submit_task(
                            TaskType.OPEN_PAGE,
                            url=page_url,
                            intercept_policy=self.intercept_policy
                        )

                        result_set: Optional[InterceptResultSet] = future.result()
                        if result_set is None:
                            self.logger.error(f"No response for {page_url}")
                            self.synchronizer.mark_fetch_failed(self.site, league_id, "No response")
                            continue

                        if result_set.is_empty():
                            self.logger.error(f"No odds data for {page_url}")
                            self.synchronizer.mark_fetch_failed(self.site, league_id, "No data")
                            continue

                        if result_set.is_not_modified():
                            self.logger.warning(f"Odds data is not modified for {page_url}")
                            self.synchronizer.mark_as_not_modified(self.site, league_id)
                            continue

                        self.synchronizer.sync_raw_data(
                            self.site, {
                                "source_url": page_url,
                                "league_id": league_id,
                                "json_body": result_set.to_dict(keys=["matchups", "odds"])
                            }
                        )
                        self.synchronizer.mark_as_fetched(self.site, league_id)
                        self.logger.info(f"Synced raw odds for league_id={league_id} league_name={league_name}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.synchronizer.mark_fetch_failed(self.site, league_id, full_stack_trace)
                        self.logger.error(f"Failed to sync odds for {league_name}: {e}")
                        self.idle_sleep()

            except Exception as e:
                self.logger.error(f"Sync loop error: {e}", exc_info=True)
                self.idle_sleep()
