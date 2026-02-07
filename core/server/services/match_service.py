from typing import List, Optional, Tuple
from core.server.services.base_service import BaseService
from core.store.postgres.models.fotmob import Fixture
from core.store.postgres.models.fotmob.match_data import MatchStat, MatchLineup, MatchPlayerStat
from core.types.enums import SiteName


class MatchService(BaseService):
    def get_match_detail(self, match_id: int) -> Tuple[Fixture, Optional[MatchStat], List[MatchLineup], List[MatchPlayerStat]]:
        with self.db.get_session(SiteName.FOTMOB.value) as session:
            fixture = session.query(Fixture).filter(
                Fixture.match_id == match_id
            ).first()

            if not fixture:
                raise ValueError("Match not found")

            match_stat = session.query(MatchStat).filter(
                MatchStat.match_id == match_id
            ).first()

            lineups = session.query(MatchLineup).filter(
                MatchLineup.match_id == match_id
            ).all()

            player_stats = session.query(MatchPlayerStat).filter(
                MatchPlayerStat.match_id == match_id
            ).all()

            session.expunge_all()
            return fixture, match_stat, lineups, player_stats
