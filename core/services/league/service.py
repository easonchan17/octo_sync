from core.services.league.schemas import SystemLeagueData
import zlib
from functools import lru_cache
from dataclasses import dataclass
from core.types.enums import LeaguePriority
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload, Session
from core.services.base_service import BaseService
from typing import Dict, List, Optional, Any, Union, Set
from core.store.postgres.models import League, SiteLeague, Status
from core.store.cache.memory_cache import MemoryCache
from core.types.enums import SiteName
from .schemas import SystemLeagueData, SiteLeagueData

@dataclass(frozen=True)
class SiteMeta:
    index: int
    name: str
    scope: str

class SiteConfig:
    _META: Dict[str, SiteMeta] = {
        site_name.value: SiteMeta(
            index=i,
            name=site_name.value,
            scope=f"{site_name.value}:leagues"
        )
        for i, site_name in enumerate(SiteName)
    }

    @classmethod
    def get_scope(cls, site: str) -> str:
        return cls._META[site].scope

    @classmethod
    def get_index(cls, site: str) -> int:
        return cls._META[site].index

    @classmethod
    def get_sites(cls, excluded_sites: Optional[Set[str]] = None) -> List[str]:
        return [
            meta.name
            for meta in cls._META.values()
            if excluded_sites is None or meta.name not in excluded_sites
        ]

    @classmethod
    def get_scopes(cls, excluded_sites: Optional[Set[str]] = None) -> List[str]:
        return [
            meta.scope
            for meta in cls._META.values()
            if excluded_sites is None or meta.name not in excluded_sites
        ]

class OfficialLoader:
    def _build(self, league: League) -> SystemLeagueData:
        return SystemLeagueData(
            id=league.id,
            name=league.name,
            priority=league.priority,
            site_leagues={
                site_league.site_name: SiteLeagueData(
                    site_name=site_league.site_name,
                    league_id=site_league.league_id,
                    league_name=site_league.league_name,
                    ref_league_id=site_league.ref_league_id,
                    extra_data=dict(site_league.extra_data or {})
                )
                for site_league in (league.site_leagues or [])
            },
        )

    def get_all(self, session: Session) -> List[SystemLeagueData]:
        return [
            self._build(league)
            for league in (
                session.query(League)
                .options(selectinload(League.site_leagues))
                .filter(League.status == Status.ACTIVE.value)
                .all()
            )
        ]

class OrphanLoader:
    def _build(self, league: SiteLeague) -> SystemLeagueData:
        high_bits = SiteConfig.get_index(league.site_name) << 32
        low_bits = zlib.crc32(league.league_id.encode('utf-8')) & 0xFFFFFFFF
        id = high_bits | low_bits

        return SystemLeagueData(
            id=id,
            name=league.league_name,
            priority=LeaguePriority.LEVEL_BASIC.value,
            site_leagues={
                league.site_name: SiteLeagueData(
                    site_name=league.site_name,
                    league_id=league.league_id,
                    league_name=league.league_name,
                    ref_league_id=id,
                    extra_data=dict(league.extra_data or {}),
                )
            },
        )

    def get_all(self, session: Session) -> List[SystemLeagueData]:
        return [
            self._build(site_league)
            for site_league in (
                session.query(SiteLeague)
                .filter(SiteLeague.ref_league_id.is_(None))
                .all()
            )
        ]

    def add(self, session: Session, site_name: str, league_id: str, league_name: str) -> SystemLeagueData:
        insert_stmt = insert(SiteLeague).values(
            site_name=site_name,
            league_id=league_id,
            league_name=league_name
        )
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[SiteLeague.site_name, SiteLeague.league_id],
            set_={'league_name': league_name}
        ).returning(SiteLeague)

        result = session.execute(upsert_stmt)
        site_league = result.scalar_one()

        return self._build(site_league)


class LeagueCache:
    def __init__(self) -> None:
        self._cache = MemoryCache()

    def get(self, site_name: str, league_id: Union[str, int]) -> Optional[Any]:
        return self._cache.get_item(
            SiteConfig.get_scope(site_name), str(league_id)
        )

    def get_all(self, site_name: str) -> Optional[Dict[str, SystemLeagueData]]:
        return self._cache.get_scope(SiteConfig.get_scope(site_name))

    def set(self, system_league: SystemLeagueData) -> None:
        for site_league in system_league.site_leagues.values():
            self._cache.set_item(
                SiteConfig.get_scope(site_league.site_name),
                site_league.league_id,
                system_league.id
            )

        self._cache.set_item(
            SiteConfig.get_scope(SiteName.SYSTEM.value),
            str(system_league.id),
            system_league
        )

    def delete(self, site_names: List[str]) -> None:
        for site_name in site_names:
            self._cache.delete_scope(SiteConfig.get_scope(site_name))


class LeagueService(BaseService):
    def __init__(self) -> None:
        super().__init__()
        self._official_loader = OfficialLoader()
        self._orphan_loader = OrphanLoader()
        self._cache = None

    def reload(self) -> None:
        with self.db.get_session() as session:
            officials = self._official_loader.get_all(session)
            orphans = self._orphan_loader.get_all(session)

            new_cache = LeagueCache()
            for league in officials + orphans:
                new_cache.set(league)

            self._cache = new_cache

    def get(self, id: int) -> Optional[SystemLeagueData]:
        if self._cache is None:
            return None

        return self._cache.get(SiteName.SYSTEM.value, str(id))

    def resolve(self, site_name: str, league_id: str, league_name: str) -> Optional[SystemLeagueData]:
        if self._cache is None:
            return None

        ref_league_id = self._cache.get(site_name, str(league_id))
        if ref_league_id is not None:
            return self.get(ref_league_id)

        with self.db.get_session() as session:
            orphan = self._orphan_loader.add(session, site_name, league_id, league_name)
            self._cache.set(orphan)
            return orphan

    def get_leagues(self, min_priority: Optional[int] = None) -> List[SystemLeagueData]:
        if self._cache is None:
            return []

        leagues = self._cache.get_all(SiteName.SYSTEM.value)
        if not leagues:
            return []

        if min_priority is not None:
            items = (league for league in leagues.values() if league.priority >= min_priority)
        else:
            items = leagues.values()

        return sorted(items, key=lambda item: (-item.priority, item.name))

    def get_site_leagues(self, site_name: str, min_priority: Optional[int] = None) -> List[SiteLeagueData]:
        return [
            site_league for league in self.get_leagues(min_priority=min_priority)
            if (site_league := league.site_leagues.get(site_name)) is not None
        ]


@lru_cache(maxsize=1)
def get_league_service() -> LeagueService:
    return LeagueService()

league_service = get_league_service()
