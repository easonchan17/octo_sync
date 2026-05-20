from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from core.types.enums import LeaguePriority

@dataclass(frozen=True)
class SiteLeagueData:
    site_name: str
    league_id: int
    league_name: str
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    ref_league_id: Optional[int] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class CanonicalLeagueData:
    id: int
    name: str
    priority: int
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    site_leagues: Dict[str, SiteLeagueData] = field(default_factory=dict)

    @property
    def is_major(self) -> bool:
        return self.priority >= LeaguePriority.LEVEL_MAJOR.value