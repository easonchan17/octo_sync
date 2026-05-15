import traceback, re, json
from datetime import datetime, timezone
from urllib.parse import urlparse
from pathlib import PurePosixPath
from core.types.enums import SiteName, Position, LineupRole
from core.logger.logger_manager import LoggerManager
from core.scheduler.task_registry import TaskRegistry
from typing import Dict, Any, Optional, List, Callable, Tuple
from core.tasks.poll_task import PollTask
from core.types.params import CrawlParams
from core.store.postgres.models.fotmob.match import MatchLineup, MatchStat, MatchPlayerStat, ShotStat
from core.tasks.sync.fotmob.utils import extract_status
from core.store.postgres.daos.fotmob import MatchDao
from core.store.postgres.daos.common import AssetDao

_VALUE_WITH_PERCENT_PATTERN = re.compile(r'^(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)')

def parse_pair(value: str, value_type1: type, value_type2: type) -> Tuple[Optional[Any], Optional[Any]]:
    if not isinstance(value, str):
        return None, None

    value = value.strip()
    if not value:
        return None, None

    match = _VALUE_WITH_PERCENT_PATTERN.search(value)
    if match is None:
        return None, None

    try:
        return value_type1(match.group(1)), value_type2(match.group(2))
    except (ValueError, TypeError):
        return None, None

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

class FormationResolver:
    FORMATIONS = {
        "1-4-4-2": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.RM, Position.RCM, Position.LCM, Position.LM],
            [Position.RST, Position.LST]
        ],
        "1-4-3-3": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.RCM, Position.CM, Position.LCM],
            [Position.RW, Position.ST, Position.LW]
        ],
        "1-4-2-3-1": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.RDM, Position.LDM],
            [Position.RM, Position.CAM, Position.LM],
            [Position.ST]
        ],
        "1-4-1-4-1": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.CDM],
            [Position.RM, Position.RCM, Position.LCM, Position.LM],
            [Position.ST]
        ],
        "1-4-1-2-3": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.CDM],
            [Position.RCM, Position.LCM],
            [Position.RW, Position.ST, Position.LW]
        ],
        "1-4-2-1-3": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.RDM, Position.LDM],
            [Position.CAM],
            [Position.RW, Position.ST, Position.LW]
        ],
        "1-4-4-1-1": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.RM, Position.RCM, Position.LCM, Position.LM],
            [Position.CAM],
            [Position.ST]
        ],
        "1-4-2-2-2": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.RDM, Position.LDM],
            [Position.RAM, Position.LAM],
            [Position.RST, Position.LST]
        ],
        "1-4-3-1-2": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.RCM, Position.CM, Position.LCM],
            [Position.CAM],
            [Position.RST, Position.LST]
        ],
        "1-4-1-2-1-2": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.CDM],
            [Position.RCM, Position.LCM],
            [Position.CAM],
            [Position.RST, Position.LST]
        ],
        "1-4-5-1": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.RM, Position.RCM, Position.CM, Position.LCM, Position.LM],
            [Position.ST]
        ],
        "1-4-3-2-1": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.RCM, Position.CM, Position.LCM],
            [Position.RAM, Position.LAM],
            [Position.ST]
        ],
        "1-4-2-4": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.RCM, Position.LCM],
            [Position.RW, Position.RST, Position.LST, Position.LW]
        ],
        "1-4-1-3-2": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.CDM],
            [Position.RM, Position.CAM, Position.LM],
            [Position.RST, Position.LST]
        ],
        "1-4-2-2-1-1": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.RDM, Position.LDM],
            [Position.RM, Position.LM],
            [Position.CAM],
            [Position.ST]
        ],
        "1-4-1-2-2-1": [
            [Position.GK],
            [Position.RB, Position.RCB, Position.LCB, Position.LB],
            [Position.CDM],
            [Position.RCM, Position.LCM],
            [Position.RAM, Position.LAM],
            [Position.ST]
        ],
        "1-3-4-3": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.RM, Position.RCM, Position.LCM, Position.LM],
            [Position.RW, Position.ST, Position.LW]
        ],
        "1-3-1-2-1-3": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.CDM],
            [Position.RCM, Position.LCM],
            [Position.CAM],
            [Position.RW, Position.ST, Position.LW]
        ],
        "1-3-5-2": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.RM, Position.RCM, Position.CDM, Position.LCM, Position.LM],
            [Position.RST, Position.LST]
        ],
        "1-3-4-2-1": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.RM, Position.RCM, Position.LCM, Position.LM],
            [Position.RAM, Position.LAM],
            [Position.ST]
        ],
        "1-3-4-1-2": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.RM, Position.RCM, Position.LCM, Position.LM],
            [Position.CAM],
            [Position.RST, Position.LST]
        ],
        "1-3-2-4-1": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.RDM, Position.LDM],
            [Position.RM, Position.RAM, Position.LAM, Position.LM],
            [Position.ST]
        ],
        "1-3-1-4-2": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.CDM],
            [Position.RM, Position.RCM, Position.LCM, Position.LM],
            [Position.RST, Position.LST]
        ],
        "1-3-5-1-1": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.RM, Position.RCM, Position.CDM, Position.LCM, Position.LM],
            [Position.CAM],
            [Position.ST]
        ],
        "1-3-3-3-1": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.RCM, Position.CDM, Position.LCM],
            [Position.RM, Position.CAM, Position.LM],
            [Position.ST]
        ],
        "1-3-3-2-2": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.RCM, Position.CDM, Position.LCM],
            [Position.RAM, Position.LAM],
            [Position.RST, Position.LST]
        ],
        "1-3-3-1-3": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.RCM, Position.CDM, Position.LCM],
            [Position.CAM],
            [Position.RW, Position.ST, Position.LW]
        ],
        "1-3-2-2-3": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.RDM, Position.LDM],
            [Position.RAM, Position.LAM],
            [Position.RW, Position.ST, Position.LW]
        ],
        "1-3-2-3-2": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.RDM, Position.LDM],
            [Position.RM, Position.CAM, Position.LM],
            [Position.RST, Position.LST]
        ],
        "1-3-1-3-1-2": [
            [Position.GK],
            [Position.RCB, Position.CB, Position.LCB],
            [Position.CDM],
            [Position.RM, Position.CM, Position.LM],
            [Position.CAM],
            [Position.RST, Position.LST]
        ],
        "1-5-3-2": [
            [Position.GK],
            [Position.RWB, Position.RCB, Position.CB, Position.LCB, Position.LWB],
            [Position.RCM, Position.CM, Position.LCM],
            [Position.RST, Position.LST]
        ],
        "1-5-4-1": [
            [Position.GK],
            [Position.RWB, Position.RCB, Position.CB, Position.LCB, Position.LWB],
            [Position.RM, Position.RCM, Position.LCM, Position.LM],
            [Position.ST]
        ],
        "1-5-2-3": [
            [Position.GK],
            [Position.RWB, Position.RCB, Position.CB, Position.LCB, Position.LWB],
            [Position.RCM, Position.LCM],
            [Position.RW, Position.ST, Position.LW]
        ],
        "1-5-2-1-2": [
            [Position.GK],
            [Position.RWB, Position.RCB, Position.CB, Position.LCB, Position.LWB],
            [Position.RCM, Position.LCM],
            [Position.CAM],
            [Position.RST, Position.LST]
        ],
        "1-5-3-1-1": [
            [Position.GK],
            [Position.RWB, Position.RCB, Position.CB, Position.LCB, Position.LWB],
            [Position.RCM, Position.CM, Position.LCM],
            [Position.CAM],
            [Position.ST]
        ],
        "1-5-1-3-1": [
            [Position.GK],
            [Position.RWB, Position.RCB, Position.CB, Position.LCB, Position.LWB],
            [Position.CDM],
            [Position.RM, Position.CAM, Position.LM],
            [Position.ST]
        ],
        "1-5-2-2-1": [
            [Position.GK],
            [Position.RWB, Position.RCB, Position.CB, Position.LCB, Position.LWB],
            [Position.RCM, Position.LCM],
            [Position.RAM, Position.LAM],
            [Position.ST]
        ],
        "1-5-1-2-1-1": [
            [Position.GK],
            [Position.RWB, Position.RCB, Position.CB, Position.LCB, Position.LWB],
            [Position.CDM],
            [Position.RCM, Position.LCM],
            [Position.CAM],
            [Position.ST]
        ]
    }

    # ADVANCE_POSITION = {
    #     Position.RB : Position.RWB,
    #     Position.LB : Position.LWB,

    #     Position.RWB: Position.RM,
    #     Position.LWB: Position.LM,

    #     Position.RM: Position.RW,
    #     Position.LM: Position.LW,

    #     Position.RCM: Position.RAM,
    #     Position.LCM: Position.LAM
    # }

    # DEEPER_POSITION = {
    #     Position.RW: Position.RM,
    #     Position.LW: Position.LM,

    #     Position.RAM: Position.RCM,
    #     Position.LAM: Position.LCM,

    #     Position.RM: Position.RWB,
    #     Position.LM: Position.LWB,

    #     Position.RWB: Position.RB,
    #     Position.LWB: Position.LB
    # }

    @staticmethod
    def _get_x(player: Dict[str, Any]) -> float:
        return player.get('verticalLayout', {}).get('x', 0)

    @staticmethod
    def _get_y(player: Dict[str, Any]) -> float:
        return player.get('verticalLayout', {}).get('y', 0)

    @staticmethod
    def _get_w(player: Dict[str, Any]) -> float:
        return player.get('verticalLayout', {}).get('width', 0)

    def __init__(self):
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def resolve(self, formation: str, players: List[Dict[str, Any]]) -> None:
        if not formation or not players:
            return

        formation_ex = f"1-{formation}"
        player_matrix = self._build_formation(formation_ex, players)

        position_matrix = self.FORMATIONS.get(formation_ex)
        if position_matrix is None:
            raise ValueError(f"Unsupported formation: {formation}")

        for players_in_layer, positions_in_layer in zip(player_matrix, position_matrix):
            # base_y = self._get_y(players_in_layer[len(players_in_layer)//2])
            for player, position in zip(players_in_layer, positions_in_layer):
                player['position'] = position.value
                # current_y = self._get_y(player)
                # if current_y == base_y:
                #     player['position'] = position.value
                # elif current_y > base_y:
                #     self.logger.info(f'{formation} advance {position.value}')
                #     player['position'] = self.ADVANCE_POSITION[position].value
                # else:
                #     self.logger.info(f'{formation} deeper {position.value}')
                #     player['position'] = self.DEEPER_POSITION[position].value


    def _build_formation(self, formation: str, players: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        counts = [int(count) for count in formation.split("-")]
        sorted_players = sorted(players, key=self._get_y)

        layers = []
        offset = 0
        for count in counts:
            layer_players = sorted_players[offset:offset + count]
            layers.append(sorted(layer_players, key=self._get_x))
            offset += count

        return layers

class MatchParser:
    MATCH_STATS_EXTRACTOR = {
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

    SHOT_STATS_EXTRACTOR = {
        "id": [("event_id", lambda x: x)],
        "period": [("period", lambda x: x)],
        "min": [("min", lambda x: x)],
        "minAdded": [("min_added", lambda x: x)],
        "x": [("x", lambda x: x)],
        "y": [("y", lambda x: x)],
        "teamId": [("team_id", lambda x: x)],
        "keeperId": [("keeper_id", lambda x: x)],
        "playerId": [("player_id", lambda x: x)],
        "shotType": [("shot_type", lambda x: x)],
        "eventType": [("event_type", lambda x: x)],
        "situation": [("situation", lambda x: x)],
        "isBlocked": [("is_blocked", lambda x: x)],
        "isOwnGoal": [("is_own_goal", lambda x: x)],
        "isOnTarget": [("is_on_target", lambda x: x)],
        "isSavedOffLine": [("is_saved_off_line", lambda x: x)],
        "isFromInsideBox": [("is_inside_box", lambda x: x)],
        "expectedGoals": [("xg", lambda x: x)],
        "expectedGoalsOnTarget": [("xgot", lambda x: x)],
    }

    SHOT_STATS_COUNTER = {
        "shots_inside_box":         lambda shot: 1 if shot.get("isFromInsideBox") is True else 0,
        "shots_freekick":           lambda shot: 1 if shot.get("situation") == "FreeKick" else 0,
        "shots_fastbreak":          lambda shot: 1 if shot.get("situation") == "FastBreak" else 0,
        "shots_setpiece":           lambda shot: 1 if shot.get("situation") == "SetPiece" else 0,
        "shots_corner":             lambda shot: 1 if shot.get("situation") == "FromCorner" else 0,
        "shots_header":             lambda shot: 1 if shot.get("shotType") == "Header" else 0,
        "shots_penalty":            lambda shot: 1 if shot.get("situation") == "Penalty" else 0,
        "shots_individual_play":    lambda shot: 1 if shot.get("situation") == "IndividualPlay" else 0,
        "shots_throw_in_set_piece": lambda shot: 1 if shot.get("situation") == "ThrowInSetPiece" else 0,
        "goals_inside_box":         lambda shot: 1 if shot.get("eventType") == "Goal" and shot.get("isFromInsideBox") is True else 0,
        "goals_freekick":           lambda shot: 1 if shot.get("eventType") == "Goal" and shot.get("situation") == "FreeKick" else 0,
        "goals_fastbreak":          lambda shot: 1 if shot.get("eventType") == "Goal" and shot.get("situation") == "FastBreak" else 0,
        "goals_setpiece":           lambda shot: 1 if shot.get("eventType") == "Goal" and shot.get("situation") == "SetPiece" else 0,
        "goals_corner":             lambda shot: 1 if shot.get("eventType") == "Goal" and shot.get("situation") == "FromCorner" else 0,
        "goals_header":             lambda shot: 1 if shot.get("eventType") == "Goal" and shot.get("shotType") == "Header" else 0,
        "goals_penalty":            lambda shot: 1 if shot.get("eventType") == "Goal" and shot.get("situation") == "Penalty" else 0,
        "goals_individual_play":    lambda shot: 1 if shot.get("eventType") == "Goal" and shot.get("situation") == "IndividualPlay" else 0,
        "goals_throw_in_set_piece": lambda shot: 1 if shot.get("eventType") == "Goal" and shot.get("situation") == "ThrowInSetPiece" else 0,
        "xg_inside_box":            lambda shot: (shot.get("expectedGoals") or 0) if shot.get("isFromInsideBox") is True else 0,
        "xg_freekick":              lambda shot: (shot.get("expectedGoals") or 0) if shot.get("situation") == "FreeKick" else 0,
        "xg_fastbreak":             lambda shot: (shot.get("expectedGoals") or 0) if shot.get("situation") == "FastBreak" else 0,
        "xg_setpiece":              lambda shot: (shot.get("expectedGoals") or 0) if shot.get("situation") == "SetPiece" else 0,
        "xg_corner":                lambda shot: (shot.get("expectedGoals") or 0) if shot.get("situation") == "FromCorner" else 0,
        "xg_header":                lambda shot: (shot.get("expectedGoals") or 0) if shot.get("shotType") == "Header" else 0,
        "xg_individual_play":       lambda shot: (shot.get("expectedGoals") or 0) if shot.get("situation") == "IndividualPlay" else 0,
        "xg_throw_in_set_piece":    lambda shot: (shot.get("expectedGoals") or 0) if shot.get("situation") == "ThrowInSetPiece" else 0,
        "xgot_inside_box":          lambda shot: (shot.get("expectedGoalsOnTarget") or 0) if shot.get("isFromInsideBox") is True else 0,
        "xgot_freekick":            lambda shot: (shot.get("expectedGoalsOnTarget") or 0) if shot.get("situation") == "FreeKick" else 0,
        "xgot_fastbreak":           lambda shot: (shot.get("expectedGoalsOnTarget") or 0) if shot.get("situation") == "FastBreak" else 0,
        "xgot_setpiece":            lambda shot: (shot.get("expectedGoalsOnTarget") or 0) if shot.get("situation") == "SetPiece" else 0,
        "xgot_corner":              lambda shot: (shot.get("expectedGoalsOnTarget") or 0) if shot.get("situation") == "FromCorner" else 0,
        "xgot_header":              lambda shot: (shot.get("expectedGoalsOnTarget") or 0) if shot.get("shotType") == "Header" else 0,
        "xgot_individual_play":     lambda shot: (shot.get("expectedGoalsOnTarget") or 0) if shot.get("situation") == "IndividualPlay" else 0,
        "xgot_throw_in_set_piece":  lambda shot: (shot.get("expectedGoalsOnTarget") or 0) if shot.get("situation") == "ThrowInSetPiece" else 0,
    }

    PLAYER_STATS_EXTRACTOR = {
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
        "blocked_shots": [("shots_blocked", extract_value)],
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
        "id": [("member_id", lambda x: x)],
        "age": [("age", lambda x: x)],
        "name": [("member_name", lambda x: x)],
        "countryName": [("country_name", lambda x: x)],
        "countryCode": [("country_code", lambda x: x)],
        "marketValue": [("market_value", lambda x: x or 0)],
        "positionId": [("position_id", lambda x: x or 0)],
        "position": [("position", lambda x: x or "")],
        "performance": [("rating", lambda x: x.get("rating", 0))],
        "shirtNumber": [("shirt_number", lambda x: int(x) if x and x.isdigit() else 0)],
        "usualPlayingPositionId": [("usual_playing_position_id", lambda x: x or 0)],
        "isCaptain": [("is_captain", lambda x: bool(x))],
        "optaId": [("opta_id", lambda x: x or "")]
    }

    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.formation_resolver = FormationResolver()

    def parse(self, json_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not json_data:
            self.logger.error(f"json data is empty")
            return None

        general = json_data.get('general', {})

        match_id = general.get('matchId')
        if not match_id:
            self.logger.error(f"No match id found in response")
            return None

        home_id = general.get('homeTeam').get('id')
        away_id = general.get('awayTeam').get('id')
        if not home_id or not away_id:
            self.logger.error(f"No team id found in response")
            return None

        content = json_data.get('content', {})
        if not content:
            self.logger.error(f"No content found in response")
            return None

        result = {"match_id": match_id}

        raw_lineup = content.get('lineup')
        if raw_lineup is not None:
            result["lineup"] = self._parse_lineup(match_id, raw_lineup)

        home_goals_penalty, away_goals_penalty = 0, 0
        raw_player_stats = content.get('playerStats')
        if raw_player_stats is not None:
            result["player_stats"], result["shot_stats"], home_goals_penalty, away_goals_penalty = self._parse_player_stats(match_id, home_id, away_id, raw_player_stats)

        stats_root = content.get('stats')
        periods = stats_root.get('Periods') if stats_root else None
        all_periods = periods.get('All') if periods else None
        stat_groups = all_periods.get('stats') if all_periods else None
        if stat_groups is not None:
            result["match_stats"] = self._parse_match_stats(match_id, stat_groups)
            result["match_stats"]["home_goals_penalty"] = home_goals_penalty
            result["match_stats"]["away_goals_penalty"] = away_goals_penalty

        status = json_data.get('header', {}).get('status')
        match_status, kickoff_time, _, _ = extract_status(status, CrawlParams.MATCH_LIFESPAN)
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
            unavailables = team_data.get("unavailable", [])

            self.formation_resolver.resolve(formation, starters)

            groups = [
                (LineupRole.STARTER, starters),
                (LineupRole.SUB, subs),
                (LineupRole.UNAVAILABLE, unavailables),
            ]
            records = []
            seen = set()
            for lineup_role, members in groups:
                for member in members:
                    record = self._create_lineup_record(match_id, team_id, team_name)
                    for key, val in member.items():
                        targets = self.LINEUP_MAPPING.get(key)
                        if not targets:
                            continue

                        for target_key, extractor in targets:
                            record[target_key] = extractor(val)

                    record["role"] = lineup_role.value

                    member_id = record.get("member_id")
                    if member_id and member_id not in seen:
                        seen.add(member_id)
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
                targets = self.MATCH_STATS_EXTRACTOR.get(stat.get("key"))
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
        opta_id: str,
        team_id: int,
        position_id: int,
        is_goalkeeper: bool,
        usual_position: int
    ) -> Dict[str, Any]:
        keys = MatchPlayerStat.get_column_keys(exclude=('created_at', 'updated_at', 'status'))
        record = {key: None for key in keys}
        record["match_id"] = match_id
        record["player_id"] = player_id
        record["player_name"] = player_name
        record["opta_id"] = opta_id
        record["team_id"] = team_id
        record["position_id"] = position_id
        record["is_goalkeeper"] = is_goalkeeper
        record["usual_position"] = usual_position
        return record

    def _create_shot_stat_record(self, match_id: int) -> Dict[str, Any]:
        keys = ShotStat.get_column_keys(exclude=('created_at', 'updated_at', 'status'))
        record = {key: None for key in keys}
        record["match_id"] = match_id
        return record

    def _parse_player_stats(self, match_id: int, home_id: int, away_id: int, player_datas: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, int]:
        player_records = []
        shot_records = []
        home_goals_penalty, away_goals_penalty = 0, 0
        for _, player_data in player_datas.items():
            player_id = player_data.get("id")
            player_name = player_data.get("name")
            opta_id = player_data.get("optaId")
            team_id = player_data.get("teamId")
            position_id = player_data.get("positionId")
            is_goalkeeper = player_data.get("isGoalkeeper")
            usual_position = player_data.get("usualPosition")

            player_record = self._create_player_stats_record(
                match_id, player_id, player_name, opta_id, team_id, position_id, is_goalkeeper, usual_position)

            stat_groups = player_data.get("stats", [])
            for stat_group in stat_groups:
                stats = stat_group.get("stats", {})
                for _, stat in stats.items():
                    targets = self.PLAYER_STATS_EXTRACTOR.get(stat.get("key"))
                    if not targets:
                        continue
                    raw_val = stat.get("stat", {})
                    for target_key, extractor in targets:
                        player_record[target_key] = extractor(raw_val)

            shot_map = player_data.get("shotmap", [])
            for shot in shot_map:
                shot_record = self._create_shot_stat_record(match_id)
                for source_key, targets in self.SHOT_STATS_EXTRACTOR.items():
                    raw_val = shot.get(source_key)
                    for target_key, extractor in targets:
                        shot_record[target_key] = extractor(raw_val)
                shot_records.append(shot_record)

                for target_key, counter in self.SHOT_STATS_COUNTER.items():
                    player_record[target_key] = (player_record[target_key] or 0) + counter(shot)

            player_records.append(player_record)

            goals_penalty = player_record["goals_penalty"] or 0
            if team_id == home_id:
                home_goals_penalty += goals_penalty
            elif team_id == away_id:
                away_goals_penalty += goals_penalty

        self.logger.debug(f"Parsed {len(player_records)} player stats for match {match_id}")
        return player_records, shot_records, home_goals_penalty, away_goals_penalty

class TeamLogoParser:
    def parse(self, json_data: Dict[str, Any], home_code: str, away_code: str) -> List[Dict[str, Any]]:
        event_jsonld = json_data.get('seo', {}).get('eventJSONLD', {})
        home_team = event_jsonld.get('homeTeam') or {}
        away_team = event_jsonld.get('awayTeam') or {}

        records = []
        for team, file_name in ((home_team, home_code), (away_team, away_code)):
            logo_url = team.get('logo')
            if not logo_url or not file_name:
                continue

            records.append({
                'source_url': logo_url,
                'source_site': SiteName.FOTMOB.value,
                'asset_type': 'image',
                'entity_type': 'team',
                'asset_usage': 'logo',
                'file_name': file_name,
                'file_ext': PurePosixPath(urlparse(logo_url).path).suffix.lstrip('.'),
                'next_fetch_at': datetime.now(timezone.utc),
            })

        return records

@TaskRegistry.poll('parse.fotmob.match')
class ParseMatch(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.FOTMOB.value)
        self.payload = payload or {}
        self.match_dao = MatchDao()
        self.asset_dao = AssetDao()
        self.parser = MatchParser()
        self.logo_parser = TeamLogoParser()

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.match_dao.get_pending_parse_items(
                    CrawlParams.PARSE_MAX_RETRIES,
                    CrawlParams.PARSE_BATCH_SIZE
                )

                if not items:
                    self.idle_sleep()
                    continue

                for match_id, kickoff_time, json_body, home_code, away_code in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_data = self.parser.parse(json_body)
                        if parsed_data is None:
                            self.match_dao.mark_parse_failed(match_id, "match data is None")
                            continue

                        new_kickoff_time = datetime.fromisoformat(parsed_data["kickoff_time"])
                        match_status = parsed_data["match_status"]

                        if new_kickoff_time != kickoff_time:
                            self.logger.warning(
                                f"match {match_id} kickoff time changed: {kickoff_time.astimezone(timezone.utc)} -> {new_kickoff_time}"
                            )
                            kickoff_time = new_kickoff_time

                        self.match_dao.sync_parsed_data(parsed_data)
                        self.match_dao.mark_as_parsed(match_id, kickoff_time, match_status)
                        self.logger.info(f"Parsed match: kickoff_time={kickoff_time} match_id={match_id}")

                        team_assets = self.logo_parser.parse(json_body, home_code, away_code)
                        if team_assets:
                            self.asset_dao.insert_assets(team_assets)
                    except Exception as e:
                        self.logger.error(
                            f"Parse failed match_id={match_id} kickoff_time={kickoff_time}\n"
                            f"{json.dumps(parsed_data, indent=2, default=str)}"
                        )
                        full_stack_trace = traceback.format_exc()
                        self.match_dao.mark_parse_failed(match_id, full_stack_trace)
                        self.logger.error(f"Failed to parse match data for match {match_id}: {e}", exc_info=True)

            except Exception as e:
                self.logger.error(f"Failed to parse match data: {e}", exc_info=True)
                self.idle_sleep()
