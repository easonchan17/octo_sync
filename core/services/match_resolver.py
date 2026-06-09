import bisect
from thefuzz import fuzz
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from core.services.base_service import BaseService

@dataclass
class MatchItem:
    match_key: Union[int, str]
    kickoff_time: datetime
    home_team: str
    away_team: str

    def __str__(self) -> str:
        return f"[M:{self.match_key}] [{self.kickoff_time}] {self.home_team} vs {self.away_team}"

class MatchResolver(BaseService):
    TEAM_ALIASES = {
        # Premier League
        "bournemouth": "afc bournemouth",
        "leeds": "leeds united",
        "manchester utd": "manchester united",
        "tottenham": "tottenham hotspur",
        "leicester": "leicester city",
        "west brom": "west bromwich albion",
        "brighton": "brighton & hove albion",
        "sheffield utd": "sheffield united",
        "wolves": "wolverhampton wanderers",
        "ipswich": "ipswich town",
        "newcastle": "newcastle united",
        "luton": "luton town",
        "west ham": "west ham united",
        "nottingham": "nottingham forest",
        "norwich": "norwich city",

        # La Liga
        "alaves": "deportivo alaves",
        "oviedo": "real oviedo",
        "betis": "real betis",
        "huesca": "sd huesca",
        "valladolid": "real valladolid",
        "ath bilbao": "athletic club",
        "granada cf": "granada",
        "cadiz cf": "cadiz",
        "atl. madrid": "atletico madrid",

        # Serie A
        "verona": "hellas verona",
        "as roma": "roma",
        "ac milan": "milan",

        # Bundesliga
        "heidenheim": "fc heidenheim",
        "stuttgart": "vfb stuttgart",
        "dortmund": "borussia dortmund",
        "fc koln": "1. fc köln",
        "dusseldorf": "fortuna düsseldorf",
        "hertha berlin": "hertha bsc",
        "greuther furth": "greuther fürth",
        "mainz": "mainz 05",
        "b. monchengladbach": "borussia mönchengladbach",
        "bayern munich": "bayern münchen",
        "schalke": "schalke 04",

        # Ligue 1
        "psg": "paris saint-germain",
        "st etienne": "saint-etienne",
        "clermont": "clermont foot",

        # National
        "czech republic": "czech"
    }

    def __init__(self, kickoff_tolerance: timedelta, similarity_threshold: int) -> None:
        super().__init__()
        self.kickoff_tolerance = kickoff_tolerance
        self.similarity_threshold = similarity_threshold

    def resolve(self, source_matches: List[MatchItem], target_matches: List[MatchItem]) -> Dict[Union[int, str], Union[int, str]]:
        if not source_matches or not target_matches:
            raise ValueError("No source or target matches provided for resolution")

        target_index: Dict[datetime, List[MatchItem]] = {}
        for target in target_matches:
            target_index.setdefault(target.kickoff_time, []).append(target)

        sorted_keys = sorted(target_index.keys())

        def get_candidates(kickoff_time: datetime) -> List[MatchItem]:
            lo = bisect.bisect_left(sorted_keys, kickoff_time - self.kickoff_tolerance)
            hi = bisect.bisect_right(sorted_keys, kickoff_time + self.kickoff_tolerance)
            return [target for kt in sorted_keys[lo:hi] for target in target_index[kt]]

        seen_targets = set()
        mappings: Dict[Union[int, str], Union[int, str]] = {}

        for source_match in source_matches:
            candidate_matches = get_candidates(source_match.kickoff_time)
            if not candidate_matches:
                self.logger.warning(f"No candidates found: {source_match}")
                continue

            best_target = self._find_best_match(source_match, candidate_matches)
            if not best_target:
                continue

            if best_target.match_key in seen_targets:
                self.logger.warning(f"Duplicate target match_key={best_target.match_key}, skipping source match_key={source_match.match_key}")
                continue

            mappings[source_match.match_key] = best_target.match_key
            seen_targets.add(best_target.match_key)

        return mappings

    def _find_best_match(self, source: MatchItem, target_matches: List[MatchItem]) -> Optional[MatchItem]:
        if not target_matches:
            return None

        best_score, best_target = max(
            ((self._calc_similarity(source, target), target) for target in target_matches),
            key=lambda item: item[0]
        )

        if best_score < self.similarity_threshold:
            if best_score > 0:
                self.logger.warning(f"Low similarity: score={best_score}, source: {source}, target: {best_target}")
            return None

        return best_target

    def _normalize_name(self, name: str) -> str:
        clean_name = name.lower().strip()
        return self.TEAM_ALIASES.get(clean_name, clean_name)

    def _calc_similarity(self, source: MatchItem, target: MatchItem) -> int:
        src_home = self._normalize_name(source.home_team)
        src_away = self._normalize_name(source.away_team)
        tgt_home = self._normalize_name(target.home_team)
        tgt_away = self._normalize_name(target.away_team)

        if src_home == tgt_home or src_away == tgt_away:
            return 100

        home_score = max(fuzz.token_set_ratio(src_home, tgt_home), self._acronym_score(src_home, tgt_home))
        away_score = max(fuzz.token_set_ratio(src_away, tgt_away), self._acronym_score(src_away, tgt_away))

        if home_score < self.similarity_threshold or away_score < self.similarity_threshold:
            return 0

        return (home_score + away_score) // 2

    def _acronym_score(self, name_a: str, name_b: str) -> int:
        if len(name_a) == len(name_b):
            return 0

        short, long = (name_a, name_b) if len(name_a) < len(name_b) else (name_b, name_a)

        acronym = short.replace('.', '').replace('-', '').strip().upper()
        initials = ''.join(word[0] for word in long.replace('-', ' ').split() if word).upper()

        return 100 if acronym == initials else 0
