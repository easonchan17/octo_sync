import traceback
from decimal import Decimal
from core.registry import Registry
from core.store.postgres.models import Site
from typing import Any, Dict, Optional, List, Tuple
from core.scheduler.tasks.poll_task import PollTask
from core.logger.logger_manager import LoggerManager
from core.scheduler.synchronizers.pinnacle2.match_odds_synchronizer import MatchOddsSynchronizer
from core.store.postgres.models.pinnacle import Fixture, Moneyline, Spread
from core.types.params import MatchCrawlParams

ALLOWED_ODDS_TYPES = {"moneyline", "spread"}


class MatchOddsParser:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def parse(self, json_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not json_body:
            self.logger.error("json_body is empty")
            return None

        match_records = self._parse_matches(json_body.get("matchups"))
        moneyline_records, spread_records = self._parse_odds(json_body.get("odds"))

        return {
            "matchups": match_records,
            "moneylines": moneyline_records,
            "spreads": spread_records,
        }

    def _parse_matches(self, raw_data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if raw_data is None:
            return []

        matches: Dict[str, Any] = {}
        for item in raw_data:
            if item.get('type') != 'matchup': continue
            if item.get('units') != 'Regular': continue
            if item.get('status') != 'pending': continue

            match_id = item.get('id')
            if not match_id: continue

            kickoff_time = item.get('startTime')
            if not kickoff_time: continue

            home_team = None
            away_team = None
            participants = item.get('participants', [])
            for team in participants:
                alignment = team.get('alignment')
                if alignment == 'home':
                    home_team = team.get('name')
                elif alignment == 'away':
                    away_team = team.get('name')

            league = item.get('league', {})
            matches[match_id] = {
                Fixture.match_id.key: match_id,
                Fixture.kickoff_time.key: kickoff_time,
                Fixture.league_id.key: league.get('id'),
                Fixture.league_name.key: league.get('name'),
                Fixture.home_team.key: home_team,
                Fixture.away_team.key: away_team
            }

        return list(matches.values())


    def _parse_odds(self, raw_data: Optional[Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if raw_data is None:
            return [], []

        match_odds: Dict[str, Any] = {}

        for item in raw_data:
            if item.get('period') != 0: continue
            if item.get('status') != 'open': continue
            if item.get('isAlternate', False): continue

            odds_type = item.get('type')
            if odds_type not in ALLOWED_ODDS_TYPES: continue

            match_id = item.get('matchupId')
            if not match_id: continue

            if odds_type not in match_odds:
                match_odds[odds_type] = {}

            prices = item.get('prices', [])
            match_odds[odds_type][match_id] = {
                'period': 0,
                'is_alternate': False,
                'prices': prices
            }

        moneyline_records = []
        spread_records = []

        for odds_type, odds_data in match_odds.items():
            for match_id, match_odds in odds_data.items():
                match_id = int(match_id)
                if odds_type == "moneyline":
                    moneyline_records.append(self._build_moneyline_record(match_id, match_odds))
                elif odds_type == "spread":
                    spread_records.append(self._build_spread_record(match_id, match_odds))

        return moneyline_records, spread_records

    def _build_moneyline_record(self, match_id: int, odds_data: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            Moneyline.match_id.key: match_id,
            Moneyline.period.key: odds_data.get("period", 0),
        }
        for price in odds_data.get("prices", []):
            designation = price.get("designation")
            price_value = price.get("price")
            if designation == "home":
                record[Moneyline.home_price.key] = price_value
                record[Moneyline.home_odds.key] = self._american_to_decimal(price_value)
            elif designation == "away":
                record[Moneyline.away_price.key] = price_value
                record[Moneyline.away_odds.key] = self._american_to_decimal(price_value)
            elif designation == "draw":
                record[Moneyline.draw_price.key] = price_value
                record[Moneyline.draw_odds.key] = self._american_to_decimal(price_value)
        return record

    def _build_spread_record(self, match_id: int, odds_data: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            Spread.match_id.key: match_id,
            Spread.period.key: odds_data.get("period", 0),
            Spread.is_alternate.key: odds_data.get("is_alternate", False),
        }
        for price in odds_data.get("prices", []):
            designation = price.get("designation")
            price_value = price.get("price")
            points = price.get("points") or 0
            if designation == "home":
                record[Spread.handicap.key] = Decimal(str(points))
                record[Spread.home_price.key] = price_value
                record[Spread.home_odds.key] = self._american_to_decimal(price_value)
            elif designation == "away":
                record[Spread.away_price.key] = price_value
                record[Spread.away_odds.key] = self._american_to_decimal(price_value)
        return record

    def _american_to_decimal(self, price: int) -> Decimal:
        if not price:
            return Decimal(0)
        if price > 0:
            return Decimal(str(round(1 + price / 100, 3)))
        return Decimal(str(round(1 + 100 / abs(price), 3)))


@Registry.poll("parse.pinnacle.odds")
class ParseMatchOdds(PollTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = MatchOddsSynchronizer()
        self.parser = MatchOddsParser()

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.synchronizer.get_pending_parse_items(
                    self.site,
                    MatchCrawlParams.PARSE_MAX_RETRIES,
                    MatchCrawlParams.RAW_DATA_QUERY_LIMIT,
                )

                if not items:
                    self.idle_sleep()
                    continue

                for league_id, json_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_data = self.parser.parse(json_body)
                        if parsed_data is None:
                            self.synchronizer.mark_parse_failed(self.site, league_id, "parsed data is None")
                            continue

                        self.synchronizer.sync_parsed_data(self.site, parsed_data)
                        self.synchronizer.mark_as_parsed(self.site, league_id)
                        self.logger.info(f"Parsed raw odds league_id={league_id}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.synchronizer.mark_parse_failed(self.site, league_id, full_stack_trace)
                        self.logger.error(f"Failed to parse raw odds league_id={league_id}: {e}", exc_info=True)

            except Exception as e:
                self.logger.error(f"Parse loop error: {e}", exc_info=True)
                self.idle_sleep()
