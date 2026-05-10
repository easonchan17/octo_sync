from typing import Dict, Any
from core.services.base_service import BaseService
from core.store.postgres.daos.fotmob import MatchDao


class MatchService(BaseService):
    def __init__(self):
        super().__init__()
        self.match_dao = MatchDao()

    def get_match_detail(self, match_id: int) -> Dict[str, Any]:
        return self.match_dao.get_raw_data(match_id)
