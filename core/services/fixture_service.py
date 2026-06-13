from datetime import datetime
from typing import List, Dict, Any
from core.services.league import get_league_service
from core.services.base_service import BaseService
from core.store.postgres.daos.fotmob import ActiveFixtureDao
from core.store.postgres.daos.oddsportal import OddsDao
from core.types.enums import SiteName

class FixtureService(BaseService):
    def __init__(self):
        super().__init__()
        self.fixture_dao = ActiveFixtureDao()
        self.odds_dao = OddsDao()
        self.league_service = get_league_service()

    def get_league_fixtures(self, league_id: int, round: str, season: int) -> List[Any]:
        return self.fixture_dao.get_league_fixtures(league_id, round, season)

    def get_fixture_groups(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        leagues = {
            league.site_leagues[SiteName.FOTMOB.value].league_id: league
            for league in self.league_service.get_leagues()
            if SiteName.FOTMOB.value in league.site_leagues
        }
        if not leagues:
            return []

        fixtures = self.fixture_dao.get_by_time_range(
            start_time, end_time, list(leagues.keys())
        )
        if not fixtures:
            return []

        # match_ids = [f.match_id for f in fixtures if f.match_id]
        # odds_summary = self.odds_dao.get_match_odds_summary(match_ids)

        fixture_groups = {}
        for fixture in fixtures:
            league_id = fixture.league_id

            if league_id not in fixture_groups:
                league = leagues[league_id]
                fixture_groups[league_id] = {
                    "league_id": league.id,
                    "league_name": league.name,
                    "priority": league.priority,
                    "matches": []
                }

            # fixture_dict = fixture._asdict()
            # fixture_dict.update(odds_summary.get(fixture.match_id, {}))
            fixture_groups[league_id]["matches"].append(fixture)

        return sorted(fixture_groups.values(), key=lambda x: (-x["priority"], x["league_id"]))