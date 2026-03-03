from enum import IntEnum, Enum

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
            MatchStatus.CANCELLED
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
