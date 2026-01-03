from fastapi import HTTPException, Query
from core.server.services.fixture_service import FixtureService
from core.server.controllers.base_controller import BaseController
from core.server.models.api_models import PaginationInfo, PaginatedDataResponse
from core.server.models.fixture_models import FixtureRead

class FixtureController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.fixture_service = FixtureService()
        self.router.get("/v1/fixtures", response_model=PaginatedDataResponse[FixtureRead])(self.get_fixtures)

    def get_fixtures(
        self,
        status: str = Query(..., description="Match status: finished, live, or upcoming"),
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page")
    ) -> PaginatedDataResponse[FixtureRead]:
        if status not in ['finished', 'live', 'upcoming']:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}. Must be one of: finished, live, upcoming")

        try:
            total, fixtures = self.fixture_service.get_fixtures(
                status=status,
                page=page,
                per_page=per_page
            )

            items = [FixtureRead.model_validate(f) for f in fixtures]

            return PaginatedDataResponse[FixtureRead](
                pagination=PaginationInfo(
                    page=page,
                    per_page=per_page,
                    total=total
                ),
                items=items
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to get fixtures v1: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get fixtures: {str(e)}")
