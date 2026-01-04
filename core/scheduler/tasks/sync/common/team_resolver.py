import json
from thefuzz import fuzz
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from core.logger.logger_manager import LoggerManager
from core.store.postgres.postgresql_manager import PostgreSQLManager

class TeamResolver:
    SIMILARITY_THRESHOLD = 80

    TEAM_ALIAS = {
        'Man United': 'Manchester United',
        'Man City': 'Manchester City'
    }

    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.db = PostgreSQLManager.get_instance()

    def resolve(self, source_matches: List[Dict], target_matches: List[Any], with_target: Optional[bool] = False) -> None:
        if not source_matches:
            raise ValueError("No source matches")

        if not target_matches:
            raise ValueError("No target matches")

        target_index = {}
        for target_match in target_matches:
            target_match.kickoff_time = target_match.kickoff_time.astimezone(timezone.utc)
            target_index.setdefault(target_match.kickoff_time, []).append(target_match)

        for source_match in source_matches:
            kickoff_time = source_match['kickoff_time']
            if isinstance(kickoff_time, str):
                kickoff_time = datetime.fromisoformat(kickoff_time)

            candidate_matches = target_index.get(kickoff_time, [])
            if not candidate_matches:
                pretty_source = json.dumps(source_match, indent=4, ensure_ascii=False, default=str)
                self.logger.warning(f"No candidate matches found for source match:\n{pretty_source}")
                raise ValueError("No candidate matches found for source match")

            best_match = self._find_best_match(source_match, candidate_matches)

            if not best_match:
                pretty_source = json.dumps(source_match, indent=4, ensure_ascii=False, default=str)
                self.logger.warning(f"No best match found for source match:\n{pretty_source}")
                pretty_candidates = json.dumps(candidate_matches, indent=4, ensure_ascii=False, default=str)
                self.logger.warning(f"Candidate matches:\n{pretty_candidates}")
                raise ValueError("No best match found for source match")

            source_match['home_team'] = best_match.home_team
            source_match['away_team'] = best_match.away_team

            if with_target:
                source_match['target'] = best_match


    def _find_best_match(self, source_match: Dict, candidate_matches: List[Any]) -> Optional[Any]:
        max_score = 0
        best_candidate = None

        for candidate_match in candidate_matches:
            score = self._calc_similarity(source_match, candidate_match)
            if score >= self.SIMILARITY_THRESHOLD and score > max_score:
                max_score = score
                best_candidate = candidate_match

        return best_candidate

    def _calc_similarity(self, source_match: Dict, target_match: Any) -> int:
        source_home_team = self.TEAM_ALIAS.get(source_match['home_team'], source_match['home_team'])
        source_away_team = self.TEAM_ALIAS.get(source_match['away_team'], source_match['away_team'])
        target_home_team = target_match.home_team
        target_away_team = target_match.away_team

        if source_home_team == target_home_team and source_away_team == target_away_team:
            return 100

        home_similarity = fuzz.token_set_ratio(source_home_team, target_home_team)
        away_similarity = fuzz.token_set_ratio(source_away_team, target_away_team)

        return int((home_similarity + away_similarity) / 2)
