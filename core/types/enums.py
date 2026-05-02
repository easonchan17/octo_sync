from enum import IntEnum, Enum
from typing import NamedTuple, Optional, List, Dict, Any

class OddsMarket(NamedTuple):
    betting_type_id: int
    scope_id: int
    betting_type_slug: str
    outcomes: Optional[dict[str, str]] = None

class OddsMarkets:
    FT_1X2 = OddsMarket(betting_type_id=1, scope_id=2, betting_type_slug='1X2', outcomes={"home": "0", "draw": "1", "away": "2"})
    FT_AH  = OddsMarket(betting_type_id=5, scope_id=2, betting_type_slug='ah', outcomes={"home": "0", "away": "1"})


class UpsertStrategy(str, Enum):
    OVERWRITE = "overwrite"
    IF_ABSENT = "if_absent"
    KEEP_MIN = "keep_min"
    KEEP_MAX = "keep_max"

class SiteName(str, Enum):
    SYSTEM = 'system'
    FBREF = 'fbref'
    FOTMOB = 'fotmob'
    PINNACLE = 'pinnacle'
    FOOTBALL_DATA = 'football_data'
    ODDSPORTAL = 'oddsportal'

class LeagueID(IntEnum):
    UNKNOWN = 0
    PREMIER_LEAGUE = 101
    LA_LIGA = 102
    SERIE_A = 103
    BUNDESLIGA = 104
    LIGUE_1 = 105

class LeaguePriority(IntEnum):
    LEVEL_GLOBAL = 1000
    LEVEL_MAJOR = 500
    LEVEL_REGIONAL = 100
    LEVEL_BASIC = 50
    LEVEL_NONE = 0

class MatchStatus(IntEnum):
    SCHEDULED = 0
    TIMED = 1

    IN_PROGRESS = 9

    FIRST_HALF = 10
    HALFTIME = 11
    SECOND_HALF = 12
    EXTRA_TIME = 13
    PENALTY = 14

    FINISHED = 20
    FINISHED_AET = 21
    FINISHED_PEN = 22
    FINISHED_AWARDED = 23

    POSTPONED = 30
    CANCELLED = 31

    @classmethod
    def natural_finals(cls) -> list:
        return [cls.FINISHED.value, cls.FINISHED_AET.value, cls.FINISHED_PEN.value]

    @property
    def is_aborted(self) -> bool:
        return self in (
            MatchStatus.POSTPONED,
            MatchStatus.CANCELLED,
            MatchStatus.FINISHED_AWARDED
        )

    @property
    def is_finished(self) -> bool:
        return self in (
            MatchStatus.FINISHED,
            MatchStatus.FINISHED_AET,
            MatchStatus.FINISHED_PEN,
            MatchStatus.FINISHED_AWARDED
        )

    @property
    def is_finalized(self) -> bool:
        return self in (
            MatchStatus.FINISHED,
            MatchStatus.FINISHED_AET,
            MatchStatus.FINISHED_PEN,
            MatchStatus.FINISHED_AWARDED,
            MatchStatus.POSTPONED,
            MatchStatus.CANCELLED
        )

    @property
    def is_playing(self) -> bool:
        return self in (
            MatchStatus.IN_PROGRESS,
            MatchStatus.FIRST_HALF,
            MatchStatus.HALFTIME,
            MatchStatus.SECOND_HALF,
            MatchStatus.EXTRA_TIME,
            MatchStatus.PENALTY
        )

class Position(str, Enum):
    # ==========================================
    # Goalkeeper
    # ==========================================
    GK  = "GK"   # Goalkeeper

    # ==========================================
    # Defenders - Center Backs
    # ==========================================
    CB  = "CB"   # Center Back
    LCB = "LCB"  # Left Center Back
    RCB = "RCB"  # Right Center Back

    # ==========================================
    # Defenders - Full Backs
    # ==========================================
    LB  = "LB"   # Left Back
    RB  = "RB"   # Right Back

    # ==========================================
    # Defenders/Midfielders - Wing Backs
    # ==========================================
    LWB = "LWB"  # Left Wing Back
    RWB = "RWB"  # Right Wing Back

    # ==========================================
    # Midfielders - Defensive
    # ==========================================
    CDM = "CDM"  # Central Defensive Midfielder
    LDM = "LDM"  # Left Defensive Midfielder
    RDM = "RDM"  # Right Defensive Midfielder

    # ==========================================
    # Midfielders - Central
    # ==========================================
    CM  = "CM"   # Central Midfielder
    LCM = "LCM"  # Left Central Midfielder
    RCM = "RCM"  # Right Central Midfielder

    # ==========================================
    # Midfielders - Wide
    # ==========================================
    LM  = "LM"   # Left Midfielder
    RM  = "RM"   # Right Midfielder

    # ==========================================
    # Midfielders - Attacking
    # ==========================================
    CAM = "CAM"  # Central Attacking Midfielder
    LAM = "LAM"  # Left Attacking Midfielder
    RAM = "RAM"  # Right Attacking Midfielder

    # ==========================================
    # Attackers - Wingers
    # ==========================================
    LW  = "LW"   # Left Winger
    RW  = "RW"   # Right Winger

    # ==========================================
    # Attackers - Forwards & Strikers
    # ==========================================
    CF  = "CF"   # Center Forward
    ST  = "ST"   # Striker
    LST = "LST"  # Left Striker
    RST = "RST"  # Right Striker
    SS  = "SS"   # Second Striker

    ATTACK_POSITIONS    = ["FW", "LW", "RW"]
    PLAYMAKER_POSITIONS = ["AM", "CM", "LM", "RM", "DM", "WB"]
    DEFENSE_POSITIONS   = ["DF", "CB", "LB", "RB", "DM", "WB"]
    AERIAL_POSITIONS    = ["DF", "CB", "LB", "RB", "DM", "WB", "FW"]
    GK_POSITIONS        = ["GK"]