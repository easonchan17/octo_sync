from enum import IntEnum


class MatchStatus(IntEnum):
    SCHEDULED = 0
    TIMED = 1

    FIRST_HALF = 10
    HALFTIME = 11
    SECOND_HALF = 12
    EXTRA_TIME = 13
    PENALTY = 14

    FINISHED = 20
    FINISHED_AET = 21
    FINISHED_PEN = 22

    POSTPONED = 30
    CANCELLED = 31
