from datetime import timedelta
from typing import Dict, Any
from core.types.enums import SiteName
from core.services.base_service import BaseService
from core.services.league import get_league_service
from core.store.postgres.daos.fotmob import MatchDao


class MatchService(BaseService):
    H2H_LOOKBACK = timedelta(days=365 * 3)
    FORM_LIMIT = 5

    def __init__(self):
        super().__init__()
        self.match_dao = MatchDao()
        self.league_service = get_league_service()

    def get_match_detail(self, match_code: str) -> Dict[str, Any]:
        data = self.match_dao.get_match_detail(match_code)

        match_id = data['match_id']
        home_id = data['home_id']
        away_id = data['away_id']
        kickoff_time = data['kickoff_time']
        content = data['json_body'].get('content') or {}
        canonical_league = self.league_service.get_canonical_league(SiteName.FOTMOB.value, data['league_id'])

        data['league_id'] = canonical_league.id if canonical_league is not None else None
        data['league_name'] = canonical_league.name if canonical_league is not None else None
        data['detail'] = {
            'weather':  content.get('weather'),
            'momentum': ((content.get('momentum') or {}).get('main') or {}).get('data'),
            'events':   ((content.get('matchFacts') or {}).get('events') or {}).get('events'),
            'lineup':   {
                "home": self.match_dao.get_match_lineup(match_id, home_id),
                "away": self.match_dao.get_match_lineup(match_id, away_id),
            },
            'stats':    self.match_dao.get_match_stats(match_id),
            'shot_map': self.match_dao.get_match_shot_map(match_id),
            'form':     {
                "home": self.match_dao.get_team_form(home_id, kickoff_time, self.FORM_LIMIT),
                "away": self.match_dao.get_team_form(away_id, kickoff_time, self.FORM_LIMIT),
            },
            'h2h':      self.match_dao.get_team_h2h(home_id, away_id, kickoff_time - self.H2H_LOOKBACK, kickoff_time),
        }
        return data
