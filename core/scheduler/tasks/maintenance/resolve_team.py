from thefuzz import fuzz
from core.store.postgres.models import Site
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
from core.scheduler.tasks.base_task import BaseTask
from core.scheduler.synchronizers.common.team_mapping_synchronizer import TeamMappingSynchronizer

class ResolveTeam(BaseTask):
    SIMILARITY_THRESHOLD = 80
    TARGET_SITE_NAME = "fotmob"

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = TeamMappingSynchronizer()
        self.target_site = self.synchronizer.get_site(self.TARGET_SITE_NAME)

    def execute(self, *args, **kwargs) -> None:
        source_league_id = self.payload.get('source_league_id')
        target_league_id = self.payload.get('target_league_id')

        if not source_league_id or not target_league_id:
            raise ValueError(f"Missing required params: {self.payload}")

        try:
            min_kickoff_time = datetime.now(timezone.utc) - timedelta(days=1)

            source_matches = self.synchronizer.get_matches(
                self.site,
                source_league_id,
                min_kickoff_time
            )

            target_matches = self.synchronizer.get_matches(
                self.target_site,
                target_league_id,
                min_kickoff_time
            )

            matched_records = self._match_teams(
                source_matches,
                target_matches
            )
            self.synchronizer.sync(matched_records)

        except Exception as e:
            self.logger.error(f"ResolveTeam failed: {e}", exc_info=True)

    def _match_teams(self, sources: List[Any], targets: List[Any]) -> List[Dict]:
        if not sources or not targets:
            return []

        target_index = {}
        for target in targets:
            target_index.setdefault(target.kickoff_time, []).append(target)

        team_mappings = set()
        for source in sources:
            max_score = 0
            best_candidate = None

            candidates = target_index.get(source.kickoff_time, [])
            for candidate in candidates:
                score = self._calc_similarity(source, candidate)
                if score < self.SIMILARITY_THRESHOLD:
                    continue

                if score > max_score:
                    max_score = score
                    best_candidate = candidate

            if best_candidate is None:
                continue

            team_mappings.add((source.home_team, best_candidate.home_team, best_candidate.home_id))
            team_mappings.add((source.away_team, best_candidate.away_team, best_candidate.away_id))

        return [
            {
                'source_site': self.site.id,
                'source_team': source_team,
                'target_team': target_team,
                'target_team_id': target_team_id
            }
            for source_team, target_team, target_team_id in team_mappings
        ]

    def _calc_similarity(self, source: Any, target: Any) -> int:
        if source.home_team == target.home_team and source.away_team == target.away_team:
            return 100

        home_similarity = fuzz.token_set_ratio(source.home_team, target.home_team)
        away_similarity = fuzz.token_set_ratio(source.away_team, target.away_team)

        return int((home_similarity + away_similarity) / 2)
