from pydantic import BaseModel, computed_field, Field, field_serializer
from core.services.name_i18n_service import get_name_i18n_service
from typing import List, TypeVar, Generic, Optional, Dict, Any
from core.types.enums import MatchStatus, BookmakerID, BROAD_POSITION
from datetime import datetime
from enum import IntEnum

T = TypeVar('T')

TEAM_LOGO_URL = "/media/image/team/logo/{team_code}.png"
LEAGUE_LOGO_URL = "/media/image/league/logo/{league_id}.png"
PLAYER_LOGO_URL = "/media/image/player/logo/{player_code}.png"

KNOCKOUT_STAGE_ZH = {
    "1/16":    "1/16决赛",
    "1/8":     "1/8决赛",
    "1/4":     "1/4决赛",
    "1/2":     "半决赛",
    "bronze":  "季军赛",
    "final":   "决赛",
    "playoff": "附加赛",
}

BOOKMAKER_ZH: Dict[int, str] = {
    BookmakerID.BETFAIR_EXCHANGE.value: "动态",
    BookmakerID.BETINASIA.value: "基准",
}



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
# League Models
# ==============================================================================
class LeagueResponse(BaseModel):
    id: int
    name: str
    priority: int

    @field_serializer('name')
    def serialize_name(self, value: str) -> str:
        return get_name_i18n_service().get(str(self.id)) or value

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


class ProbFormat(IntEnum):
    DECIMAL = 0
    PERCENT = 1

DEFAULT_PROB_FORMAT = ProbFormat.PERCENT


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

    @field_serializer('home_team')
    def serialize_home_team(self, value: str) -> str:
        return get_name_i18n_service().get(self.home_code) or value

    @field_serializer('away_team')
    def serialize_away_team(self, value: str) -> str:
        return get_name_i18n_service().get(self.away_code) or value

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
    group_name: Optional[str] = None

    @field_serializer('round')
    def serialize_round(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        zh = KNOCKOUT_STAGE_ZH.get(value)
        return zh if zh else f"第{value}轮"

    @field_serializer('group_name')
    def serialize_group_name(self, value: Optional[str]) -> Optional[str]:
        return f"{value}组" if value else value


class FixtureResponse(BaseModel):
    league_id: int
    league_name: str
    priority: int
    matches: List[MatchResponse]

    @field_serializer('league_name')
    def serialize_league_name(self, value: str) -> str:
        return get_name_i18n_service().get(str(self.league_id)) or value

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


class StadiumResponse(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    surface: Optional[str] = None


class PlayerResponse(BaseModel):
    player_name: str
    player_code: str
    shirt_number: Optional[int] = None
    position: Optional[str]
    usual_playing_position_id: Optional[int] = Field(default=None, exclude=True)
    role: Optional[int] = None
    is_captain: Optional[bool] = None
    rating: Optional[float] = None

    @computed_field
    @property
    def usual_position(self) -> Optional[str]:
        if self.usual_playing_position_id is not None:
            entry = BROAD_POSITION.get(self.usual_playing_position_id)
            return entry[1] if entry else None
        return None

    @computed_field
    @property
    def player_logo(self) -> str:
        return PLAYER_LOGO_URL.format(player_code=self.player_code)

    class Config:
        from_attributes = True


class RecentMatchResponse(BaseMatchResponse):
    ref_league_id: Optional[int] = Field(default=None, serialization_alias='league_id')
    league_name: str

    @field_serializer('league_name')
    def serialize_league_name(self, value: str) -> str:
        if self.ref_league_id:
            return get_name_i18n_service().get(str(self.ref_league_id)) or value
        return value

    @computed_field
    @property
    def league_logo(self) -> Optional[str]:
        return LEAGUE_LOGO_URL.format(league_id=self.ref_league_id) if self.ref_league_id else None

class MatchPredictionResponse(BaseModel):
    label: str = "AI预测"
    model_version: str
    probabilities: Dict[str, float]
    probability_labels: List[str] = ["主队", "平局", "客队"]
    prediction: int
    confidence: Optional[float] = None
    confidence_label: str = "置信度"
    predicted_at: Optional[datetime] = None
    predicted_at_label: str = "预测时间"

    @field_serializer('probabilities')
    def serialize_probabilities(self, values: Dict[str, float]) -> list:
        ordered = [values[k] for k in ("2", "1", "0")]
        if DEFAULT_PROB_FORMAT == ProbFormat.PERCENT:
            return [f"{round(v * 100)}%" for v in ordered]
        return [round(v, 2) for v in ordered]

class ProbsItemResponse(BaseModel):
    bookmaker_id: Optional[int] = Field(default=None, exclude=True)
    open_label: str = "初"
    close_label: str = "即"
    open: List[Optional[float]] = []
    close: List[Optional[float]] = []
    movement: List[Optional[str]] = []
    change_time: List[Optional[datetime]] = []

    @computed_field
    @property
    def label(self) -> str:
        return BOOKMAKER_ZH.get(self.bookmaker_id) if self.bookmaker_id else "综合"

    @field_serializer('open', 'close')
    def serialize_probs(self, values: List[Optional[float]]) -> list:
        if DEFAULT_PROB_FORMAT == ProbFormat.PERCENT:
            return [f"{round(v * 100)}%" if v is not None else v for v in values]
        return [round(v, 2) if v is not None else v for v in values]


class AhProbsItemResponse(ProbsItemResponse):
    @field_serializer('open', 'close')
    def serialize_probs(self, values: List[Optional[float]]) -> list:
        if DEFAULT_PROB_FORMAT == ProbFormat.PERCENT:
            return [f"{round(v * 100)}%" if v is not None and i != 1 else v for i, v in enumerate(values)]
        return [round(v, 2) if v is not None else v for v in values]


class EuProbsResponse(BaseModel):
    label: str = "常规"
    columns: List[str] = ["主队", "平局", "客队"]
    avg: Optional[ProbsItemResponse] = None
    bookmakers: List[ProbsItemResponse] = []


class AhProbsResponse(BaseModel):
    label: str = "让球"
    columns: List[str] = ["主队", "让", "客队"]
    avg: Optional[AhProbsItemResponse] = None
    bookmakers: List[AhProbsItemResponse] = []

class ProbsResponse(BaseModel):
    label: str = "概率分析"
    eu: Optional[EuProbsResponse] = None
    ah: Optional[AhProbsResponse] = None


class StandingResponse(BaseModel):
    position: Optional[int] = Field(default=None, validation_alias='idx')
    team_name: Optional[str] = Field(default=None, validation_alias='name')
    team_code: Optional[str] = None
    points: Optional[int] = Field(default=None, validation_alias='pts')
    played: Optional[int] = None
    wins: Optional[int] = None
    draws: Optional[int] = None
    losses: Optional[int] = None
    goals: Optional[str] = Field(default=None, validation_alias='scoresStr')
    goal_diff: Optional[int] = Field(default=None, validation_alias='goalConDiff')
    qual_color: Optional[str] = Field(default=None, validation_alias='qualColor')
    deduction: Optional[int] = None
    xg: Optional[float] = None
    xg_diff: Optional[float] = Field(default=None, validation_alias='xgDiff')
    xga: Optional[float] = Field(default=None, validation_alias='xgConceded')
    xga_diff: Optional[float] = Field(default=None, validation_alias='xgConcededDiff')
    x_points: Optional[float] = Field(default=None, validation_alias='xPoints')
    x_points_diff: Optional[float] = Field(default=None, validation_alias='xPointsDiff')
    x_position: Optional[int] = Field(default=None, validation_alias='xPosition')
    x_position_diff: Optional[int] = Field(default=None, validation_alias='xPositionDiff')

    @field_serializer('team_name')
    def serialize_team_name(self, value: Optional[str]) -> Optional[str]:
        if self.team_code:
            return get_name_i18n_service().get(self.team_code) or value
        return value

    @computed_field
    @property
    def team_logo(self) -> Optional[str]:
        return TEAM_LOGO_URL.format(team_code=self.team_code) if self.team_code else None


class StandingsResponse(BaseModel):
    all: Optional[List[StandingResponse]] = None
    home: Optional[List[StandingResponse]] = None
    away: Optional[List[StandingResponse]] = None
    xg: Optional[List[StandingResponse]] = None

class KnockoutMatchupResponse(BaseModel):
    home_short_name: str          = Field(validation_alias='homeTeamShortName')
    away_short_name: str          = Field(validation_alias='awayTeamShortName')
    home_score: Optional[int]     = Field(default=None, validation_alias='homeScore')
    away_score: Optional[int]     = Field(default=None, validation_alias='awayScore')
    home_code:   Optional[str]    = Field(default=None)
    away_code:   Optional[str]    = Field(default=None)
    winner_code: Optional[str]    = Field(default=None)

    @computed_field
    @property
    def home_logo(self) -> Optional[str]:
        return TEAM_LOGO_URL.format(team_code=self.home_code) if self.home_code else None

    @computed_field
    @property
    def away_logo(self) -> Optional[str]:
        return TEAM_LOGO_URL.format(team_code=self.away_code) if self.away_code else None


class KnockoutRoundResponse(BaseModel):
    stage: str
    matchups: List[KnockoutMatchupResponse]

    @field_serializer('stage')
    def serialize_stage(self, value: str) -> str:
        return KNOCKOUT_STAGE_ZH.get(value, value)


class MatchDetail(BaseModel):
    events: Optional[List[EventResponse]] = None
    shot_map: List[ShotResponse] = []
    momentum: Optional[List[Any]] = None
    weather: Optional[WeatherResponse] = None
    stadium: Optional[StadiumResponse] = None
    stats: Optional[Dict[str, Any]] = None
    lineup: Dict[str, List[PlayerResponse]] = {}
    form: Dict[str, List[RecentMatchResponse]] = {}
    h2h: List[RecentMatchResponse] = []
    probs: Optional[ProbsResponse] = None
    prediction: Optional[MatchPredictionResponse] = None
    standings: Optional[StandingsResponse] = None
    knockout: Optional[List[KnockoutRoundResponse]] = None


class MatchDetailResponse(MatchResponse):
    league_id: Optional[int] = None
    league_name: Optional[str] = None
    detail: MatchDetail

    @field_serializer('league_name')
    def serialize_league_name(self, value: Optional[str]) -> Optional[str]:
        if self.league_id:
            return get_name_i18n_service().get(str(self.league_id)) or value
        return value

    @computed_field
    @property
    def league_logo(self) -> Optional[str]:
        return LEAGUE_LOGO_URL.format(league_id=self.league_id) if self.league_id else None

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
# Chat Models
# ==============================================================================
class ConversationSummaryResponse(BaseModel):
    conversation_id: str
    title: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationMessageResponse(BaseModel):
    role: str
    content: Any


# ==============================================================================
# Auth Models
# ==============================================================================
class SendCodeRequest(BaseModel):
    email: str
    turnstileToken: str


class LoginRequest(BaseModel):
    email: str
    code: str
