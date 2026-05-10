from typing import Any, Dict
from fastapi import HTTPException
from core.services.match_service import MatchService
from core.services.model_service import ModelService
from core.server.http.controllers.base_controller import BaseController
from core.server.http.schemas.api_models import PredictionResponse

class MatchController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.match_service = MatchService()
        self.model_service = ModelService()
        self.router.get("/v1/matches/{match_id}")(self.get_detail)
        self.router.get("/v1/matches/{match_id}/prediction", response_model=PredictionResponse)(self.predict)

    def get_detail(self, match_id: int) -> Dict[str, Any]:
        try:
            return self.match_service.get_detail(match_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to get match detail {match_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get match detail: {str(e)}")

    def predict(self, match_id: int) -> PredictionResponse:
        try:
            result = self.model_service.predict(match_id)
            return PredictionResponse(**result)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to make prediction for match {match_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to make prediction: {str(e)}")
