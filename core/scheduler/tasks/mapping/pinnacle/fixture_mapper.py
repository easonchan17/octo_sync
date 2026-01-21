from typing import Any
from core.domain.enums import SiteName
from core.store.postgres.models import PinnacleFixture, FotmobFixture
from ..base_mapper import BaseMapper

class FixtureMapper(BaseMapper):
    def execute(self, *args, **kwargs) -> Any:
        self._map_fixtures(
            raw_site=SiteName.PINNACLE.value,
            raw_model=PinnacleFixture,
            ref_site=SiteName.FOTMOB.value,
            ref_model=FotmobFixture
        )
