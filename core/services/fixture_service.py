from datetime import datetime
from typing import List, Dict, Any
from core.services.league import league_service
from core.services.base_service import BaseService
from core.store.postgres.daos.fotmob import ActiveFixtureDao
from core.types.enums import SiteName

class FixtureService(BaseService):
    def __init__(self):
        super().__init__()
        self.fixture_dao = ActiveFixtureDao()

    def get_grouped_fixtures(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        leagues = {
            int(league.site_leagues[SiteName.FOTMOB.value].league_id): league
            for league in league_service.get_leagues()
            if SiteName.FOTMOB.value in league.site_leagues
        }
        if not leagues:
            return []

        fixtures = self.fixture_dao.get_by_time_range(
            start_time, end_time, list(leagues.keys())
        )
        if not fixtures:
            return []

        grouped_fixtures = {}
        for fixture in fixtures:
            league_id = fixture.league_id

            if league_id not in grouped_fixtures:
                league = leagues[league_id]
                grouped_fixtures[league_id] = {
                    "league_id": league.id,
                    "league_name": league.name,
                    "priority": league.priority,
                    "fixtures": []
                }

            grouped_fixtures[league_id]["fixtures"].append(fixture)

        return sorted(grouped_fixtures.values(), key=lambda x: (-x["priority"], x["league_id"]))