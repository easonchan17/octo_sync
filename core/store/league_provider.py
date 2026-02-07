import copy
from functools import lru_cache
from types import MappingProxyType
from core.types.enums import LeagueID
from typing import Dict, Any, Union, Optional
from core.store.postgres.models import League
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.store.postgres.models.base_model import Status
from core.store.cache.global_store import get_global_store

class LeagueProvider:
    def __init__(self):
        self.cache = get_global_store()

    def _normalize_league_id(self, league_id: Union[LeagueID, int, str]) -> LeagueID:
        if isinstance(league_id, str):
            league_id = LeagueID(int(league_id))
        elif isinstance(league_id, int):
            league_id = LeagueID(league_id)

        if not isinstance(league_id, LeagueID):
            raise ValueError(f"Invalid league ID type: {league_id}")

        return league_id

    def _fetch_raw_data(self, league_id: LeagueID) -> Optional[Dict[str, Any]]:
        with PostgreSQLManager.get_instance().get_session() as session:
            league = session.query(League).filter(
                League.id == league_id.value,
                League.status == Status.ACTIVE.value
            ).first()

            if not league:
                return None

            sites = copy.deepcopy(league.sites) if league.sites else {}
            for _, site in sites.items():
                if "name" not in site:
                    site["name"] = league.name

            return {
                "id": league.id,
                "name": league.name,
                "sites": sites
            }

    def invalidate_league(self, league_id: Union[LeagueID, int, str]) -> None:
        league_id = self._normalize_league_id(league_id)
        cache_key = f"leagues.{league_id.value}"
        self.cache.remove(cache_key)

    def get_league(self, league_id: Union[LeagueID, int, str], site_name: str) -> MappingProxyType:
        league_id = self._normalize_league_id(league_id)
        cache_key = f"leagues.{league_id.value}"

        league = self.cache.get(cache_key)
        if league is None:
            league = self._fetch_raw_data(league_id)

            if league is None:
                raise ValueError(f"League {league_id.value} not found or inactive.")

            self.cache.set(cache_key, league)

        site = league.get("sites", {}).get(site_name)
        if site is None:
            raise ValueError(f"Site {site_name} configuration not found for league {league_id.value}")

        return MappingProxyType(site)

@lru_cache(maxsize=None)
def get_league_provider() -> LeagueProvider:
    return LeagueProvider()

league_provider = get_league_provider()
