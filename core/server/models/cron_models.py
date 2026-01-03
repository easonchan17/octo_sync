from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class CronStatus(BaseModel):
    running: bool
    state: str
    job_count: int


class CronJob(BaseModel):
    id: str
    name: str
    next_run_time: Optional[datetime] = None
    trigger: str


class CronJobCreate(BaseModel):
    func: str
    name: str
    minute: Optional[int] = None
    hour: Optional[int] = None
    day: Optional[int] = None
    month: Optional[int] = None
    day_of_week: Optional[int] = None
    kwargs: Optional[Dict[str, Any]] = None
