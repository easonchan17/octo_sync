from typing import Dict, Any
from fastapi import HTTPException, Body
from core.server.services.inference_service import InferenceService
from core.server.controllers.base_controller import BaseController
from core.server.models.inference_models import PredictionResponse

class InferenceController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.inference_service = InferenceService()
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

    def predict(self, family: str, version: str, payload: Dict[str, Any] = Body(...)) -> PredictionResponse:
        try:
            result = self.inference_service.predict(version, payload)
            return PredictionResponse(**result)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to make prediction: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to make prediction: {str(e)}")
