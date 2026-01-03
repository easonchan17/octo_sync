from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional


class SiteBase(BaseModel):
    name: str
    url: HttpUrl


class SiteCreate(SiteBase):
    pass


class SiteRead(SiteBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
