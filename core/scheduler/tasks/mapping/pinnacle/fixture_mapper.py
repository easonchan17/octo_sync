from typing import Any
from core.registry import Registry
from core.store.postgres.models import PinnacleFixture, FotmobFixture
from ..base_mapper import BaseMapper


@Registry.task('sync.pinnacle.map_fixtures')
class FixtureMapper(BaseMapper):
    def execute(self, *args, **kwargs) -> Any:
        self._map_fixtures(raw_model=PinnacleFixture, ref_model=FotmobFixture)
