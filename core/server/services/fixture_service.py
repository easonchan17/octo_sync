from sqlalchemy import  func
from typing import Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from core.server.services.base_service import BaseService
from core.store.postgres.models.fotmob import Fixture
from core.store.postgres.models.common import MatchStatus
from core.config.league_config import LEAGUE_METADATA


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

STATUS_CODE_MAP = {
    MatchStatus.SCHEDULED.value: "NS",
    MatchStatus.TIMED.value: "NS",
    MatchStatus.IN_PROGRESS.value: "Live",
    MatchStatus.FIRST_HALF.value: "1H",
    MatchStatus.HALFTIME.value: "HT",
    MatchStatus.SECOND_HALF.value: "2H",
    MatchStatus.EXTRA_TIME.value: "ET",
    MatchStatus.PENALTY.value: "P",
    MatchStatus.FINISHED.value: "FT",
    MatchStatus.FINISHED_AET.value: "AET",
    MatchStatus.FINISHED_PEN.value: "PEN",
    MatchStatus.FINISHED_AWARDED.value: "AWD",
    MatchStatus.POSTPONED.value: "POST",
    MatchStatus.CANCELLED.value: "CAN"
}


def get_status_string(status_code: int) -> str:
    return STATUS_CODE_MAP.get(status_code, str(status_code))


class FixtureService(BaseService):
    def get_fixture(self, match_id: int) -> Optional[Fixture]:
        with self.db.get_session('fotmob') as session:
            fixture = session.query(Fixture).filter(Fixture.match_id == match_id).first()
            if not fixture:
                return None
            return self._detach(fixture)

    def get_fixtures(
        self,
        status: str,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[int, List[Fixture]]:
        current_time = datetime.now(timezone.utc)
        today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

        with self.db.get_session('fotmob') as session:
            query = session.query(Fixture).filter(
                Fixture.status.op('&')(1) == 1
            )

            if status == 'finished':
                time_start = today_start - timedelta(days=6)
                time_end = current_time
                query = query.filter(
                    Fixture.kickoff_time >= time_start,
                    Fixture.kickoff_time <= time_end,
                    Fixture.match_status.in_(FINISHED_STATUSES)
                ).order_by(Fixture.kickoff_time.desc())

            elif status == 'upcoming':
                time_start = current_time
                time_end = today_start + timedelta(days=7)
                query = query.filter(
                    Fixture.kickoff_time >= time_start,
                    Fixture.kickoff_time < time_end,
                    Fixture.match_status.in_(UPCOMING_STATUSES)
                ).order_by(Fixture.kickoff_time.asc())

            elif status == 'live':
                query = query.filter(
                    Fixture.match_status.in_(LIVE_STATUSES)
                ).order_by(Fixture.kickoff_time.desc())

            else:
                raise ValueError(f"Invalid status: {status}")

            total = query.count()
            offset = (page - 1) * per_page
            fixtures = query.offset(offset).limit(per_page).all()

            return total, fixtures

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
            created_at=f.created_at,
            updated_at=f.updated_at
        )
