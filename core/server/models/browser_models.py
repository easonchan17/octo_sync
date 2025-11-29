from pydantic import BaseModel

class PagePoolStatus(BaseModel):
    total_created: int
    available_in_pool: int
    max_size: int
    in_use: int