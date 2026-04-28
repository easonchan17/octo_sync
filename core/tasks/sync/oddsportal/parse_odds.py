import json
from abc import abstractmethod
from typing import Any, Dict, List, Optional
from core.scheduler.task_registry import TaskRegistry
from core.types.enums import OddsMarket, OddsMarkets, SiteName
from core.tasks.poll_task import PollTask, CrawlParams
from core.store.postgres.daos.oddsportal import OddsDao
from core.logger.logger_manager import LoggerManager
from core.utils.datetime_utils import from_timestamp

class BaseOddsParser:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def _is_expected_market(self, json_body: Dict[str, Any], market: OddsMarket) -> bool:
        d = json_body.get("d", {})
        bt = d.get("bt")
        sc = d.get("sc")

        if not bt or not sc:
            self.logger.error(f"bt or sc is missing: bt={bt}, sc={sc}")
            return False

        if bt != market.betting_type_id or sc != market.scope_id:
            self.logger.error(f"bt/sc mismatch: expected {market.betting_type_id}/{market.scope_id}, got {bt}/{sc}")
            self.logger.info(f"json_body: {json.dumps(json_body, indent=2, ensure_ascii=False)}")
            return False

        return True

    def _extract_bookmaker_ids(self, json_body: Dict[str, Any], market: OddsMarket) -> List[str]:
        ids = json_body.get("d", {}).get("nav", {}).get(str(market.betting_type_id), {}).get(str(market.scope_id), [])
        if not ids:
            self.logger.error("bookmaker ids is missing")

        return ids


    def _extract_odds_data(self, json_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        odds_data = json_body.get("d", {}).get("oddsdata")
        if not odds_data:
            self.logger.error("odds data is missing")

        return odds_data

    @abstractmethod
    def parse(self, match_code: str, market: OddsMarket, json_body: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        raise NotImplementedError

class Odds1x2Parser(BaseOddsParser):
    def _extract_odds_records(self, match_code: str, market: OddsMarket, quote_type: str,  market_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        closing_odds = market_data.get("odds", {})
        if not closing_odds:
            self.logger.error("closing odds is empty")
            return None

        opening_odds = market_data.get("openingOdd", {})
        if not opening_odds:
            self.logger.error("opening odds is empty")
            return None

        movement = market_data.get("movement", {})
        closing_change_time = market_data.get("changeTime", {})
        opening_change_time = market_data.get("openingChangeTime", {})
        closing_volume = market_data.get("volume", {})
        opening_volume = market_data.get("openingVolume", {})

        if not isinstance(closing_volume, dict):
            closing_volume = {}

        home_key = market.outcomes["home"]
        draw_key = market.outcomes["draw"]
        away_key = market.outcomes["away"]
        bookmaker_ids = list(closing_odds.keys())

        records = []
        for bookmaker_id in bookmaker_ids:
            try:
                closing_bookmaker_odds = closing_odds.get(bookmaker_id, {})
                opening_bookmaker_odds = opening_odds.get(bookmaker_id, {})
                closing_bookmaker_change_time = closing_change_time.get(bookmaker_id, {})
                opening_bookmaker_change_time = opening_change_time.get(bookmaker_id, {})
                closing_bookmaker_volume = closing_volume.get(bookmaker_id, {})
                opening_bookmaker_volume = opening_volume.get(bookmaker_id, {})
                bookmaker_odds_movement = movement.get(bookmaker_id, {})

                if not closing_bookmaker_odds or not opening_bookmaker_odds:
                    self.logger.error(f"Odds data is missing for bookmaker_id={bookmaker_id}")
                    continue

                records.append({
                    "match_code": match_code,
                    "quote_type": quote_type,
                    "betting_type_id": market.betting_type_id,
                    "scope_id": market.scope_id,
                    "bookmaker_id": int(bookmaker_id),
                    "closing_home_odds": closing_bookmaker_odds.get(home_key),
                    "closing_draw_odds": closing_bookmaker_odds.get(draw_key),
                    "closing_away_odds": closing_bookmaker_odds.get(away_key),
                    "opening_home_odds": opening_bookmaker_odds.get(home_key),
                    "opening_draw_odds": opening_bookmaker_odds.get(draw_key),
                    "opening_away_odds": opening_bookmaker_odds.get(away_key),
                    "closing_home_volume": closing_bookmaker_volume.get(home_key),
                    "closing_draw_volume": closing_bookmaker_volume.get(draw_key),
                    "closing_away_volume": closing_bookmaker_volume.get(away_key),
                    "opening_home_volume": opening_bookmaker_volume.get(home_key),
                    "opening_draw_volume": opening_bookmaker_volume.get(draw_key),
                    "opening_away_volume": opening_bookmaker_volume.get(away_key),
                    "home_movement": bookmaker_odds_movement.get(home_key),
                    "draw_movement": bookmaker_odds_movement.get(draw_key),
                    "away_movement": bookmaker_odds_movement.get(away_key),
                    "closing_home_change_time": from_timestamp(closing_bookmaker_change_time.get(home_key)),
                    "closing_draw_change_time": from_timestamp(closing_bookmaker_change_time.get(draw_key)),
                    "closing_away_change_time": from_timestamp(closing_bookmaker_change_time.get(away_key)),
                    "opening_home_change_time": from_timestamp(opening_bookmaker_change_time.get(home_key)),
                    "opening_draw_change_time": from_timestamp(opening_bookmaker_change_time.get(draw_key)),
                    "opening_away_change_time": from_timestamp(opening_bookmaker_change_time.get(away_key)),
                })
            except Exception as e:
                self.logger.error(f"Error extracting odds record for bookmaker_id={bookmaker_id}: {e}", exc_info=True)
                self.logger.error(json.dumps({
                    "closing_bookmaker_odds": closing_bookmaker_odds,
                    "opening_bookmaker_odds": opening_bookmaker_odds,
                    "closing_bookmaker_change_time": closing_bookmaker_change_time,
                    "opening_bookmaker_change_time": opening_bookmaker_change_time,
                    "closing_bookmaker_volume": closing_bookmaker_volume,
                    "opening_bookmaker_volume": opening_bookmaker_volume,
                    "bookmaker_odds_movement": bookmaker_odds_movement,
                }, indent=2, ensure_ascii=False))
                return None

        return records

    def parse(self, match_code: str, market: OddsMarket, json_body: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        if not self._is_expected_market(json_body, market):
            return None

        odds_data = self._extract_odds_data(json_body)
        if not odds_data:
            return None

        records = []
        for quote_type in ["back", "lay"]:
            quote_data = odds_data.get(quote_type)
            if not quote_data:
                self.logger.warning(f"{quote_type} data is missing")
                continue

            market_data = next(iter(quote_data.values()), None)
            if not market_data:
                self.logger.warning(f"{quote_type} data is missing")
                continue

            quote_records = self._extract_odds_records(
                match_code, market, quote_type, market_data
            )
            if not quote_records:
                self.logger.error(f"Failed to extract {quote_type} odds records")
                continue

            records.extend(quote_records)

        return records


class OddsAhParser(BaseOddsParser):
    def _extract_odds_records(self, match_code: str, market: OddsMarket, quote_type: str, market_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        closing_odds = market_data.get("odds", {})
        if not closing_odds:
            return None

        opening_odds = market_data.get("openingOdd", {})
        if not opening_odds:
            return None

        movement = market_data.get("movement", {})
        closing_change_time = market_data.get("changeTime", {})
        opening_change_time = market_data.get("openingChangeTime", {})
        closing_volume = market_data.get("volume", {})
        opening_volume = market_data.get("openingVolume", {})

        if not isinstance(closing_volume, dict):
            closing_volume = {}

        handicap_value = market_data.get("handicapValue")
        if handicap_value is None:
            self.logger.error("handicap value is missing")
            return None

        bookmaker_ids = list(closing_odds.keys())

        records = []
        for bookmaker_id in bookmaker_ids:
            try:
                closing_bookmaker_odds = closing_odds.get(bookmaker_id)
                opening_bookmaker_odds = opening_odds.get(bookmaker_id)
                closing_bookmaker_change_time = closing_change_time.get(bookmaker_id)
                opening_bookmaker_change_time = opening_change_time.get(bookmaker_id)
                closing_bookmaker_volume = closing_volume.get(bookmaker_id)
                opening_bookmaker_volume = opening_volume.get(bookmaker_id)
                bookmaker_odds_movement = movement.get(bookmaker_id)

                if not closing_bookmaker_odds or not opening_bookmaker_odds:
                    self.logger.warning(f"Odds data is missing for bookmaker_id={bookmaker_id}")
                    continue

                if float(handicap_value) < 0:
                    closing_bookmaker_odds = list(closing_bookmaker_odds.values())
                    opening_bookmaker_odds = list(opening_bookmaker_odds.values())
                    closing_bookmaker_change_time = list(closing_bookmaker_change_time.values()) if closing_bookmaker_change_time else None
                    opening_bookmaker_change_time = list(opening_bookmaker_change_time.values()) if opening_bookmaker_change_time else None
                    closing_bookmaker_volume = list(closing_bookmaker_volume.values()) if closing_bookmaker_volume else None
                    opening_bookmaker_volume = list(opening_bookmaker_volume.values()) if opening_bookmaker_volume else None
                    bookmaker_odds_movement = list(bookmaker_odds_movement.values()) if bookmaker_odds_movement else None

                if len(closing_bookmaker_odds) != 2 or len(opening_bookmaker_odds) != 2:
                    self.logger.warning(f"Expected 2 odds for home and away, got {len(closing_bookmaker_odds)} closing odds and {len(opening_bookmaker_odds)} opening odds for bookmaker_id={bookmaker_id}")
                    continue

                closing_bookmaker_change_time = closing_bookmaker_change_time or [None, None]
                opening_bookmaker_change_time = opening_bookmaker_change_time or [None, None]
                closing_bookmaker_volume = closing_bookmaker_volume or [None, None]
                opening_bookmaker_volume = opening_bookmaker_volume or [None, None]
                bookmaker_odds_movement = bookmaker_odds_movement or [None, None]

                records.append({
                    "match_code": match_code,
                    "quote_type": quote_type,
                    "betting_type_id": market.betting_type_id,
                    "scope_id": market.scope_id,
                    "bookmaker_id": int(bookmaker_id),
                    "handicap": float(handicap_value),
                    "closing_home_odds": closing_bookmaker_odds[0],
                    "closing_away_odds": closing_bookmaker_odds[1],
                    "opening_home_odds": opening_bookmaker_odds[0],
                    "opening_away_odds": opening_bookmaker_odds[1],
                    "closing_home_volume": closing_bookmaker_volume[0],
                    "closing_away_volume": closing_bookmaker_volume[1],
                    "opening_home_volume": opening_bookmaker_volume[0],
                    "opening_away_volume": opening_bookmaker_volume[1],
                    "home_movement": bookmaker_odds_movement[0],
                    "away_movement": bookmaker_odds_movement[1],
                    "closing_home_change_time": from_timestamp(closing_bookmaker_change_time[0]),
                    "closing_away_change_time": from_timestamp(closing_bookmaker_change_time[1]),
                    "opening_home_change_time": from_timestamp(opening_bookmaker_change_time[0]),
                    "opening_away_change_time": from_timestamp(opening_bookmaker_change_time[1]),
                })
            except Exception as e:
                self.logger.error(f"Error extracting odds record for bookmaker_id={bookmaker_id}: {e}", exc_info=True)
                self.logger.error(json.dumps({
                    "closing_bookmaker_odds": closing_bookmaker_odds,
                    "opening_bookmaker_odds": opening_bookmaker_odds,
                    "closing_bookmaker_change_time": closing_bookmaker_change_time,
                    "opening_bookmaker_change_time": opening_bookmaker_change_time,
                    "closing_bookmaker_volume": closing_bookmaker_volume,
                    "opening_bookmaker_volume": opening_bookmaker_volume,
                    "bookmaker_odds_movement": bookmaker_odds_movement,
                }, indent=2, ensure_ascii=False))
                return None
        return records

    def parse(self, match_code: str, market: OddsMarket, json_body: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        if not self._is_expected_market(json_body, market):
            return None

        odds_data = self._extract_odds_data(json_body)
        if not odds_data:
            return None

        records = []
        for quote_type in ["back", "lay"]:
            market_data = odds_data.get(quote_type, {})
            if not market_data:
                self.logger.warning(f"{quote_type} data is missing")
                continue

            for data in market_data.values():
                quote_records = self._extract_odds_records(
                    match_code, market, quote_type, data
                )
                if not quote_records:
                    self.logger.warning(f"Failed to extract {quote_type} odds records")
                    continue

                records.extend(quote_records)

        return records


class BaseParseOdds(PollTask):
    def __init__(self, market: OddsMarkets, parser, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.ODDSPORTAL.value)
        self.market = market
        self.parser = parser
        self.payload = payload or {}
        self.odds_dao = OddsDao()

    @abstractmethod
    def _sync_parsed_data(self, records: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                betting_type_id, scope_id = self.market.betting_type_id, self.market.scope_id
                items = self.odds_dao.get_pending_parse_items(
                    betting_type_id,
                    scope_id,
                    CrawlParams.PARSE_MAX_RETRIES,
                    CrawlParams.PARSE_BATCH_SIZE
                )

                if not items:
                    self.idle_sleep()
                    continue

                for match_code, json_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_odds = self.parser.parse(match_code, self.market, json_body)
                        if parsed_odds is None:
                            self.odds_dao.mark_parse_failed(match_code, betting_type_id, scope_id, "Parsed odds is None")
                            self.logger.error(f"Failed to parse odds match_code={match_code}: odds is None")
                            continue

                        if not parsed_odds:
                            self.odds_dao.mark_parse_failed(match_code, betting_type_id, scope_id, "Parsed odds is empty")
                            self.logger.error(f"Failed to parse odds match_code={match_code}: odds is empty")
                            continue

                        self._sync_parsed_data(parsed_odds)
                        self.odds_dao.mark_as_parsed(match_code, betting_type_id, scope_id)
                        self.logger.info(f"Parsed odds match_code={match_code} betting_type_id={betting_type_id} scope_id={scope_id} count={len(parsed_odds)}")

                    except Exception as e:
                        self.odds_dao.mark_parse_failed(match_code, betting_type_id, scope_id)
                        self.logger.error(f"Failed to parse odds match_code={match_code}: {e}", exc_info=True)
                        self.logger.error(f"json_body: {json.dumps(json_body, ensure_ascii=False, indent=2)}")

            except Exception as e:
                self.logger.error(f"Parse odds loop error: {e}", exc_info=True)
                self.idle_sleep()


@TaskRegistry.poll('parse.oddsportal.ft_1x2_odds')
class ParseFT1x2Odds(BaseParseOdds):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(OddsMarkets.FT_1X2, Odds1x2Parser(), payload)

    def _sync_parsed_data(self, records: List[Dict[str, Any]]) -> None:
        self.odds_dao.sync_parsed_1x2_data(records)


@TaskRegistry.poll('parse.oddsportal.ft_ah_odds')
class ParseFTAhOdds(BaseParseOdds):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(OddsMarkets.FT_AH, OddsAhParser(), payload)

    def _sync_parsed_data(self, records: List[Dict[str, Any]]) -> None:
        self.odds_dao.sync_parsed_ah_data(records)
