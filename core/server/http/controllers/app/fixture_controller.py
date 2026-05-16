from datetime import timedelta
from typing import List
from fastapi import HTTPException, Query
from core.utils.datetime_utils import begin_time_of_date
from core.services.fixture_service import FixtureService
from core.server.http.controllers.base_controller import BaseController
from core.server.http.schemas.api_models import FixtureResponse

class FixtureController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.fixture_service = FixtureService()
        self.router.get("/v1/fixtures", response_model=List[FixtureResponse])(self.get_fixtures)

    def get_fixtures(
        self,
        match_date: str = Query(..., alias="date", description="Match date (YYYYMMDD) in UTC"),
    ) -> List[FixtureResponse]:
        try:
            start_time = begin_time_of_date(match_date, "%Y%m%d", "Asia/Shanghai")
            fixture_groups = self.fixture_service.get_fixture_groups(
                start_time=start_time,
                end_time=start_time + timedelta(days=1)
            )
            return [FixtureResponse.model_validate(fixture_group) for fixture_group in fixture_groups]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to get fixtures v1: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get fixtures: {str(e)}")
