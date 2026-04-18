from typing import List
from fastapi import HTTPException
from core.services.league import league_service
from core.server.controllers.base_controller import BaseController
from core.server.schemas.api_models import LeagueResponse

class LeagueController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.router.get("/v1/leagues", response_model=List[LeagueResponse])(self.get_leagues)

    def get_leagues(self) -> List[LeagueResponse]:
        try:
            leagues = league_service.get_leagues()
            return [LeagueResponse.model_validate(league) for league in leagues]
        except Exception as e:
            self.logger.error(f"Failed to get leagues: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get leagues: {str(e)}")