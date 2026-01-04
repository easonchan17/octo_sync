from sqlalchemy import  func
from typing import Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from core.server.services.base_service import BaseService
from core.store.postgres.models.fotmob import Fixture
from core.store.postgres.models.common import MatchStatus
from core.config.league_config import LEAGUE_METADATA
from core.server.models.api_models import FixtureStatus


FINISHED_STATUSES = [
    MatchStatus.FINISHED.value,
    MatchStatus.FINISHED_AET.value,
    MatchStatus.FINISHED_PEN.value,
    MatchStatus.FINISHED_AWARDED.value
]

UPCOMING_STATUSES = [
    MatchStatus.SCHEDULED.value,
    MatchStatus.TIMED.value,
    MatchStatus.POSTPONED.value
]

LIVE_STATUSES = [
    MatchStatus.IN_PROGRESS.value,
    MatchStatus.FIRST_HALF.value,
    MatchStatus.HALFTIME.value,
    MatchStatus.SECOND_HALF.value,
    MatchStatus.EXTRA_TIME.value,
    MatchStatus.PENALTY.value
]

class FixtureService(BaseService):
    def get_fixtures(
        self,
        status: FixtureStatus,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[int, List[Fixture]]:
        current_time = datetime.now(timezone.utc)
        today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        site = self.get_site('fotmob')

        with self.db.get_session(site.get_namespace()) as session:
            query = session.query(Fixture).filter(
                Fixture.status.op('&')(1) == 1
            )

            if status == FixtureStatus.FINISHED:
                time_start = today_start - timedelta(days=6)
                time_end = current_time
                query = query.filter(
                    Fixture.kickoff_time >= time_start,
                    Fixture.kickoff_time <= time_end,
                    Fixture.match_status.in_(FINISHED_STATUSES)
                ).order_by(Fixture.kickoff_time.desc())

            elif status == FixtureStatus.UPCOMING:
                time_start = current_time
                time_end = today_start + timedelta(days=7)
                query = query.filter(
                    Fixture.kickoff_time >= time_start,
                    Fixture.kickoff_time < time_end,
                    Fixture.match_status.in_(UPCOMING_STATUSES)
                ).order_by(Fixture.kickoff_time.asc())

            elif status == FixtureStatus.LIVE:
                query = query.filter(
                    Fixture.match_status.in_(LIVE_STATUSES)
                ).order_by(Fixture.kickoff_time.desc())

            else:
                raise ValueError(f"Invalid status: {status}")

            total = query.count()
            offset = (page - 1) * page_size
            fixtures = query.offset(offset).limit(page_size).all()

            session.expunge_all()
            return total, fixtures