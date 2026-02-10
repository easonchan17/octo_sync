import traceback
from core.registry import Registry
from core.types.enums import MatchStatus
from core.store.postgres.models import Site
from core.utils.fotmob_utils import parse_pair
from datetime import datetime, timedelta, timezone
from core.scheduler.tasks.poll_task import PollTask
from core.logger.logger_manager import LoggerManager
from typing import Dict, Any, Optional, List, Callable, Tuple
from core.store.postgres.models.fotmob.match_data import MatchLineup, MatchStat, MatchPlayerStat
from core.scheduler.synchronizers.fotmob.match_data_synchronizer import MatchDataSynchronizer
from core.types.params import MatchCrawlParams
from core.utils.fotmob_utils import extract_status

def make_actual_extractor(val_type: type, rate_type: type) -> Callable[[List[Optional[str]]], List[Optional[Any]]]:
    def extractor(stats: List[Optional[str]]) -> List[Optional[Any]]:
        results = []
        for stat in stats:
            if stat is None:
                results.append(None)
                continue
            val, _ = parse_pair(stat, val_type, rate_type)
            results.append(val)
        return results
    return extractor

def make_total_extractor(val_type: type, rate_type: type) -> Callable[[List[Optional[str]]], List[Optional[Any]]]:
    def extractor(stats: List[Optional[str]]) -> List[Optional[Any]]:
        results = []
        for stat in stats:
            if stat is None:
                results.append(None)
                continue
            val, rate = parse_pair(stat, val_type, rate_type)
            if val is None or rate is None or rate == 0:
                results.append(None)
                continue
            total = val_type(val * 100 / rate)
            results.append(total)
        return results
    return extractor

def extract_values(stats: List[Optional[str]]) -> List[Optional[Any]]:
    return stats

def extract_value(stat: Dict[str, Any]) -> Optional[Any]:
    return stat.get("value")

def extract_total(stat: Dict[str, Any]) -> Optional[Any]:
    return stat.get("total")

class MatchDataParser:
    MATCH_STATS_MAPPING = {
        "BallPossesion": [(("home_possession", "away_possession"), extract_values)],
        "expected_goals": [(("home_xg", "away_xg"), extract_values)],
        "total_shots": [(("home_shots", "away_shots"), extract_values)],
        "ShotsOnTarget": [(("home_shots_on_target", "away_shots_on_target"), extract_values)],
        "big_chance": [(("home_big_chances", "away_big_chances"), extract_values)],
        "big_chance_missed_title": [(("home_big_chances_missed", "away_big_chances_missed"), extract_values)],
        "accurate_passes": [
            (("home_passes_completed", "away_passes_completed"), make_actual_extractor(int, int)),
            (("home_passes", "away_passes"), make_total_extractor(int, int))
        ],
        "fouls": [(("home_fouls_committed", "away_fouls_committed"), extract_values)],
        "corners": [(("home_corners", "away_corners"), extract_values)],
        "ShotsOffTarget": [(("home_shots_off_target", "away_shots_off_target"), extract_values)],
        "shots_inside_box": [(("home_shots_inside_box", "away_shots_inside_box"), extract_values)],
        "shots_outside_box": [(("home_shots_outside_box", "away_shots_outside_box"), extract_values)],
        "shots_woodwork": [(("home_hit_woodwork", "away_hit_woodwork"), extract_values)],
        "passes": [(("home_passes", "away_passes"), extract_values)],
        "own_half_passes": [(("home_own_half_passes", "away_own_half_passes"), extract_values)],
        "opposition_half_passes": [(("home_opp_half_passes", "away_opp_half_passes"), extract_values)],
        "long_balls_accurate": [
            (("home_long_passes_completed", "away_long_passes_completed"), make_actual_extractor(int, int)),
            (("home_long_passes", "away_long_passes"), make_total_extractor(int, int))
        ],
        "accurate_crosses": [
            (("home_crosses_completed", "away_crosses_completed"), make_actual_extractor(int, int)),
            (("home_crosses", "away_crosses"), make_total_extractor(int, int))
        ],
        "yellow_cards": [(("home_yellow_cards", "away_yellow_cards"), extract_values)],
        "red_cards": [(("home_red_cards", "away_red_cards"), extract_values)],
        "matchstats.headers.tackles": [(("home_tackles", "away_tackles"), extract_values)],
        "interceptions": [(("home_interceptions", "away_interceptions"), extract_values)],
        "clearances": [(("home_clearances", "away_clearances"), extract_values)],
        "shot_blocks": [(("home_shot_blocks", "away_shot_blocks"), extract_values)],
        "keeper_saves": [(("home_keeper_saves", "away_keeper_saves"), extract_values)],
        "duel_won": [(("home_duels_won", "away_duels_won"), extract_values)],
        "ground_duels_won": [
            (("home_ground_duels_won", "away_ground_duels_won"), make_actual_extractor(int, int)),
            (("home_ground_duels", "away_ground_duels"), make_total_extractor(int, int))
        ],
        "aerials_won": [
            (("home_aerials_won", "away_aerials_won"), make_actual_extractor(int, int)),
            (("home_aerials", "away_aerials"), make_total_extractor(int, int))
        ],
        "dribbles_succeeded": [
            (("home_dribbles_completed", "away_dribbles_completed"), make_actual_extractor(int, int)),
            (("home_dribbles", "away_dribbles"), make_total_extractor(int, int))
        ],
        "Offsides": [(("home_offsides", "away_offsides"), extract_values)],
        "player_throws": [(("home_throws", "away_throws"), extract_values)],
        "expected_goals_on_target": [(("home_xg_on_target", "away_xg_on_target"), extract_values)],
        "expected_goals_open_play": [(("home_xg_open_play", "away_xg_open_play"), extract_values)],
        "expected_goals_set_play": [(("home_xg_set_play", "away_xg_set_play"), extract_values)],
        "expected_goals_non_penalty": [(("home_npxg", "away_npxg"), extract_values)],
    }

    PLAYER_STATS_MAPPING = {
        "rating_title": [("rating", extract_value)],
        "minutes_played": [("minutes_played", extract_value)],
        "goals": [("goals", extract_value)],
        "assists": [("assists", extract_value)],
        "expected_goals": [("xg", extract_value)],
        "expected_assists": [("xa", extract_value)],
        "expected_goals_on_target_variant": [("xgot", extract_value)],
        "chances_created": [("chances_created", extract_value)],
        "fantasy_points": [("fantasy_points", extract_value)],
        "total_shots": [("shots", extract_value)],
        "ShotsOnTarget": [("shots_on_target", extract_value)],
        "blocked_shots": [("blocked_shots", extract_value)],
        "touches": [("touches", extract_value)],
        "touches_opp_box": [("touches_opp_box", extract_value)],
        "passes_into_final_third": [("passes_into_final_third", extract_value)],
        "accurate_passes": [
            ("passes_completed", extract_value),
            ("passes", extract_total)
        ],
        "long_balls_accurate": [
            ("long_passes_completed", extract_value),
            ("long_passes", extract_total)
        ],
        "dispossessed": [("dispossessed", extract_value)],
        "expected_goals_non_penalty": [("npxg", extract_value)],
        "matchstats.headers.tackles": [("tackles", extract_value)],
        "shot_blocks": [("blocks", extract_value)],
        "clearances": [("clearances", extract_value)],
        "headed_clearance": [("headed_clearance", extract_value)],
        "interceptions": [("interceptions", extract_value)],
        "recoveries": [("recoveries", extract_value)],
        "dribbled_past": [("dribbled_past", extract_value)],
        "duel_won": [("duels_won", extract_value)],
        "duel_lost": [("duels_lost", extract_value)],
        "ground_duels_won": [
            ("ground_duels_won", extract_value),
            ("ground_duels", extract_total)
        ],
        "aerials_won": [
            ("aerials_won", extract_value),
            ("aerials", extract_total)
        ],
        "was_fouled": [("fouls_suffered", extract_value)],
        "fouls": [("fouls_committed", extract_value)],
        "saves": [("saves", extract_value)],
        "goals_conceded": [("goals_conceded", extract_value)],
        "expected_goals_on_target_faced": [("xgot_faced", extract_value)],
        "goals_prevented": [("goals_prevented", extract_value)],
        "keeper_sweeper": [("keeper_sweeper", extract_value)],
        "keeper_high_claim": [("keeper_high_claim", extract_value)],
        "keeper_diving_save": [("keeper_diving_save", extract_value)],
        "saves_inside_box": [("saves_inside_box", extract_value)],
        "punches": [("punches", extract_value)],
        "player_throws": [("throws", extract_value)],
    }

    LINEUP_MAPPING = {
        "starter": {
            "id": [("member_id", lambda x: x)],
            "age": [("age", lambda x: x)],
            "optaId": [("opta_id", lambda x: x)],
            "name": [("member_name", lambda x: x)],
            "shirtNumber": [("shirt_number", lambda x: int(x) if x and x.isdigit() else None)],
            "countryName": [("country_name", lambda x: x)],
            "countryCode": [("country_code", lambda x: x)],
            "performance": [("rating", lambda x: x.get("rating"))],
            "horizontalLayout": [("horizontal_layout", lambda x: x)],
            "verticalLayout": [("vertical_layout", lambda x: x)],
            "positionId": [("position_id", lambda x: x)],
            "usualPlayingPositionId": [("usual_playing_position_id", lambda x: x)],
            "isCaptain": [("is_captain", lambda x: bool(x))]
        },
        "sub": {
            "id": [("member_id", lambda x: x)],
            "age": [("age", lambda x: x)],
            "optaId": [("opta_id", lambda x: x)],
            "name": [("member_name", lambda x: x)],
            "shirtNumber": [("shirt_number", lambda x: int(x) if x and x.isdigit() else None)],
            "countryName": [("country_name", lambda x: x)],
            "countryCode": [("country_code", lambda x: x)],
            "performance": [("rating", lambda x: x.get("rating"))],
            "positionId": [("position_id", lambda x: x)],
            "usualPlayingPositionId": [("usual_playing_position_id", lambda x: x)]
        },
        "coach": {
            "id": [("member_id", lambda x: x)],
            "age": [("age", lambda x: x)],
            "optaId": [("opta_id", lambda x: x)],
            "name": [("member_name", lambda x: x)],
            "countryName": [("country_name", lambda x: x)],
            "countryCode": [("country_code", lambda x: x)]
        }
    }

    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def parse(self, json_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not json_body:
            self.logger.error(f"Failed to decode json body: {json_body}")
            return None

        match_id = json_body.get('general', {}).get('matchId')
        if not match_id:
            self.logger.error(f"No match id found in response")
            return None

        content = json_body.get('content', {})
        if not content:
            self.logger.error(f"No content found in response")
            return None

        result = {"match_id": match_id}

        raw_lineup = content.get('lineup')
        if raw_lineup is not None:
            result["lineup"] = self._parse_lineup(match_id, raw_lineup)

        stats_root = content.get('stats')
        periods = stats_root.get('Periods') if stats_root else None
        all_periods = periods.get('All') if periods else None
        stat_groups = all_periods.get('stats') if all_periods else None
        if stat_groups is not None:
            result["match_stats"] = self._parse_match_stats(match_id, stat_groups)

        raw_player_stats = content.get('playerStats')
        if raw_player_stats is not None:
            result["player_stats"] = self._parse_player_stats(match_id, raw_player_stats)

        status = json_body.get('header', {}).get('status')
        match_status, kickoff_time, _, _ = extract_status(status, MatchCrawlParams.MATCH_SAFE_DURATION_HOURS)
        result["match_status"] = match_status
        result["kickoff_time"] = kickoff_time
        return result

    def _create_lineup_record(
        self,
        match_id: int,
        team_id: int,
        team_name: str
    ) -> Dict[str, Any]:
        keys = MatchLineup.get_column_keys(exclude=('created_at', 'updated_at', 'status'))
        record = {key: None for key in keys}
        record["match_id"] = match_id
        record["team_id"] = team_id
        record["team_name"] = team_name
        return record

    def _parse_lineup(self, match_id: int, raw_lineup: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        def parse_team_lineup(team_data: Optional[Dict[str, Any]]) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]]]:
            if not team_data:
                return None, None

            team_id = team_data.get("id")
            team_name = team_data.get("name")
            formation = team_data.get("formation")
            starters = team_data.get("starters", [])
            subs = team_data.get("subs", [])
            coach = team_data.get("coach")
            groups = [
                (starters, "starter", "is_starter"),
                (subs, "sub", "is_sub"),
                ([coach] if coach else [], "coach", "is_coach")
            ]
            records = []
            for members, role, flag in groups:
                field_mapping = self.LINEUP_MAPPING.get(role, {})
                for member in members:
                    record = self._create_lineup_record(match_id, team_id, team_name)
                    for key, val in member.items():
                        targets = field_mapping.get(key)
                        if not targets:
                            continue
                        for target_key, extractor in targets:
                            record[target_key] = extractor(val)
                    record[flag] = True
                    records.append(record)
            return formation, records

        lineup_type = raw_lineup.get("lineupType")
        home_formation, home_lineup = parse_team_lineup(raw_lineup.get("homeTeam"))
        away_formation, away_lineup = parse_team_lineup(raw_lineup.get("awayTeam"))
        return {
            "lineup_type": lineup_type,
            "home_formation": home_formation,
            "home_lineup": home_lineup,
            "away_formation": away_formation,
            "away_lineup": away_lineup
        }

    def _create_match_stats_record(self, match_id: int) -> Dict[str, Any]:
        keys = MatchStat.get_column_keys(exclude=('created_at', 'updated_at', 'status'))
        record = {key: None for key in keys}
        record["match_id"] = match_id
        return record

    def _parse_match_stats(self, match_id: int, stat_groups: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        record = self._create_match_stats_record(match_id)
        for stat_group in stat_groups:
            stats = stat_group.get("stats", [])
            for stat in stats:
                targets = self.MATCH_STATS_MAPPING.get(stat.get("key"))
                if not targets:
                    continue
                raw_vals = stat.get("stats", [None, None])
                for target_keys, extractor in targets:
                    target_vals = extractor(raw_vals)
                    record.update(zip(target_keys, target_vals))
        return record

    def _create_player_stats_record(
        self,
        match_id: int,
        player_id: int,
        player_name: str,
        opta_id: str
    ) -> Dict[str, Any]:
        keys = MatchPlayerStat.get_column_keys(exclude=('created_at', 'updated_at', 'status'))
        record = {key: None for key in keys}
        record["match_id"] = match_id
        record["player_id"] = player_id
        record["player_name"] = player_name
        record["opta_id"] = opta_id
        return record

    def _parse_player_stats(self, match_id: int, player_datas: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        records = []
        for _, player_data in player_datas.items():
            player_id = player_data.get("id")
            player_name = player_data.get("name")
            opta_id = player_data.get("optaId")
            record = self._create_player_stats_record(match_id, player_id, player_name, opta_id)
            stat_groups = player_data.get("stats", [])
            for stat_group in stat_groups:
                stats = stat_group.get("stats", {})
                for _, stat in stats.items():
                    targets = self.PLAYER_STATS_MAPPING.get(stat.get("key"))
                    if not targets:
                        continue
                    raw_val = stat.get("stat", {})
                    for target_key, extractor in targets:
                        record[target_key] = extractor(raw_val)
            records.append(record)
        self.logger.info(f"Parsed {len(records)} player stats for match {match_id}")
        return records

@Registry.poll('parse.fotmob.match_data')
class ParseMatchData(PollTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = MatchDataSynchronizer()
        self.parser = MatchDataParser()

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                start_time, end_time = self.get_fetch_time_range(MatchCrawlParams.LOOKAHEAD_HOURS)
                items = self.synchronizer.get_pending_parse_items(
                    self.site,
                    start_time,
                    end_time,
                    MatchCrawlParams.PARSE_MAX_RETRIES,
                    MatchCrawlParams.RAW_DATA_QUERY_LIMIT
                )

                if not items:
                    self.idle_sleep()
                    continue

                for match_id, kickoff_time, last_fetched_at, json_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_data = self.parser.parse(json_body)
                        if parsed_data is None:
                            self.synchronizer.mark_parse_failed(self.site, match_id, "match data is None")
                            continue


                        new_kickoff_time = datetime.fromisoformat(parsed_data["kickoff_time"])
                        match_status = parsed_data["match_status"]

                        if new_kickoff_time != kickoff_time:
                            self.logger.warning(
                                f"match {match_id} kickoff time changed: {kickoff_time.astimezone(timezone.utc)} -> {new_kickoff_time}"
                            )

                        self.synchronizer.sync_parsed_data(self.site, parsed_data)
                        self.synchronizer.mark_as_parsed(self.site, match_id, new_kickoff_time, match_status)

                        if MatchStatus(match_status).is_finalized:
                            count = self.calculate_confirm_count(kickoff_time, last_fetched_at, MatchCrawlParams.CONFIRM_INTERVAL_HOURS)
                            self.synchronizer.set_confirm_count(self.site, match_id, count)

                        self.logger.info(f"Parsed match: kickoff_time={kickoff_time} match_id={match_id}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.synchronizer.mark_parse_failed(self.site, match_id, full_stack_trace)
                        self.logger.error(f"Failed to parse match data for match {match_id}: {e}", exc_info=True)
            except Exception as e:
                self.logger.error(f"Failed to parse match data: {e}", exc_info=True)
                self.idle_sleep()
