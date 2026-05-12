from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from core.types.enums import MatchStatus
from core.store.postgres.models.fotmob.fixture import Fixture
from core.store.postgres.models.fotmob.match import FormCacheBuildLog
from ..base_dao import BaseDao


class FormCacheDao(BaseDao):
    def get_latest_built_at(self) -> Optional[datetime]:
        with self.db.get_session() as session:
            return session.query(func.max(FormCacheBuildLog.built_at)).scalar()

    def count_updated_since(self, last_check_time: datetime, min_kickoff_time: datetime) -> int:
        with self.db.get_session() as session:
            return session.query(func.count()).select_from(Fixture).filter(
                Fixture.kickoff_time >= min_kickoff_time,
                Fixture.match_status.in_(MatchStatus.natural_finals()),
                Fixture.updated_at > last_check_time
            ).scalar() or 0

    def add_build_log(self, checkpoint: datetime, match_count: int) -> None:
        with self.db.get_session() as session:
            session.execute(
                insert(FormCacheBuildLog).values(
                    built_at=datetime.now(timezone.utc),
                    checkpoint=checkpoint,
                    match_count=match_count
                )
            )
