from pydantic import BaseModel, computed_field, Field
from typing import List, TypeVar, Generic, Optional, Dict, Any
from core.types.enums import MatchStatus
from datetime import datetime
from enum import IntEnum

T = TypeVar('T')

TEAM_LOGO_URL = "/media/image/team/logo/{team_code}.png"
LEAGUE_LOGO_URL = "/media/image/league/logo/{league_id}.png"
PLAYER_LOGO_URL = "/media/image/player/logo/{player_code}.png"


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
        return LEAGUE_LOGO_URL.format(league_id=self.id)

    class Config:
        from_attributes = True


# ==============================================================================
# Fixture and Match Models
# ==============================================================================
class DisplayMatchStatus(IntEnum):
    UPCOMING = 0
    LIVE = 1
    FINISHED = 2


class BaseMatchResponse(BaseModel):
    match_code: str
    kickoff_time: datetime
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
        return TEAM_LOGO_URL.format(team_code=self.home_code)

    @computed_field
    @property
    def away_logo(self) -> str:
        return TEAM_LOGO_URL.format(team_code=self.away_code)

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


class MatchResponse(BaseMatchResponse):
    round: Optional[str] = None


class FixtureResponse(BaseModel):
    league_id: int
    league_name: str
    priority: int
    matches: List[MatchResponse]

    @computed_field
    @property
    def league_logo(self) -> str:
        return LEAGUE_LOGO_URL.format(league_id=self.league_id)


# ==============================================================================
# Match Detail Models
# ==============================================================================
class SwapPlayerResponse(BaseModel):
    name: Optional[str] = None


class EventResponse(BaseModel):
    time: Optional[int] = None
    type: Optional[str] = None
    is_home: Optional[bool] = Field(default=None, validation_alias='isHome')
    home_score: Optional[int] = Field(default=None, validation_alias='homeScore')
    away_score: Optional[int] = Field(default=None, validation_alias='awayScore')
    new_scores: Optional[List[int]] = Field(default=None, validation_alias='newScore')
    player_name: Optional[str] = Field(default=None, validation_alias='nameStr')
    card: Optional[str] = None
    assist: Optional[str] = Field(default=None, validation_alias='assistStr')
    own_goal: Optional[bool] = Field(default=None, validation_alias='ownGoal')
    swap: Optional[List[SwapPlayerResponse]] = None
    half: Optional[str] = Field(default=None, validation_alias='halfStrShort')
    minutes_added: Optional[str] = Field(default=None, validation_alias='minutesAddedStr')
    is_penalty_shootout_event: Optional[bool] = Field(default=None, validation_alias='isPenaltyShootoutEvent')
    pen_shootout_scores: Optional[List[int]] = Field(default=None, validation_alias='penShootoutScore')
    overload_time: Optional[int] = Field(default=None, validation_alias='overloadTime')
    injured_player_out: Optional[bool] = Field(default=None, validation_alias='injuredPlayerOut')


class ShotResponse(BaseModel):
    x: Optional[float] = None
    y: Optional[float] = None
    min: Optional[int] = None
    min_added: Optional[int] = None
    period: Optional[str] = None
    player_name: Optional[str] = None
    shot_type: Optional[str] = None
    event_type: Optional[str] = None
    situation: Optional[str] = None
    is_on_target: Optional[bool] = None
    is_blocked: Optional[bool] = None
    is_own_goal: Optional[bool] = None
    xg: Optional[float] = None
    xgot: Optional[float] = None
    on_goal_shot_x: Optional[float] = None
    on_goal_shot_y: Optional[float] = None
    goal_y: Optional[float] = None
    goal_z: Optional[float] = None
    team_code: Optional[str] = None
    player_code: Optional[str] = None

    @computed_field
    @property
    def team_logo(self) -> Optional[str]:
        return TEAM_LOGO_URL.format(team_code=self.team_code) if self.team_code else None

    @computed_field
    @property
    def player_logo(self) -> Optional[str]:
        return PLAYER_LOGO_URL.format(player_code=self.player_code) if self.player_code else None


class WeatherResponse(BaseModel):
    description: Optional[str] = None
    temperature: Optional[int] = None
    wind_speed: Optional[float] = Field(default=None, validation_alias='windSpeed')
    wind_direction: Optional[str] = Field(default=None, validation_alias='windDirectionCardinal')
    precipitation: Optional[float] = None


class PlayerResponse(BaseModel):
    player_name: str = Field(validation_alias='member_name')
    player_code: str
    shirt_number: Optional[int] = None
    position: Optional[str] = None
    role: Optional[int] = None
    is_captain: Optional[bool] = None
    rating: Optional[float] = None

    @computed_field
    @property
    def player_logo(self) -> str:
        return PLAYER_LOGO_URL.format(player_code=self.player_code)

    class Config:
        from_attributes = True


class RecentMatchResponse(BaseMatchResponse):
    ref_league_id: Optional[int] = Field(default=None, serialization_alias='league_id')
    league_name: str

    @computed_field
    @property
    def league_logo(self) -> Optional[str]:
        return LEAGUE_LOGO_URL.format(league_id=self.ref_league_id) if self.ref_league_id else None


class MatchDetail(BaseModel):
    events: Optional[List[EventResponse]] = None
    shot_map: List[ShotResponse] = []
    momentum: Optional[List[Any]] = None
    weather: Optional[WeatherResponse] = None
    stats: Optional[Dict[str, Any]] = None
    lineup: Dict[str, List[PlayerResponse]] = {}
    form: Dict[str, List[RecentMatchResponse]] = {}
    h2h: List[RecentMatchResponse] = []


class MatchDetailResponse(MatchResponse):
    league_id: Optional[int] = None
    league_name: Optional[str] = None
    detail: MatchDetail

    @computed_field
    @property
    def league_logo(self) -> Optional[str]:
        return LEAGUE_LOGO_URL.format(league_id=self.league_id) if self.league_id else None


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
