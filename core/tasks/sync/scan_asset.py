from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, List, Dict, Optional, Tuple
from urllib.parse import urlparse
from core.types.enums import SiteName
from core.tasks.poll_task import PollTask
from core.store.postgres.daos.common import AssetDao
from core.scheduler.task_registry import TaskRegistry

class AssetType(str, Enum):
    IMAGE = 'image'


class AssetUsage(str, Enum):
    LOGO = 'logo'


class EntityType(str, Enum):
    TEAM = 'team'
    LEAGUE = 'league'
    PLAYER = 'player'


class BaseAssetScanner(ABC):
    def __init__(self, site_name: str, asset_type: AssetType, entity_type: EntityType, asset_usage: AssetUsage, url_template: str) -> None:
        self.site_name = site_name
        self.asset_type = asset_type
        self.entity_type = entity_type
        self.asset_usage = asset_usage
        self.url_template = url_template
        self.file_ext = PurePosixPath(urlparse(url_template).path).suffix.lstrip('.')
        self.asset_dao = AssetDao()

    @abstractmethod
    def scan_items(self) -> Optional[Tuple[List[Dict], int]]:
        ...

    def sync_items(self, items: List[Dict]) -> None:
        self.asset_dao.sync_scanned_data(items)

    def update_progress(self, max_id: int) -> None:
        self.asset_dao.update_scan_progress(
            self.site_name, self.asset_type, self.entity_type, self.asset_usage, max_id
        )

    def scan(self) -> int:
        result = self.scan_items()
        if result is None:
            return 0

        items, max_id = result
        if items:
            self.sync_items(items)

        self.update_progress(max_id)
        return len(items)


class TeamLogoScanner(BaseAssetScanner):
    def __init__(self, site_name: str, url_template: str) -> None:
        super().__init__(site_name, AssetType.IMAGE, EntityType.TEAM, AssetUsage.LOGO, url_template)

    @abstractmethod
    def get_pending_fetch_teams(self, last_id: int) -> List[Any]:
        ...

    def scan_items(self) -> Optional[Tuple[List[Dict], int]]:
        last_id = self.asset_dao.get_scan_progress(
            self.site_name, self.asset_type, self.entity_type, self.asset_usage
        )
        items = self.get_pending_fetch_teams(last_id)
        if not items:
            return None

        teams: Dict[int, str] = {}
        for item in items:
            if item.home_id not in teams:
                teams[item.home_id] = item.home_code
            if item.away_id not in teams:
                teams[item.away_id] = item.away_code

        now = datetime.now(timezone.utc)
        assets = [
            {
                'source_url': self.url_template.format(team_id),
                'source_site': self.site_name,
                'asset_type': self.asset_type,
                'entity_type': self.entity_type,
                'asset_usage': self.asset_usage,
                'file_name': team_code,
                'file_ext': self.file_ext,
                'next_fetch_at': now,
            }
            for team_id, team_code in teams.items()
        ]
        return assets, items[-1].id


class FotmobTeamLogoScanner(TeamLogoScanner):
    def get_pending_fetch_teams(self, last_id: int) -> List[Any]:
        return self.asset_dao.get_fotmob_pending_fetch_teams(last_id)

class PlayerLogoScanner(BaseAssetScanner):
    def __init__(self, site_name: str, url_template: str) -> None:
        super().__init__(site_name, AssetType.IMAGE, EntityType.PLAYER, AssetUsage.LOGO, url_template)

    @abstractmethod
    def get_pending_fetch_players(self, last_id: int) -> List[Any]:
        ...

    def scan_items(self) -> Optional[Tuple[List[Dict], int]]:
        last_id = self.asset_dao.get_scan_progress(
            self.site_name, self.asset_type, self.entity_type, self.asset_usage
        )
        items = self.get_pending_fetch_players(last_id)
        if not items:
            return None

        players: Dict[int, str] = {}
        for item in items:
            if item.player_id not in players:
                players[item.player_id] = item.player_code

        now = datetime.now(timezone.utc)
        assets = [
            {
                'source_url': self.url_template.format(player_id),
                'source_site': self.site_name,
                'asset_type': self.asset_type,
                'entity_type': self.entity_type,
                'asset_usage': self.asset_usage,
                'file_name': player_code,
                'file_ext': self.file_ext,
                'next_fetch_at': now,
            }
            for player_id, player_code in players.items()
        ]
        return assets, items[-1].id


class FotmobPlayerLogoScanner(PlayerLogoScanner):
    BATCH_SIZE = 2000

    def get_pending_fetch_players(self, last_id: int) -> List[Any]:
        return self.asset_dao.get_fotmob_pending_fetch_players(last_id, self.BATCH_SIZE)

class LeagueLogoScanner(BaseAssetScanner):
    def __init__(self, site_name: str, url_template: str) -> None:
        super().__init__(site_name, AssetType.IMAGE, EntityType.LEAGUE, AssetUsage.LOGO, url_template)

    def scan_items(self) -> Optional[Tuple[List[Dict], int]]:
        last_id = self.asset_dao.get_scan_progress(
            self.site_name, self.asset_type, self.entity_type, self.asset_usage
        )
        leagues = self.asset_dao.get_pending_fetch_leagues(self.site_name, last_id)
        if not leagues:
            return None

        now = datetime.now(timezone.utc)
        assets = [
            {
                'source_url': self.url_template.format(league.league_id),
                'source_site': self.site_name,
                'asset_type': self.asset_type,
                'entity_type': self.entity_type,
                'asset_usage': self.asset_usage,
                'file_name': str(league.ref_league_id),
                'file_ext': self.file_ext,
                'next_fetch_at': now,
            }
            for league in leagues
        ]
        return assets, leagues[-1].id

@TaskRegistry.poll('scan.asset')
class ScanAsset(PollTask):
    FOTMOB_TEAM_LOGO_URL = 'https://images.fotmob.com/image_resources/logo/teamlogo/{}.png'
    FOTMOB_PLAYER_LOGO_URL = 'https://images.fotmob.com/image_resources/playerimages/{}.png'
    FOTMOB_LEAGUE_LOGO_URL = 'https://images.fotmob.com/image_resources/logo/leaguelogo/{}.png'

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.scanners = [
            FotmobTeamLogoScanner(site_name=SiteName.FOTMOB.value, url_template=self.FOTMOB_TEAM_LOGO_URL),
            FotmobPlayerLogoScanner(site_name=SiteName.FOTMOB.value, url_template=self.FOTMOB_PLAYER_LOGO_URL),
            LeagueLogoScanner(site_name=SiteName.FOTMOB.value, url_template=self.FOTMOB_LEAGUE_LOGO_URL),
        ]

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            for scanner in self.scanners:
                try:
                    scanner.scan()
                except Exception as e:
                    self.logger.error(f"ScanAsset error: {e}", exc_info=True)
            self.idle_sleep()
