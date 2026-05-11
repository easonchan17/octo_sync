from typing import Optional, Dict, Any
from .base import BaseSampleBuilder


class PredictSampleBuilder(BaseSampleBuilder):
    def __init__(self, match_id: int) -> None:
        super().__init__()
        self.match_id = match_id

    def build(self) -> Optional[Dict[str, Any]]:
        raise NotImplementedError
