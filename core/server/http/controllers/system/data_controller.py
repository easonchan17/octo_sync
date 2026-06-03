from fastapi import HTTPException
from core.server.http.controllers.base_controller import BaseController
from core.store.postgres.daos.common import RawDataDao


class DataController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.raw_data_dao = RawDataDao()

        self.router.get("/data/match/{match_code}")(self.get_match_raw)
        self.router.get("/data/fixture/{match_code}")(self.get_fixture_raw)
        self.router.get("/data/odds/{match_code}")(self.get_odds_raw)

    def get_match_raw(self, match_code: str) -> dict:
        raw = self.raw_data_dao.get_match_raw_by_code(match_code)
        if raw is None:
            raise HTTPException(status_code=404, detail="raw match data not found")

        return raw

    def get_fixture_raw(self, match_code: str) -> dict:
        raw = self.raw_data_dao.get_fixture_raw_by_code(match_code)
        if raw is None:
            raise HTTPException(status_code=404, detail="raw fixture data not found")

        return raw

    def get_odds_raw(self, match_code: str) -> list:
        raw = self.raw_data_dao.get_odds_raw_by_match_code(match_code)
        if raw is None:
            raise HTTPException(status_code=404, detail="raw odds data not found")

        return raw
