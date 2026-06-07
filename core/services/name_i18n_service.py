from functools import cache
from typing import Dict, Optional
from core.services.base_service import BaseService
from core.store.postgres.daos.common import NameI18nDao


class NameI18nService(BaseService):
    def __init__(self) -> None:
        super().__init__()
        self.name_i18n_dao = NameI18nDao()
        self._cache: Dict[str, str] = {}

    def load(self) -> None:
        rows = self.name_i18n_dao.get_all_zh_names()
        self._cache = {row.entity_code: row.name for row in rows}

    def get(self, entity_code: str) -> Optional[str]:
        if entity_code in self._cache:
            return self._cache[entity_code]
        row = self.name_i18n_dao.get_zh_name(entity_code)
        if row:
            self._cache[entity_code] = row.name
            return row.name
        return None


@cache
def get_name_i18n_service() -> NameI18nService:
    return NameI18nService()
