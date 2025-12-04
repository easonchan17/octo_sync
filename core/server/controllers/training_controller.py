from fastapi import HTTPException, Body
from typing import Optional, Dict, Any
from core.server.services.training_service import TrainingService
from core.server.controllers.base_controller import BaseController

class TrainingController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.training_service = TrainingService()
        self.router.post("/training/{model}", response_model=str)(self.start_training)
        self.router.delete("/training/{model}", response_model=str)(self.stop_training)

    async def start_training(self, model: str, payload: Optional[Dict[str, Any]] = Body(default=None)) -> str:
        try:
            return await self.training_service.start_training(model, payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to start training: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to start training: {str(e)}")

    async def stop_training(self, model: str) -> str:
        try:
            return await self.training_service.stop_training(model)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to stop training {model}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to stop training: {str(e)}")