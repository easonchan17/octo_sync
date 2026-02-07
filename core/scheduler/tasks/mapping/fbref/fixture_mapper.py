from typing import Any
from core.types.enums import SiteName
from core.store.postgres.models import FbrefFixture, FotmobFixture
from ..base_mapper import BaseMapper

class FixtureMapper(BaseMapper):
    def execute(self, *args, **kwargs) -> Any:
        self._map_fixtures(
            raw_site=SiteName.FBREF.value,
            raw_model=FbrefFixture,
            ref_site=SiteName.FOTMOB.value,
            ref_model=FotmobFixture
        )
