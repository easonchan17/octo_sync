from typing import Dict, Any, Union
from core.domain.enums import LeagueID

LEAGUE_METADATA = {
    LeagueID.EPL: {
        "name": "Premier League",
        "sites": {
            "fbref": {"id": "9"},
            "fotmob": {"id": 47},
            "football-data": {
                "id": "9",
                "name": "E0",
                "timezone": "Europe/London"
            },
        }
    },
    LeagueID.LALIGA: {
        "name": "LaLiga",
        "sites": {
            "fbref": {"id": ""},
            "fotmob": {"id": ""}
        }
    }
}


def get_league_metadata(league_id: Union[LeagueID, int, str], site_name: str) -> Dict[str, Any]:
    if isinstance(league_id, str):
        league_id = LeagueID(int(league_id))
    elif isinstance(league_id, int):
        league_id = LeagueID(league_id)

    if not isinstance(league_id, LeagueID):
        raise ValueError(f"Invalid league ID: {league_id}")

    metadata = LEAGUE_METADATA.get(league_id)
    if not metadata:
        raise ValueError(f"League ID {league_id} not found")

    sites = metadata.get("sites", {})
    if site_name not in sites:
        raise ValueError(f"Site '{site_name}' not found for league {league_id}")

    site_config = sites[site_name].copy()
    if "name" not in site_config:
        site_config["name"] = metadata.get("name")

    return site_config
