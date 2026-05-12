from typing import Dict, Any
from core.services.base_service import BaseService
from core.store.postgres.daos.fotmob import MatchDao


class MatchService(BaseService):
    def __init__(self):
        super().__init__()
        self.match_dao = MatchDao()

    def get_detail(self, match_code: str) -> Dict[str, Any]:
        return self.match_dao.get_raw_data(match_code)
