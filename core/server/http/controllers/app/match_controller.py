from typing import Any, Dict
from fastapi import HTTPException
from core.services.match_service import MatchService
from core.services.model_service import ModelService
from core.server.http.controllers.base_controller import BaseController
from core.server.http.schemas.api_models import MatchDetailResponse, PredictionResponse

class MatchController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.match_service = MatchService()
        self.model_service = ModelService()
        self.router.get("/v1/matches/{match_code}", response_model=MatchDetailResponse)(self.get_detail)
        self.router.get("/v1/matches/{match_code}/prediction", response_model=PredictionResponse)(self.predict)

    def get_detail(self, match_code: str) -> MatchDetailResponse:
        try:
            return MatchDetailResponse.model_validate(self.match_service.get_match_detail(match_code))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to get match detail {match_code}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get match detail: {str(e)}")

    def predict(self, match_code: str) -> PredictionResponse:
        try:
            result = self.model_service.predict(match_code)
            return PredictionResponse(**result, match_code=match_code)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to make prediction for match {match_code}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to make prediction: {str(e)}")
