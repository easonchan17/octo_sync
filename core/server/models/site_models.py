from pydantic import BaseModel, Field
from datetime import datetime

class SiteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Site name")
    url: str = Field(..., description="Site URL")

class SiteCreate(SiteBase):
    pass

class SiteResponse(SiteBase):
    id: int
    create_at: datetime
    update_at: datetime

    class Config:
        from_attributes = True