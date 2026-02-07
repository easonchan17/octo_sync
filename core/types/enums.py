from enum import IntEnum, Enum

class UpsertStrategy(str, Enum):
    OVERWRITE = "overwrite"
    IF_ABSENT = "if_absent"
    KEEP_MIN = "keep_min"
    KEEP_MAX = "keep_max"

class SiteName(str, Enum):
    FBREF = 'fbref'
    FOTMOB = 'fotmob'
    PINNACLE = 'pinnacle'
    FOOTBALL_DATA = 'football-data'

class LeagueID(IntEnum):
    EPL = 101
    LALIGA = 102

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
