from functools import lru_cache
from typing import Dict, Any, Union, Optional, Tuple
from core.domain.enums import LeagueID, SiteName

LEAGUE_CONFIG = {
    LeagueID.EPL: {
        "name": "Premier League",
        "sites": {
            SiteName.FBREF.value: {
                "id": "9"
            },
            SiteName.FOTMOB.value: {
                "id": 47,
                "name": "premier-league"
            },
            SiteName.PINNACLE.value: {
                "id": 1980
            },
            SiteName.FOOTBALL_DATA.value: {
                "id": "9",
                "name": "E0",
                "timezone": "Europe/London"
            },
        }
    },
    LeagueID.LALIGA: {
        "name": "LaLiga",
        "sites": {
        }
    }
}

class LeagueRegistry:
    def get_league_config(self, league_id: Union[LeagueID, int, str], site_name: str) -> Dict[str, Any]:
        if isinstance(league_id, str):
            league_id = LeagueID(int(league_id))
        elif isinstance(league_id, int):
            league_id = LeagueID(league_id)

        if not isinstance(league_id, LeagueID):
            raise ValueError(f"Invalid league ID type: {league_id}")

        configs = LEAGUE_CONFIG.get(league_id)
        if not configs:
            raise ValueError(f"League config not found for {league_id}")

        sites = configs.get("sites", {})
        if site_name not in sites:
            raise ValueError(f"Site {site_name} not found for {league_id}")

        config = sites[site_name].copy()

        if "name" not in config:
            config["name"] = configs.get("name")

        return config

@lru_cache()
def get_league_registry() -> LeagueRegistry:
    return LeagueRegistry()

league_registry = get_league_registry()
