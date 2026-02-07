from typing import Any
from core.registry import Registry
from core.types.enums import SiteName
from core.store.postgres.models import PinnacleFixture, FotmobFixture
from ..base_mapper import BaseMapper

@Registry.task('sync.pinnacle.map_fixtures')
class FixtureMapper(BaseMapper):
    def execute(self, *args, **kwargs) -> Any:
        self._map_fixtures(
            raw_site=SiteName.PINNACLE.value,
            raw_model=PinnacleFixture,
            ref_site=SiteName.FOTMOB.value,
            ref_model=FotmobFixture
        )
