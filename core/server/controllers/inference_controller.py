from typing import Dict, Any
from fastapi import HTTPException, Body
from core.server.services.inference_service import InferenceService
from core.server.controllers.base_controller import BaseController

class InferenceController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.inference_service = InferenceService()
        self.router.post("/inference/models/{family}/{version}", response_model=bool)(self.load_model)
        self.router.delete("/inference/models/{version}", response_model=bool)(self.unload_model)
        self.router.post("/inference/models/{version}/predict", response_model=Dict[str, Any])(self.predict)

    async def load_model(self, family: str, version: str) -> bool:
        try:
            return self.inference_service.load_model(family, version)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to load model {version}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

    async def unload_model(self, version: str) -> bool:
        try:
            return self.inference_service.unload_model(version)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to unload model {version}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to unload model: {str(e)}")

    async def predict(self, version: str, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        try:
            return self.inference_service.predict(version, payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to make prediction: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to make prediction: {str(e)}")
