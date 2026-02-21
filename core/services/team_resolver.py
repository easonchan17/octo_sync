import json
from thefuzz import fuzz
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type
from core.services.base_service import BaseService


class TeamResolver(BaseService):
    SIMILARITY_THRESHOLD = 80

    TEAM_ALIAS = {
        "Man United": "Manchester United",
        "Man City": "Manchester City",
        "Wolves": "Wolverhampton Wanderers",
        "Nott'ham Forest": "Nottingham Forest"
    }

    def resolve(
        self,
        raw_matches: List[Dict],
        ref_site: str,
        ref_model: Type[Any],
        attach_ref: bool = False
    ) -> None:
        if not raw_matches:
            raise ValueError("No raw matches")

        raw_matches.sort(key=lambda x: x['kickoff_time'])
        start_time = raw_matches[0]['kickoff_time']

        ref_matches = self._get_matches(ref_site, ref_model, start_time)
        if not ref_matches:
            raise ValueError("No ref matches")

        ref_index = {}
        for ref_match in ref_matches:
            ref_match.kickoff_time = ref_match.kickoff_time.astimezone(timezone.utc)
            ref_index.setdefault(ref_match.kickoff_time, []).append(ref_match)

        for raw_match in raw_matches:
            kickoff_time = raw_match['kickoff_time']
            if isinstance(kickoff_time, str):
                kickoff_time = datetime.fromisoformat(kickoff_time)

            candidates = ref_index.get(kickoff_time, [])
            if not candidates:
                self.logger.warning(f"No candidate found for raw match:\n{json.dumps(raw_match, indent=4, ensure_ascii=False, default=str)}")
                continue

            best_ref = self._find_best_match(raw_match, candidates)

            if not best_ref:
                self.logger.warning(f"No best ref found for raw match:\n{json.dumps(raw_match, indent=4, ensure_ascii=False, default=str)}")
                self.logger.warning(f"Candidates:\n{json.dumps(candidates, indent=4, ensure_ascii=False, default=str)}")
                continue

            raw_match['home_team'] = best_ref.home_team
            raw_match['away_team'] = best_ref.away_team

            if attach_ref:
                raw_match['ref_obj'] = best_ref

    def _get_matches(self, site_name: str, model_class: Type[Any], start_time: datetime) -> List[Any]:
        with self.db.get_session(site_name) as session:
            matches = session.query(model_class).filter(
                model_class.kickoff_time >= start_time
            ).order_by(model_class.kickoff_time).all()

            if matches:
                session.expunge_all()

            return matches

    def _find_best_match(self, raw_match: Dict, candidates: List[Any]) -> Optional[Any]:
        max_score = 0
        best_ref = None

        for candidate in candidates:
            score = self._calc_similarity(raw_match, candidate)
            if score >= self.SIMILARITY_THRESHOLD and score > max_score:
                max_score = score
                best_ref = candidate

        return best_ref

    def _calc_similarity(self, raw_match: Dict, ref_match: Any) -> int:
        raw_home_team = self.TEAM_ALIAS.get(raw_match['home_team'], raw_match['home_team'])
        raw_away_team = self.TEAM_ALIAS.get(raw_match['away_team'], raw_match['away_team'])
        ref_home_team = ref_match.home_team
        ref_away_team = ref_match.away_team

        if raw_home_team == ref_home_team and raw_away_team == ref_away_team:
            return 100

        home_similarity = fuzz.token_set_ratio(raw_home_team, ref_home_team)
        away_similarity = fuzz.token_set_ratio(raw_away_team, ref_away_team)

        return int((home_similarity + away_similarity) / 2)
