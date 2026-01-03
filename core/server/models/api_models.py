from pydantic import BaseModel
from typing import List, TypeVar, Generic

T = TypeVar('T')

class PaginationInfo(BaseModel):
    page: int
    per_page: int
    total: int


class PaginatedDataResponse(BaseModel, Generic[T]):
    pagination: PaginationInfo
    items: List[T]
