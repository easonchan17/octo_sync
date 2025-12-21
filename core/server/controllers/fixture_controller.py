from fastapi import HTTPException, Query
from typing import Optional
from datetime import datetime
from core.server.controllers.base_controller import BaseController
from core.server.services.fixture_service import FixtureService
from core.server.models.fixture_models import FixtureResponse, FixtureListResponse


class FixtureController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.fixture_service = FixtureService()

        self.router.get("/fixtures", response_model=FixtureListResponse)(self.get_fixtures)
        self.router.get("/fixtures/{match_id}", response_model=FixtureResponse)(self.get_fixture)

    async def get_fixtures(
        self,
        league_id: Optional[int] = Query(None, description="Filter by league ID"),
        start_date: Optional[datetime] = Query(None, description="Filter by start date"),
        end_date: Optional[datetime] = Query(None, description="Filter by end date"),
        match_status: Optional[int] = Query(None, description="Filter by match status"),
        limit: int = Query(50, ge=1, le=200, description="Number of items to return"),
        offset: int = Query(0, ge=0, description="Number of items to skip")
    ) -> FixtureListResponse:
        try:
            total, fixtures = self.fixture_service.get_fixtures(
                league_id=league_id,
                start_date=start_date,
                end_date=end_date,
                match_status=match_status,
                limit=limit,
                offset=offset
            )
            return FixtureListResponse(
                total=total,
                items=[FixtureResponse.model_validate(f) for f in fixtures]
            )
        except Exception as e:
            self.logger.error(f"Failed to get fixtures: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get fixtures: {str(e)}")

    async def get_fixture(self, match_id: int) -> FixtureResponse:
        try:
            fixture = self.fixture_service.get_fixture(match_id)
            if not fixture:
                raise HTTPException(status_code=404, detail=f"Fixture {match_id} not found")
            return FixtureResponse.model_validate(fixture)
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get fixture {match_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get fixture: {str(e)}")
