from typing import Optional, Dict, Any
from fastapi import HTTPException, Query, Body
from core.server.services.training_service import TrainingService
from core.server.controllers.base_controller import BaseController
from core.server.services.prediction_service import PredictionService
from core.server.models.api_models import Paginated, Pagination, ModelResponse

class ModelController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.training_service = TrainingService()
        self.prediction_service = PredictionService()
        self.router.get("/models", response_model=Paginated[ModelResponse])(self.get_models)
        self.router.post("/models/{family}/{version}/load", response_model=str)(self.load_model)
        self.router.post("/models/{family}/{version}/unload", response_model=str)(self.unload_model)
        self.router.post("/models/{family}/sites/{site_name}/datasets", response_model=str)(self.create_dataset)
        self.router.post("/models/{family}/trainings", response_model=str)(self.start_training)
        self.router.delete("/models/{family}/trainings/{task_id}", response_model=str)(self.stop_training)

    def load_model(self, family: str, version: str) -> str:
        try:
            return self.prediction_service.load_model(family, version)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to load model {version}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

    def unload_model(self, family: str, version: str) -> str:
        try:
            return self.prediction_service.unload_model(version)
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
            total, records = self.prediction_service.get_models(
                page=page,
                page_size=page_size
            )

            loaded_versions = self.prediction_service.get_loaded_versions()
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

    def create_dataset(self, family: str, site_name: str, payload: Optional[Dict[str, Any]] = Body(default=None)) -> str:
        try:
            return self.training_service.create_dataset(family, site_name, payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to create dataset: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create dataset: {str(e)}")

    def start_training(self, family: str, payload: Optional[Dict[str, Any]] = Body(default=None)) -> str:
        try:
            return self.training_service.start_training(family, payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to start training: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to start training: {str(e)}")

    def stop_training(self, family: str, task_id: str) -> str:
        try:
            return self.training_service.stop_training(family, task_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to stop training {family} {task_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to stop training: {str(e)}")
