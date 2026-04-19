from datetime import datetime
from typing import List, Dict, Any
from core.services.league import league_service
from core.services.base_service import BaseService
from core.store.postgres.models.fotmob import Fixture
from core.types.enums import SiteName

class FixtureService(BaseService):
    def get_fixtures(
        self,
        start_time: datetime,
        end_time: datetime,
        league_ids: List[int],
    ) -> List[Fixture]:
        with self.db.get_session() as session:
            fixtures = session.query(
                Fixture.id,
                Fixture.league_id,
                Fixture.league_name,
                Fixture.kickoff_time,
                Fixture.round,
                Fixture.home_team,
                Fixture.home_id,
                Fixture.away_team,
                Fixture.away_id,
                Fixture.home_score,
                Fixture.away_score,
                Fixture.match_status,
            ).filter(
                Fixture.kickoff_time >= start_time,
                Fixture.kickoff_time < end_time,
                Fixture.league_id.in_(league_ids)
            ).order_by(
                Fixture.league_id.asc(),
                Fixture.kickoff_time.asc()
            ).all()

            return fixtures

    def get_grouped_fixtures(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        leagues = {
            int(league.site_leagues[SiteName.FOTMOB.value].league_id): league
            for league in league_service.get_leagues()
            if SiteName.FOTMOB.value in league.site_leagues
        }
        if not leagues:
            return []

        fixtures = self.get_fixtures(start_time, end_time, list(leagues.keys()))
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