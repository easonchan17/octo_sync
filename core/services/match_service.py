from typing import Dict, Any
from core.types.enums import SiteName
from core.services.base_service import BaseService
from core.services.league import get_league_service
from core.store.postgres.daos.fotmob import MatchDao


class MatchService(BaseService):
    def __init__(self):
        super().__init__()
        self.match_dao = MatchDao()
        self.league_service = get_league_service()

    def get_match_detail(self, match_code: str) -> Dict[str, Any]:
        data = self.match_dao.get_match_detail(match_code)
        canonical_league = self.league_service.get_canonical_league(SiteName.FOTMOB.value, data['league_id'])
        data['league_id'] = canonical_league.id if canonical_league is not None else None
        data['league_name'] = canonical_league.name if canonical_league is not None else None
        excluded = {'nav', 'seo', 'general', 'ongoing', 'hasPendingVAR'}
        data['json_body'] = {k: v for k, v in data['json_body'].items() if k not in excluded}
        data['json_body']['events'] = data['json_body'].pop('header', {}).get('events')
        content = data['json_body'].pop('content', {})
        for key in ('lineup', 'h2h', 'stats', 'shotmap', 'momentum', 'playerStats', 'matchFacts'):
            data['json_body'][key] = content.get(key)
        return data