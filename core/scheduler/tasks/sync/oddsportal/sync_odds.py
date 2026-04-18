from core.registry import Registry
from typing import Any, Dict, Optional, List
from core.browser.interceptor import TaskType
from core.scheduler.tasks.poll_task import PollTask
from core.store.postgres.daos.oddsportal import OddsDao
from core.browser.intercept_policy import InterceptPolicy, InterceptType
from core.scheduler.refetch_strategy import TimelineRefetchStrategy, AttemptRefetchStrategy
from datetime import datetime, timezone, timedelta
from core.types.params import CrawlParams
from core.types.enums import OddsMarkets

class BaseSyncOdds(PollTask):
    HOOK_SCRIPT = """(function() {
        var _origParse = JSON.parse;
        JSON.parse = function(text, reviver) {
            var result = _origParse.call(this, text, reviver);
            try {
                if (result && typeof result === 'object' && result.d && result.d.oddsdata) {
                    fetch('/__app_trace__/odds/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: text
                    });
                }
            } catch (e) {}
            return result;
        };
    })();"""

    POLICY_CONFIG = {
        "url_template": "https://www.oddsportal.com/football/h2h/{first_team}/{second_team}/#{match_code}:{betting_type};{scope_id}",
        "debug": False,
        "rules": [
            {
                "type": InterceptType.JS,
                "hook_script": HOOK_SCRIPT,
            }
        ]
    }

    def __init__(
        self,
        market: OddsMarkets,
        rule_extras: Optional[list] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__()
        self.market = market
        self.payload = payload or {}
        self.odds_dao = OddsDao()

        self.intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG, rule_extras=rule_extras)

        self.refetch_strategy = (
            TimelineRefetchStrategy(min_interval=timedelta(minutes=5))
            .add_segment(start_offset=timedelta(days=-7), end_offset=timedelta(days=-3), interval=timedelta(days=1))
            .add_segment(start_offset=timedelta(days=-3), end_offset=timedelta(hours=-24), interval=timedelta(hours=12))
            .add_segment(start_offset=timedelta(hours=-24), end_offset=timedelta(hours=-2), interval=timedelta(hours=1))
            .add_segment(start_offset=timedelta(hours=-2), end_offset=timedelta(hours=-1), interval=timedelta(minutes=15))
            .add_segment(start_offset=timedelta(hours=-1), end_offset=timedelta(0), interval=timedelta(minutes=5))
            .add_segment(start_offset=timedelta(minutes=0), end_offset=timedelta(minutes=30), interval=timedelta(minutes=10))
        )

        self.retry_strategy = (
            AttemptRefetchStrategy()
            .add_segment(min_attempts=1, max_attempts=4, interval=timedelta(minutes=1))
            .add_segment(min_attempts=4, max_attempts=7, interval=timedelta(minutes=2))
            .add_segment(min_attempts=7, max_attempts=None, interval=timedelta(minutes=15))
        )

    def _build_page_url(
        self, match_code: str, home_name: str, home_code: str, away_name: str, away_code: str, match_url: str
    ) -> str:
        if not home_code or not away_code:
            return match_url

        home_name, away_name = home_name.lower(), away_name.lower()
        slug = lambda name, code: f"{name.replace(' ', '-')}-{code}"
        home_team = slug(home_name, home_code)
        away_team = slug(away_name, away_code)

        if home_name <= away_name:
            first_team, second_team = home_team, away_team
        else:
            first_team, second_team = away_team, home_team

        return self.intercept_policy.url.format(
            first_team=first_team,
            second_team=second_team,
            match_code=match_code,
            betting_type=self.market.betting_type_slug,
            scope_id=self.market.scope_id,
        )

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.odds_dao.get_pending_fetch_items(
                    self.market.betting_type_id,
                    self.market.scope_id,
                    CrawlParams.META_DATA_QUERY_LIMIT
                )
                if not items:
                    self.idle_sleep()
                    continue

                for match_code, home_name, home_code, away_name, away_code, kickoff_time, match_url, fetch_attempts in items:
                    if self.should_stop():
                        return

                    try:
                        page_url = self._build_page_url(
                            match_code, home_name, home_code, away_name, away_code, match_url
                        )

                        future = self.interceptor.submit_task(
                            TaskType.OPEN_PAGE,
                            url=page_url,
                            intercept_policy=self.intercept_policy
                        )

                        result_set = future.result()
                        if result_set is None or result_set.is_empty():
                            self.logger.error(f"No response for {page_url}")
                            self.odds_dao.mark_fetch_failed(
                                match_code,
                                self.market.betting_type_id,
                                self.market.scope_id,
                                self.retry_strategy.suggest_interval(fetch_attempts+1),
                                "No response",
                            )
                            continue

                        json_body = result_set.first()

                        self.odds_dao.sync_raw_data({
                            "match_code": match_code,
                            "betting_type_id": self.market.betting_type_id,
                            "scope_id": self.market.scope_id,
                            "source_url": page_url,
                            "json_body": json_body,
                        })

                        fetch_interval = self.refetch_strategy.suggest_interval(kickoff_time, datetime.now(timezone.utc))
                        self.odds_dao.mark_as_fetched(match_code, self.market.betting_type_id, self.market.scope_id, fetch_interval)
                        self.logger.info(f"Synced oddsportal odds match_code={match_code}")

                    except Exception as e:
                        self.odds_dao.mark_fetch_failed(
                            match_code,
                            self.market.betting_type_id,
                            self.market.scope_id,
                            self.retry_strategy.suggest_interval(fetch_attempts+1),
                        )
                        self.logger.error(f"Failed to sync odds for match_code={match_code}: {e}")

            except Exception as e:
                self.logger.error(f"Sync odds loop error: {e}", exc_info=True)
                self.idle_sleep()

@Registry.poll('sync.oddsportal.ft_1x2_odds')
class SyncFT1x2Odds(BaseSyncOdds):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(OddsMarkets.FT_1X2, payload=payload)

@Registry.poll('sync.oddsportal.ft_ah_odds')
class SyncFTAhOdds(BaseSyncOdds):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(OddsMarkets.FT_AH, rule_extras=[{"on_trace": self._on_trace}], payload=payload)

    async def _on_trace(self, hook_context, json_data) -> Optional[Dict[str, Any]]:
        d = json_data.get("d", {})
        is_target = d.get("bt") == self.market.betting_type_id and d.get("sc") == self.market.scope_id
        if is_target:
            return json_data

        await hook_context.page_context.evaluate("""() => {
            const target = Array.from(document.querySelectorAll('*')).find(el => el.textContent.trim() === 'Asian Handicap');
            if (target) target.click();
        }""")
        return None
