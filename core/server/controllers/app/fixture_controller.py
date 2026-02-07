from fastapi import HTTPException, Query
from core.server.services.fixture_service import FixtureService
from core.server.controllers.base_controller import BaseController
from core.server.models.api_models import Pagination, Paginated, FixtureResponse, FixtureStatus

class FixtureController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.fixture_service = FixtureService()
        self.router.get("/v1/fixtures", response_model=Paginated[FixtureResponse])(self.get_fixtures)

    def get_fixtures(
        self,
        status: FixtureStatus = Query(..., description="Match status: 0=finished, 1=live, 2=upcoming"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Page size")
    ) -> Paginated[FixtureResponse]:
        try:
            total, fixtures = self.fixture_service.get_fixtures(
                status=status,
                page=page,
                page_size=page_size
            )

            items = [FixtureResponse.model_validate(f) for f in fixtures]

            return Paginated[FixtureResponse](
                pagination=Pagination(
                    page=page,
                    page_size=page_size,
                    total=total
                ),
                items=items
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to get fixtures v1: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get fixtures: {str(e)}")
