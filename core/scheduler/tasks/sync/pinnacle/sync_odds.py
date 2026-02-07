from decimal import Decimal
from core.registry import Registry
from core.store.postgres.models import Site
from core.browser.interceptor import TaskType
from typing import Any, Dict, Optional, List, Tuple
from core.scheduler.tasks.base_task import BaseTask
from core.browser.intercept_policy import InterceptPolicy
from core.browser.components.receivers.pinnacle.odds_receiver import OddsReceiver
from core.browser.components.receivers.pinnacle.fixture_receiver import FixtureReceiver
from core.scheduler.synchronizers.pinnacle.fixture_synchronizer import FixtureSynchronizer
from core.scheduler.synchronizers.pinnacle.moneyline_synchronizer import MoneylineSynchronizer
from core.scheduler.synchronizers.pinnacle.spread_synchronizer import SpreadSynchronizer
from core.store.postgres.models.pinnacle.moneyline import Moneyline
from core.store.postgres.models.pinnacle.fixture import Fixture
from core.store.postgres.models.pinnacle.spread import Spread

@Registry.task('sync.pinnacle.odds')
class SyncOdds(BaseTask):
    POLICY_CONFIG = {
        "url_template": "https://www.pinnacle.com/en/soccer/{country_name}-{league_name}/matchups/#all",
        "debug": False,
        "rules": [
            {
                "type": "http",
                "pattern": "https://guest.api.arcadia.pinnacle.com/.*/leagues/.*/matchups",
                "receiver": FixtureReceiver
            },
            {
                "type": "http",
                "pattern": "https://guest.api.arcadia.pinnacle.com/.*/leagues/.*/markets/straight",
                "receiver": OddsReceiver
            }
        ]
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.fixture_synchronizer = FixtureSynchronizer()
        self.moneyline_synchronizer = MoneylineSynchronizer()
        self.spread_synchronizer = SpreadSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        country_name = self.payload.get("country_name") or ""
        league_name = self.payload.get("league_name") or ""

        country_name = country_name.strip().lower()
        league_name = league_name.strip().lower()

        if not country_name or not league_name:
            self.logger.error("Country name and league name are required")
            return

        intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

        page_url = intercept_policy.url.format(
            country_name=country_name,
            league_name=league_name
        )

        try:
            future = self.interceptor.submit_task(
                TaskType.OPEN_PAGE,
                url=page_url,
                intercept_policy=intercept_policy
            )

            responses, _ = future.result()
            if not responses:
                self.logger.error(f"No response for {page_url}")
                return

            match_records, moneyline_records, spread_records = self._clean_and_build(responses)

            self.fixture_synchronizer.sync(self.site, match_records)
            self.moneyline_synchronizer.sync(self.site, moneyline_records)
            self.spread_synchronizer.sync(self.site, spread_records)
        except Exception as e:
            self.logger.error(f"Failed to sync odds from {self.site.name}: {e}", exc_info=True)

    def _clean_and_build(self, responses: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        matches: Dict[str, Any] = {}
        odds: Dict[str, Any] = {}

        for response in responses:
            response_type = response.get('type')
            if response_type == 'matches':
                matches = response.get('data', {})
            elif response_type == 'odds':
                odds = response.get('data', {})

        if not matches:
            self.logger.warning("No matches or odds found")
            return [], [], []

        match_records = []
        moneyline_records = []
        spread_records = []

        for match_id, match_data in matches.items():
            match_id = int(match_id)
            match_records.append(self._build_match_record(match_id, match_data))

        for odds_type, match_odds in odds.items():
            for match_id, odds_data in match_odds.items():
                if match_id not in matches:
                    continue

                match_id = int(match_id)
                if odds_type == 'moneyline':
                    moneyline_records.append(self._build_moneyline_record(match_id, odds_data))
                elif odds_type == 'spread':
                    spread_records.append(self._build_spread_record(match_id, odds_data))

        return match_records, moneyline_records, spread_records

    def _build_match_record(self, match_id: int, match_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            Fixture.match_id.key: match_id,
            Fixture.kickoff_time.key: match_data.get(Fixture.kickoff_time.key),
            Fixture.league_id.key: match_data.get(Fixture.league_id.key),
            Fixture.league_name.key: match_data.get(Fixture.league_name.key),
            Fixture.home_team.key: match_data.get(Fixture.home_team.key),
            Fixture.away_team.key: match_data.get(Fixture.away_team.key)
        }

    def _build_moneyline_record(self, match_id: int, odds_data: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            Moneyline.match_id.key: match_id,
            Moneyline.period.key: odds_data.get('period', 0),
        }

        for price in odds_data.get('prices', []):
            designation = price.get('designation')
            price_value = price.get('price')

            if designation == 'home':
                record[Moneyline.home_price.key] = price_value
                record[Moneyline.home_odds.key] = self._american_to_decimal(price_value)
            elif designation == 'away':
                record[Moneyline.away_price.key] = price_value
                record[Moneyline.away_odds.key] = self._american_to_decimal(price_value)
            elif designation == 'draw':
                record[Moneyline.draw_price.key] = price_value
                record[Moneyline.draw_odds.key] = self._american_to_decimal(price_value)

        return record

    def _build_spread_record(self, match_id: int, odds_data: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            Spread.match_id.key: match_id,
            Spread.period.key: odds_data.get('period', 0),
            Spread.is_alternate.key: odds_data.get('is_alternate', False)
        }

        for price in odds_data.get('prices', []):
            designation = price.get('designation')
            price_value = price.get('price')
            points = price.get('points') or 0

            if designation == 'home':
                record[Spread.handicap.key] = Decimal(str(points))
                record[Spread.home_price.key] = price_value
                record[Spread.home_odds.key] = self._american_to_decimal(price_value)
            elif designation == 'away':
                record[Spread.away_price.key] = price_value
                record[Spread.away_odds.key] = self._american_to_decimal(price_value)

        return record

    def _american_to_decimal(self, price: int) -> Decimal:
        if not price:
            return Decimal(0)

        if price > 0:
            return Decimal(str(round(1 + price / 100, 3)))

        return Decimal(str(round(1 + 100 / abs(price), 3)))