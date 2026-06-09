from datetime import datetime
from fastapi import HTTPException
from pydantic import BaseModel
from core.server.http.controllers.base_controller import BaseController
from core.store.postgres.daos.fotmob import MatchDao


class MatchRawPayload(BaseModel):
    url: str
    data: dict


class RawDataUploadController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.match_dao = MatchDao()
        self.router.post("/raw/match/upload")(self.capture_match_raw)

    async def capture_match_raw(self, payload: MatchRawPayload) -> dict:
        general = payload.data.get("general", {})

        try:
            match_id = int(general.get("matchId"))
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="invalid matchId")

        try:
            kickoff_time = datetime.fromisoformat(general.get("matchTimeUTCDate").replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="invalid matchTimeUTCDate")

        self.match_dao.sync_raw_data({
            "source_url": payload.url,
            "match_id": match_id,
            "kickoff_time": kickoff_time,
            "json_body": payload.data
        })
        self.match_dao.mark_as_fetched(match_id, fetch_interval=None)
        return {"status": "ok", "match_id": match_id}
