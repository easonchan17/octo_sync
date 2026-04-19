from fastapi import HTTPException
from core.services.match_service import MatchService
from core.server.http.controllers.base_controller import BaseController
from core.server.http.schemas.api_models import (
    MatchDetailResponse,
    FixtureResponse,
    MatchStatResponse,
    MatchLineupResponse,
    MatchPlayerStatResponse,
)

class MatchController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.match_service = MatchService()
        self.router.get("/v1/matches/{match_id}", response_model=MatchDetailResponse)(self.get_match_detail)

    def get_match_detail(self, match_id: int) -> MatchDetailResponse:
        try:
            fixture, match_stat, lineups, player_stats = self.match_service.get_match_detail(match_id)
            return MatchDetailResponse(
                fixture=FixtureResponse.model_validate(fixture),
                match_stats=MatchStatResponse.model_validate(match_stat) if match_stat else None,
                lineups=[MatchLineupResponse.model_validate(row) for row in lineups],
                player_stats=[MatchPlayerStatResponse.model_validate(row) for row in player_stats],
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to get match detail {match_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get match detail: {str(e)}")
