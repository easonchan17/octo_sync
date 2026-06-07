from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from core.tasks.poll_task import PollTask
from core.tasks.sync.scan_asset import EntityType
from core.store.postgres.daos.common import NameI18nDao
from core.scheduler.task_registry import TaskRegistry


class BaseNameScanner(ABC):
    LOCALE = 'en'

    def __init__(self, entity_type: EntityType) -> None:
        self.entity_type = entity_type
        self.name_i18n_dao = NameI18nDao()

    @abstractmethod
    def scan_items(self) -> Optional[Tuple[List[Dict], int]]:
        ...

    def sync_items(self, items: List[Dict]) -> None:
        self.name_i18n_dao.sync_scanned_data(items)

    def update_progress(self, max_id: int) -> None:
        self.name_i18n_dao.update_scan_progress(self.entity_type, max_id)

    def scan(self) -> int:
        result = self.scan_items()
        if result is None:
            return 0
        items, max_id = result
        if items:
            self.sync_items(items)
        self.update_progress(max_id)
        return len(items)


class TeamNameScanner(BaseNameScanner):
    def __init__(self) -> None:
        super().__init__(EntityType.TEAM)

    @abstractmethod
    def get_pending_fetch_teams(self, last_id: int) -> List[Any]:
        ...

    def scan_items(self) -> Optional[Tuple[List[Dict], int]]:
        last_id = self.name_i18n_dao.get_scan_progress(self.entity_type)
        fixtures = self.get_pending_fetch_teams(last_id)
        if not fixtures:
            return None

        teams: Dict[str, str] = {}
        for fixture in fixtures:
            if fixture.home_code not in teams:
                teams[fixture.home_code] = fixture.home_team
            if fixture.away_code not in teams:
                teams[fixture.away_code] = fixture.away_team

        names = [
            {
                'entity_type': self.entity_type,
                'entity_code': code,
                'locale': self.LOCALE,
                'name': name,
            }
            for code, name in teams.items()
        ]
        return names, fixtures[-1].id


class FotmobTeamNameScanner(TeamNameScanner):
    def get_pending_fetch_teams(self, last_id: int) -> List[Any]:
        return self.name_i18n_dao.get_fotmob_pending_fetch_teams(last_id)


class LeagueNameScanner(BaseNameScanner):
    def __init__(self) -> None:
        super().__init__(EntityType.LEAGUE)

    def get_pending_fetch_leagues(self, last_id: int) -> List[Any]:
        return self.name_i18n_dao.get_pending_fetch_leagues(last_id)

    def scan_items(self) -> Optional[Tuple[List[Dict], int]]:
        last_id = self.name_i18n_dao.get_scan_progress(self.entity_type)
        leagues = self.get_pending_fetch_leagues(last_id)
        if not leagues:
            return None

        names = [
            {
                'entity_type': self.entity_type,
                'entity_code': str(league.ref_league_id),
                'locale': self.LOCALE,
                'name': league.league_name,
            }
            for league in leagues
        ]
        return names, leagues[-1].id


class FotmobLeagueNameScanner(LeagueNameScanner):
    pass


@TaskRegistry.poll('scan.name_i18n')
class ScanNameI18n(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.scanners = [
            FotmobTeamNameScanner(),
            FotmobLeagueNameScanner(),
        ]

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            for scanner in self.scanners:
                try:
                    scanner.scan()
                except Exception as e:
                    self.logger.error(f"ScanNameI18n error: {e}", exc_info=True)
            self.idle_sleep()
