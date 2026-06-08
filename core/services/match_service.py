from datetime import timedelta
from typing import Dict, Any, Optional
from core.types.enums import SiteName, SHARP_BOOKMAKER_NAMES
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

    def resolve_standings(self, standings_json: dict, group_name: str) -> Optional[Dict[str, Any]]:
        standings_tables = standings_json.get('table')
        if not standings_tables:
            return None

        if group_name:
            tables      = standings_tables[0].get('data', {}).get('tables') or []
            group_label = f"Grp. {group_name}"
            matched     = next((t for t in tables if t.get('leagueName') == group_label), None)
            standings_table = matched.get('table') if matched else None
        else:
            standings_table = standings_tables[0].get('data', {}).get('table')

        if not isinstance(standings_table, dict):
            return None

        return {
            key: [self.enrich_standing_entry(entry) for entry in entries]
            for key, entries in standings_table.items()
            if isinstance(entries, list)
        }

    def enrich_knockout_rounds(self, rounds: list) -> list:
        salt = self.env_manager.TEAM_CODE_SALT
        return [
            {
                **round_data,
                'matchups': [
                    {
                        **matchup,
                        'home_code':   encode_id(matchup['homeTeamId'], salt),
                        'away_code':   encode_id(matchup['awayTeamId'], salt),
                        'winner_code': encode_id(matchup['winner'], salt) if matchup.get('winner') else None,
                    }
                    for matchup in round_data.get('matchups', [])
                ],
            }
            for round_data in rounds
        ]

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

        match_content = (data['match_json_body'] or {}).get('content') or {}

        standings_json= data.get('standings_json_body') or {}

        knockout_rounds = ((((standings_json.get('playoff') or {}).get('draw') or {}).get('knockout') or {})).get('rounds')
        knockout     = self.enrich_knockout_rounds(knockout_rounds) if knockout_rounds else None

        standings    = self.resolve_standings(standings_json, data.get('group_name'))

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
            'odds':      self.odds_dao.get_match_odds_detail(match_id, list(SHARP_BOOKMAKER_NAMES.keys())),
            'prediction': self.get_latest_prediction(match_code),
            'knockout':  knockout,
            'standings': standings,
        }
        return data
