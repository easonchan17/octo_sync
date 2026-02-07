from datetime import timedelta
from typing import List, Optional
from fastapi import HTTPException, Query
from core.utils.datetime_utils import begin_time_of_date
from core.server.services.fixture_service import FixtureService
from core.server.controllers.base_controller import BaseController
from core.server.models.api_models import FixtureResponse

class FixtureController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.fixture_service = FixtureService()
        self.router.get("/v1/fixtures", response_model=List[FixtureResponse])(self.get_fixtures)

    def get_fixtures(
        self,
        match_date: str = Query(..., alias="date", description="Match date (YYYYMMDD), calendar day in given timezone"),
        timezone: Optional[str] = Query(None, description="IANA timezone e.g. Asia/Shanghai; default UTC")
    ) -> List[FixtureResponse]:
        try:
            start_time = begin_time_of_date(match_date, "%Y%m%d", timezone)
            end_time = start_time + timedelta(days=1)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        try:
            fixtures = self.fixture_service.get_fixtures(start_time=start_time, end_time=end_time)
            return [FixtureResponse.model_validate(fixture) for fixture in fixtures]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to get fixtures v1: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get fixtures: {str(e)}")
