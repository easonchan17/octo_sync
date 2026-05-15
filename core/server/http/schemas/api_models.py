from pydantic import BaseModel, computed_field, Field
from typing import List, TypeVar, Generic, Optional, Dict, Any
from core.types.enums import MatchStatus
from datetime import datetime
from enum import IntEnum

T = TypeVar('T')


class FixtureStatus(IntEnum):
    UPCOMING = 0
    LIVE = 1
    FINISHED = 2

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
    match_code: str
    league_name: str
    kickoff_time: datetime
    round: Optional[str] = None
    home_code: str
    home_team: str
    away_code: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    match_status: int = Field(exclude=True)

    @computed_field
    @property
    def status(self) -> int:
        ms = MatchStatus(self.match_status)
        if ms.is_playing:
            return FixtureStatus.LIVE
        if ms.is_finalized:
            return FixtureStatus.FINISHED
        return FixtureStatus.UPCOMING

    class Config:
        from_attributes = True


class GroupedFixturesResponse(BaseModel):
    league_id: int
    league_name: str
    priority: int
    fixtures: List[FixtureResponse]


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
    match_code: str
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
