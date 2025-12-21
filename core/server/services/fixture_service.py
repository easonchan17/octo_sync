from typing import Optional, List, Tuple
from datetime import datetime
from core.server.services.base_service import BaseService
from core.store.postgres.models.fotmob import Fixture


class FixtureService(BaseService):
    def __init__(self):
        super().__init__()

    def get_fixtures(
        self,
        league_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        match_status: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[int, List[Fixture]]:
        with self.db.get_session('fotmob') as session:
            query = session.query(Fixture)

            if league_id:
                query = query.filter(Fixture.league_id == league_id)
            if start_date:
                query = query.filter(Fixture.kickoff_time >= start_date)
            if end_date:
                query = query.filter(Fixture.kickoff_time <= end_date)
            if match_status is not None:
                query = query.filter(Fixture.match_status == match_status)

            total = query.count()
            items = query.order_by(Fixture.kickoff_time.desc()).offset(offset).limit(limit).all()

            return total, [self._detach(f) for f in items]

    def get_fixture(self, match_id: int) -> Optional[Fixture]:
        with self.db.get_session('fotmob') as session:
            fixture = session.query(Fixture).filter(Fixture.match_id == match_id).first()
            if not fixture:
                return None
            return self._detach(fixture)

    def _detach(self, f: Fixture) -> Fixture:
        return Fixture(
            id=f.id,
            match_id=f.match_id,
            league_name=f.league_name,
            league_id=f.league_id,
            kickoff_time=f.kickoff_time,
            round=f.round,
            home_team=f.home_team,
            home_id=f.home_id,
            away_team=f.away_team,
            away_id=f.away_id,
            home_score=f.home_score,
            away_score=f.away_score,
            home_xg=f.home_xg,
            away_xg=f.away_xg,
            match_status=f.match_status,
            status=f.status,
            create_at=f.create_at,
            update_at=f.update_at
        )
