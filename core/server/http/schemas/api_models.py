from pydantic import BaseModel, computed_field, Field
from typing import List, TypeVar, Generic, Optional, Dict, Any
from core.types.enums import MatchStatus
from datetime import datetime
from enum import IntEnum

T = TypeVar('T')


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
# League Models
# ==============================================================================
class LeagueResponse(BaseModel):
    id: int
    name: str
    priority: int

    @computed_field
    @property
    def logo(self) -> str:
        return f"/assets/image/league/logo/{self.id}.png"

    class Config:
        from_attributes = True


# ==============================================================================
# Fixture and Match Models
# ==============================================================================
class DisplayMatchStatus(IntEnum):
    UPCOMING = 0
    LIVE = 1
    FINISHED = 2

class MatchResponse(BaseModel):
    match_code: str
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
    def home_logo(self) -> str:
        return f"/assets/image/team/logo/{self.home_code}.png"

    @computed_field
    @property
    def away_logo(self) -> str:
        return f"/assets/image/team/logo/{self.away_code}.png"

    @computed_field
    @property
    def status(self) -> int:
        ms = MatchStatus(self.match_status)
        if ms.is_playing:
            return DisplayMatchStatus.LIVE
        if ms.is_finalized:
            return DisplayMatchStatus.FINISHED
        return DisplayMatchStatus.UPCOMING

    class Config:
        from_attributes = True

class MatchDetailResponse(MatchResponse):
    league_id: int
    league_name: str
    detail: Dict[str, Any] = Field(validation_alias='json_body')

    @computed_field
    @property
    def league_logo(self) -> str:
        return f"/assets/image/league/logo/{self.league_id}.png"


class FixtureResponse(BaseModel):
    league_id: int
    league_name: str
    priority: int
    matches: List[MatchResponse]

    @computed_field
    @property
    def league_logo(self) -> str:
        return f"/assets/image/league/logo/{self.league_id}.png"


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