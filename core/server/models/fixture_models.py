from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FixtureResponse(BaseModel):
    id: int
    match_id: int
    league_id: int
    league_name: str
    kickoff_time: datetime
    round: Optional[str] = None
    home_team: str
    home_id: int
    away_team: str
    away_id: int
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    home_xg: Optional[float] = None
    away_xg: Optional[float] = None
    match_status: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FixtureListResponse(BaseModel):
    total: int
    items: List[FixtureResponse]
