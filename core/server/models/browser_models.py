from pydantic import BaseModel

class PagePoolStatus(BaseModel):
    capacity: int
    count: int