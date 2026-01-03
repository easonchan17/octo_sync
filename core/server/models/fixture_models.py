from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class FixtureRead(BaseModel):
    match_id: int
    league_name: str
    league_id: int
    kickoff_time: datetime
    round: Optional[str] = None
    home_team: str
    home_id: int
    away_team: str
    away_id: int
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    match_status: int

    class Config:
        from_attributes = True
