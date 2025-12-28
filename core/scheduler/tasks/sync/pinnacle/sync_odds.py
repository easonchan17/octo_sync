from decimal import Decimal
from core.store.postgres.models import Site
from core.browser.interceptor import TaskType
from typing import Any, Dict, Optional, List, Tuple
from core.scheduler.tasks.base_task import BaseTask
from core.browser.intercept_policy import InterceptPolicy
from core.scheduler.tasks.sync.common.team_resolver import TeamResolver
from core.scheduler.synchronizers.pinnacle.match_synchronizer import MatchSynchronizer
from core.scheduler.synchronizers.pinnacle.moneyline_synchronizer import MoneylineSynchronizer
from core.scheduler.synchronizers.pinnacle.spread_synchronizer import SpreadSynchronizer

class SyncOdds(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.match_synchronizer = MatchSynchronizer()
        self.moneyline_synchronizer = MoneylineSynchronizer()
        self.spread_synchronizer = SpreadSynchronizer()
        self.team_resolver = TeamResolver()

    def execute(self, *args, **kwargs) -> None:
        country_name = self.payload.get("country_name") or ""
        league_name = self.payload.get("league_name") or ""

        country_name = country_name.strip().lower()
        league_name = league_name.strip().lower()

        if not country_name or not league_name:
            self.logger.error("Country name and league name are required")
            return

        policy_config = self.config_manager.get_config(f"interceptor.{self.site.name}.odds")
        intercept_policy = InterceptPolicy.from_rules(policy_config)

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

            self.match_synchronizer.sync(self.site, match_records)
            self.moneyline_synchronizer.sync(self.site, moneyline_records)
            self.spread_synchronizer.sync(self.site, spread_records)
        except Exception as e:
            self.logger.error(f"Failed to sync odds from {self.site.name}: {e}", exc_info=True)

    def _clean_and_build(self, responses: List[Any]) -> Tuple[List[Any], List[Any], List[Any]]:
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

        match_records.sort(key=lambda x: x['kickoff_time'])
        target_matches = self.match_synchronizer.get_target_matches(
            match_records[0]['league_id'],
            match_records[0]['kickoff_time']
        )
        self.team_resolver.resolve(match_records, target_matches)

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
            'match_id': match_id,
            'kickoff_time': match_data.get('kickoff_time'),
            'league_id': match_data.get('league_id'),
            'league_name': match_data.get('league_name'),
            'home_team': match_data.get('home_team'),
            'away_team': match_data.get('away_team')
        }

    def _build_moneyline_record(self, match_id: int, odds_data: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            'match_id': match_id,
            'period': odds_data.get('period', 0),
        }

        for price in odds_data.get('prices', []):
            designation = price.get('designation')
            price_value = price.get('price')

            if designation == 'home':
                record['home_price'] = price_value
                record['home_odds'] = self._american_to_decimal(price_value)
            elif designation == 'away':
                record['away_price'] = price_value
                record['away_odds'] = self._american_to_decimal(price_value)
            elif designation == 'draw':
                record['draw_price'] = price_value
                record['draw_odds'] = self._american_to_decimal(price_value)

        return record

    def _build_spread_record(self, match_id: int, odds_data: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            'match_id': match_id,
            'period': odds_data.get('period', 0),
            'is_alternate': odds_data.get('isAlternate', False)
        }

        for price in odds_data.get('prices', []):
            designation = price.get('designation')
            price_value = price.get('price')
            points = price.get('points') or 0

            if designation == 'home':
                record['handicap'] = Decimal(str(points))
                record['home_price'] = price_value
                record['home_odds'] = self._american_to_decimal(price_value)
            elif designation == 'away':
                record['away_price'] = price_value
                record['away_odds'] = self._american_to_decimal(price_value)

        return record

    def _american_to_decimal(self, price: int) -> Decimal:
        if not price:
            return Decimal(0)

        if price > 0:
            return Decimal(str(round(1 + price / 100, 3)))

        return Decimal(str(round(1 + 100 / abs(price), 3)))