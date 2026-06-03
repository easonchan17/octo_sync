from datetime import timedelta
from typing import Dict, Any, Optional
from core.types.enums import SiteName
from core.services.base_service import BaseService
from core.services.league import get_league_service
from core.store.postgres.daos.fotmob import MatchDao
from core.store.postgres.daos.oddsportal import OddsDao
from core.config.env_manager import get_env_manager
from core.tasks.sync.fotmob.utils import encode_id


class MatchService(BaseService):
    H2H_LOOKBACK = timedelta(days=365 * 3)
    FORM_LIMIT = 5

    def __init__(self):
        super().__init__()
        self.match_dao = MatchDao()
        self.odds_dao = OddsDao()
        self.league_service = get_league_service()
        self.env_manager = get_env_manager()

    def enrich_standing_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        team_id = entry.get('id')
        return {**entry, 'team_code': encode_id(team_id, self.env_manager.TEAM_CODE_SALT) if team_id else None}

    def get_latest_prediction(self, match_code: str) -> Optional[Dict[str, Any]]:
        prediction = self.match_dao.get_latest_prediction(match_code)
        if prediction is None:
            return None

        return {
            "model_version": prediction.model_version,
            "probabilities": {"0": prediction.home_prob, "1": prediction.draw_prob, "2": prediction.away_prob},
            "prediction":    prediction.prediction,
        }

    def get_match_detail(self, match_code: str) -> Dict[str, Any]:
        data = self.match_dao.get_match_detail(match_code)

        match_id = data['match_id']
        home_id = data['home_id']
        away_id = data['away_id']
        kickoff_time = data['kickoff_time']

        match_content = data['match_json_body'].get('content') or {}
        standings_tables = (data.get('standings_json_body') or {}).get('table')
        standings_table = standings_tables[0].get('data', {}).get('table') if standings_tables else None

        canonical_league = self.league_service.get_canonical_league(SiteName.FOTMOB.value, data['league_id'])

        data['league_id'] = canonical_league.id if canonical_league is not None else None
        data['league_name'] = canonical_league.name if canonical_league is not None else None

        data['detail'] = {
            'weather':   match_content.get('weather'),
            'momentum':  ((match_content.get('momentum') or {}).get('main') or {}).get('data'),
            'events':    ((match_content.get('matchFacts') or {}).get('events') or {}).get('events'),
            'lineup':    {
                "home": self.match_dao.get_match_lineup(match_id, home_id),
                "away": self.match_dao.get_match_lineup(match_id, away_id),
            },
            'stats':     self.match_dao.get_match_stats(match_id),
            'shot_map':  self.match_dao.get_match_shot_map(match_id),
            'form':      {
                "home": self.match_dao.get_team_form(home_id, kickoff_time, self.FORM_LIMIT),
                "away": self.match_dao.get_team_form(away_id, kickoff_time, self.FORM_LIMIT),
            },
            'h2h':       self.match_dao.get_team_h2h(home_id, away_id, kickoff_time - self.H2H_LOOKBACK, kickoff_time),
            'odds':      self.odds_dao.get_match_odds_detail(match_id),
            'prediction': self.get_latest_prediction(match_code),
            'standings': {
                key: [self.enrich_standing_entry(entry) for entry in entries]
                for key, entries in standings_table.items()
                if isinstance(entries, list)
            } if isinstance(standings_table, dict) else None,
        }
        return data
