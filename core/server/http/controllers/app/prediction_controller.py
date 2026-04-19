from fastapi import HTTPException
from core.server.http.schemas.api_models import PredictionResponse
from core.server.http.controllers.base_controller import BaseController
from core.services.prediction_service import PredictionService

class PredictionController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.prediction_service = PredictionService()
        self.router.get("/v1/fixtures/{fixture_id}/prediction", response_model=PredictionResponse)(self.predict)

    def predict(self, fixture_id: int) -> PredictionResponse:
        try:
            result = self.prediction_service.predict(fixture_id)
            return PredictionResponse(**result)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to make prediction: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to make prediction: {str(e)}")
