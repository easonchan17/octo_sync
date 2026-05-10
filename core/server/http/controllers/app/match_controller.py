from typing import Any, Dict
from fastapi import HTTPException
from core.services.match_service import MatchService
from core.server.http.controllers.base_controller import BaseController

class MatchController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.match_service = MatchService()
        self.router.get("/v1/matches/{match_id}")(self.get_match_detail)

    def get_match_detail(self, match_id: int) -> Dict[str, Any]:
        try:
            return self.match_service.get_match_detail(match_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Failed to get match detail {match_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get match detail: {str(e)}")
