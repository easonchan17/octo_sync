import pandas as pd
from pathlib import Path
from core.utils.downloader import FileDownloader
from typing import Any, Dict, List, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.store.postgres.models.fbref.market_odds import MarketOdds
from core.scheduler.tasks.sync.common.team_resolver import TeamResolver
from core.store.postgres.models.fbref.comp_sync_state import CompSyncFlag
from core.scheduler.synchronizers.fbref.market_odds_synchronizer import MarketOddsSynchronizer


class SyncMarketOdds(BaseTask):
    COLUMN_MAPPING = {
        'kickoff_time': 'kickoff_time',
        'HomeTeam': 'home_team',
        'AwayTeam': 'away_team',
        'PSH': 'home_open',
        'PSD': 'draw_open',
        'PSA': 'away_open',
        'PSCH': 'home_close',
        'PSCD': 'draw_close',
        'PSCA': 'away_close',
        'AHh': 'ah_line_open',
        'PAHH': 'ah_home_open',
        'PAHA': 'ah_away_open',
        'AHCh': 'ah_line_close',
        'PCAHH': 'ah_home_close',
        'PCAHA': 'ah_away_close'
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.team_resolver = TeamResolver()
        self.synchronizer = MarketOddsSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        try:
            timezone = self._get_required_param("timezone")
            comp_code = self._get_required_param("comp_code")
            comp_name = self._get_required_param("comp_name")
            comp_name_with_dash = comp_name.replace(" ", "-")

            min_season = self._get_required_param("min_season")
            max_season = self._get_required_param("max_season")

            tasks = self.synchronizer.get_pending_tasks(
                self.site, comp_code, min_season, max_season, CompSyncFlag.MARKET_ODDS.value
            )
            if not tasks:
                self.logger.warning(f"No pending tasks found for {comp_name}({comp_code}) from {min_season} to {max_season}")
                return

            for season in tasks:
                source_matches = self._load_match_records(comp_name_with_dash, season, timezone)
                if not source_matches:
                    self.logger.warning(f"No source matches loaded for {comp_name_with_dash} {season}")
                    continue

                target_matches = self.synchronizer.get_target_matches(comp_code, source_matches[0]['kickoff_time'])
                self.team_resolver.resolve(source_matches, target_matches, with_target=True)

                for record in source_matches:
                    record['match_code'] = record.pop('target').match_code

                last_synced_time = source_matches[-1].get(MarketOdds.kickoff_time.key)
                self.synchronizer.sync(
                    self.site, comp_code, season, last_synced_time, source_matches
                )
        except Exception as e:
            self.logger.error(f"Failed to sync market odds: {e}", exc_info=True)

    def _get_required_param(self, key: str) -> Any:
        value = self.payload.get(key)
        if not value:
            raise ValueError(f"{key} is required")
        return value

    def _load_match_records(self, comp_name: str, season: int, timezone: str) -> List[Dict[str, Any]]:
        dataset_path = Path(self.config_manager.get_config("training.artifact.dataset"))
        file_name = f"{comp_name}-{season}-{season+1}.csv"

        dataset_file = dataset_path / file_name
        if not dataset_file.exists():
            with FileDownloader() as downloader:
                downloader.download('https://www.football-data.co.uk/mmz4281/2526/E0.csv', dataset_file)

            if not dataset_file.exists():
                self.logger.warning(f"CSV file not found: {dataset_file}")
                return []

        df = pd.read_csv(dataset_file, encoding='utf-8')
        if df.empty:
            self.logger.warning(f"CSV file is empty: {dataset_file}")
            return []

        df['kickoff_time'] = pd.to_datetime(
            df['Date'] + ' ' + df['Time'],
            format='%d/%m/%Y %H:%M'
        ).dt.tz_localize(timezone).dt.tz_convert('UTC')

        df['kickoff_time'] = df['kickoff_time'].apply(lambda x: x.to_pydatetime())
        df = df[self.COLUMN_MAPPING.keys()].rename(columns=self.COLUMN_MAPPING)

        records = df.to_dict('records')
        records.sort(key=lambda x: x['kickoff_time'])
        return records
