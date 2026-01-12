from pydantic import BaseModel, HttpUrl
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
# Site Models
# ==============================================================================
class SiteBase(BaseModel):
    name: str
    url: HttpUrl


class SiteRequest(SiteBase):
    pass


class SiteResponse(SiteBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


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
    created_at: datetime

    class Config:
        from_attributes = True

class PredictionResponse(BaseModel):
    model_version: str
    probabilities: Dict[str, float]
    prediction: int