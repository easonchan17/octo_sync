from fastapi import HTTPException, Query
from core.server.http.controllers.base_controller import BaseController
from core.services.model_service import ModelService
from core.server.http.schemas.api_models import Paginated, Pagination, ModelResponse

class ModelController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.model_service = ModelService()
        self.router.get("/models", response_model=Paginated[ModelResponse])(self.get_models)
        self.router.post("/models/{family}/{version}/load", response_model=str)(self.load_model)
        self.router.post("/models/{family}/{version}/unload", response_model=str)(self.unload_model)

    def load_model(self, family: str, version: str) -> str:
        try:
            return self.model_service.load(family, version)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to load model {version}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

    def unload_model(self, family: str, version: str) -> str:
        try:
            return self.model_service.unload(version)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to unload model {family} {version}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to unload model {family} {version}: {str(e)}")

    def get_models(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Page size")
    ) -> Paginated[ModelResponse]:
        try:
            total, records = self.model_service.get_list(
                page=page,
                page_size=page_size
            )

            return Paginated[ModelResponse](
                pagination=Pagination(
                    page=page,
                    page_size=page_size,
                    total=total
                ),
                items=[ModelResponse.model_validate(record) for record in records]
            )
        except Exception as e:
            self.logger.error(f"Failed to get models: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")
