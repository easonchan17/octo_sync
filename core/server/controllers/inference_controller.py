from typing import Dict, Any
from fastapi import HTTPException, Body, Query
from core.server.services.inference_service import InferenceService
from core.server.controllers.base_controller import BaseController
from core.server.models.api_models import PredictionResponse, Paginated, Pagination, ModelResponse

class InferenceController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.inference_service = InferenceService()
        self.router.get("/models", response_model=Paginated[ModelResponse])(self.get_models)
        self.router.post("/models/{family}/{version}", response_model=bool)(self.load_model)
        self.router.delete("/models/{family}/{version}", response_model=bool)(self.unload_model)
        self.router.post("/models/{family}/{version}/predict", response_model=PredictionResponse)(self.predict)

    def load_model(self, family: str, version: str) -> bool:
        try:
            return self.inference_service.load_model(family, version)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to load model {version}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

    def unload_model(self, family: str, version: str) -> bool:
        try:
            return self.inference_service.unload_model(version)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to unload model {version}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to unload model: {str(e)}")

    def get_models(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Page size")
    ) -> Paginated[ModelResponse]:
        try:
            total, records = self.inference_service.get_models(
                page=page,
                page_size=page_size
            )

            loaded_versions = set(self.inference_service.predictors.keys())
            items = [
                ModelResponse.model_validate({
                    **record.to_dict(),
                    "is_loaded": record.model_version in loaded_versions
                })
                for record in records
            ]

            return Paginated[ModelResponse](
                pagination=Pagination(
                    page=page,
                    page_size=page_size,
                    total=total
                ),
                items=items
            )
        except Exception as e:
            self.logger.error(f"Failed to get models: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

    def predict(self, family: str, version: str, payload: Dict[str, Any] = Body(...)) -> PredictionResponse:
        try:
            result = self.inference_service.predict(version, payload)
            return PredictionResponse(**result)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to make prediction: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to make prediction: {str(e)}")
