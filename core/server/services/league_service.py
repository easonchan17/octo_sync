from typing import List
from core.store.postgres.models import League
from core.server.services.base_service import BaseService
from core.store.postgres.models.base_model import Status

class LeagueService(BaseService):
    def get_leagues(self) -> List[League]:
        with self.db.get_session() as session:
            leagues = session.query(League).filter(
                League.status == Status.ACTIVE.value
            ).order_by(
                League.is_popular.desc(),
                League.priority.desc(),
                League.name.asc()
            ).all()

            session.expunge_all()
            return leagues
