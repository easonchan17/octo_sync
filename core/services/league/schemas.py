from typing import Dict, Any
from dataclasses import dataclass, field
from core.types.enums import LeaguePriority

@dataclass(frozen=True)
class SiteLeagueData:
    site_name: str
    league_id: str
    league_name: str
    ref_league_id: int
    extra_data: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class SystemLeagueData:
    id: int
    name: str
    priority: int
    site_leagues: Dict[str, SiteLeagueData] = field(default_factory=dict)

    @property
    def is_major(self) -> bool:
        return self.priority >= LeaguePriority.LEVEL_MAJOR.value