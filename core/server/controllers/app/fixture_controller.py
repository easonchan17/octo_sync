from datetime import timedelta
from typing import List, Optional
from fastapi import HTTPException, Query
from core.utils.datetime_utils import begin_time_of_date
from core.services.fixture_service import FixtureService
from core.server.controllers.base_controller import BaseController
from core.server.schemas.api_models import GroupedFixturesResponse
from core.types.enums import LeaguePriority

class FixtureController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.fixture_service = FixtureService()
        self.router.get("/v1/fixtures", response_model=List[GroupedFixturesResponse])(self.get_fixtures)

    def get_fixtures(
        self,
        match_date: str = Query(..., alias="date", description="Match date (YYYYMMDD), calendar day in given timezone"),
        timezone: Optional[str] = Query(None, description="IANA timezone e.g. Asia/Shanghai; default UTC"),
    ) -> List[GroupedFixturesResponse]:
        try:
            start_time = begin_time_of_date(match_date, "%Y%m%d", timezone)
            grouped_fixtures = self.fixture_service.get_grouped_fixtures(
                start_time=start_time,
                end_time=start_time + timedelta(days=1),
                min_priority=LeaguePriority.LEVEL_REGIONAL.value
            )
            return [GroupedFixturesResponse.model_validate(group) for group in grouped_fixtures]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to get fixtures v1: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get fixtures: {str(e)}")
