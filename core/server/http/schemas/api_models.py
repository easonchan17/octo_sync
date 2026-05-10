from pydantic import BaseModel
from typing import List, TypeVar, Generic, Optional, Dict, Any
from datetime import datetime
from enum import IntEnum

T = TypeVar('T')


class FixtureStatus(IntEnum):
    FINISHED = 0
    LIVE = 1
    UPCOMING = 2

    def to_string(self) -> str:
        mapping = {
            FixtureStatus.FINISHED: "finished",
            FixtureStatus.LIVE: "live",
            FixtureStatus.UPCOMING: "upcoming"
        }
        return mapping.get(self, "finished")

# ==============================================================================
# Pagination Models
# ==============================================================================
class Pagination(BaseModel):
    page: int
    page_size: int
    total: int


class Paginated(BaseModel, Generic[T]):
    pagination: Pagination
    items: List[T]


# ==============================================================================
# Fixture Models
# ==============================================================================
class FixtureResponse(BaseModel):
    id: int
    league_name: str
    kickoff_time: datetime
    round: Optional[str] = None
    home_id: int
    home_team: str
    away_id: int
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None

    class Config:
        from_attributes = True


class GroupedFixturesResponse(BaseModel):
    league_id: int
    league_name: str
    priority: int
    fixtures: List[FixtureResponse]


# ==============================================================================
# Match Detail Models
# ==============================================================================
class MatchStatResponse(BaseModel):
    home_possession: Optional[int] = None
    away_possession: Optional[int] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_xg: Optional[float] = None
    away_xg: Optional[float] = None
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None

    class Config:
        from_attributes = True


class MatchLineupResponse(BaseModel):
    match_id: int
    team_id: int
    team_name: Optional[str] = None
    member_id: int
    member_name: str
    shirt_number: Optional[int] = None
    position_id: Optional[int] = None
    role: int
    is_captain: bool = False
    rating: Optional[float] = None

    class Config:
        from_attributes = True


class MatchPlayerStatResponse(BaseModel):
    match_id: int
    player_id: int
    player_name: str
    rating: Optional[float] = None
    minutes_played: Optional[int] = None
    goals: Optional[int] = None
    assists: Optional[int] = None
    shots: Optional[int] = None
    xg: Optional[float] = None
    xa: Optional[float] = None

    class Config:
        from_attributes = True


class MatchDetailResponse(BaseModel):
    fixture: FixtureResponse
    match_stats: Optional[MatchStatResponse] = None
    lineups: List[MatchLineupResponse] = []
    player_stats: List[MatchPlayerStatResponse] = []

    class Config:
        from_attributes = True


# ==============================================================================
# Cron Models
# ==============================================================================
class CronStatus(BaseModel):
    running: bool
    state: str
    job_count: int


class CronJobRequest(BaseModel):
    func: str
    name: str
    minute: Optional[int] = None
    hour: Optional[int] = None
    day: Optional[int] = None
    month: Optional[int] = None
    day_of_week: Optional[int] = None
    kwargs: Optional[Dict[str, Any]] = None


class CronJobResponse(BaseModel):
    id: str
    name: str
    next_run_time: Optional[datetime] = None
    trigger: str


# ==============================================================================
# Inference Models
# ==============================================================================
class ModelResponse(BaseModel):
    model_version: str
    model_type: str
    dataset_name: str
    train_score: float
    test_score: float
    is_loaded: bool
    feature_names: List[str]
    created_at: datetime

    class Config:
        from_attributes = True

class PredictionResponse(BaseModel):
    fixture_id: int
    model_version: str
    probabilities: Dict[str, float]
    prediction: int


# ==============================================================================
# League Models
# ==============================================================================
class LeagueResponse(BaseModel):
    id: int
    name: str
    priority: int

    class Config:
        from_attributes = True
