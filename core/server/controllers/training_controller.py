from fastapi import HTTPException, Body
from typing import Optional, Dict, Any
from core.server.services.training_service import TrainingService
from core.server.controllers.base_controller import BaseController

class TrainingController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.training_service = TrainingService()
        self.router.post("/models/{model}/sites/{site_name}/samples", response_model=str)(self.create_samples)
        self.router.post("/models/{model}/trainings", response_model=str)(self.start_training)
        self.router.delete("/models/{model}/trainings/{task_id}", response_model=str)(self.stop_training)

    def create_samples(self, model: str, site_name: str, payload: Optional[Dict[str, Any]] = Body(default=None)) -> str:
        try:
            return self.training_service.create_samples(model, site_name, payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to generate samples: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process features: {str(e)}")

    def start_training(self, model: str, payload: Optional[Dict[str, Any]] = Body(default=None)) -> str:
        try:
            return self.training_service.start_training(model, payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to start training: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to start training: {str(e)}")

    def stop_training(self, model: str, task_id: str) -> str:
        try:
            return self.training_service.stop_training(model, task_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to stop training {model} {task_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to stop training: {str(e)}")