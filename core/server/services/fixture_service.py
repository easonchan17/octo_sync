from typing import List
from datetime import datetime
from core.server.services.base_service import BaseService
from core.store.postgres.models.fotmob import Fixture
from core.types.enums import SiteName

class FixtureService(BaseService):
    def get_fixtures(self, start_time: datetime, end_time: datetime) -> List[Fixture]:
        with self.db.get_session(SiteName.FOTMOB) as session:
            fixtures = session.query(Fixture).filter(
                Fixture.kickoff_time >= start_time,
                Fixture.kickoff_time < end_time
            ).order_by(Fixture.kickoff_time.asc()).all()

            session.expunge_all()
            return fixtures