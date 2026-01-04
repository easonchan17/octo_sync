import pandas as pd
from pathlib import Path
from core.config.league_config import get_league_metadata
from functools import cached_property
from typing import Any, Dict, List, Optional, Tuple
from core.store.postgres.models import Site
from core.utils.downloader import FileDownloader
from core.utils.pandas_utils import load_dataframe
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

    TIME_CORRECTIONS: Dict[Tuple[str, str, str], str] = {
        ('20/04/2021', 'Chelsea', 'Brighton'): '20:15',
        ('19/12/2021', 'Newcastle', 'Man City'): '14:15',
        ('26/02/2022', 'Brighton', 'Aston Villa'): '15:00',
    }

    POLICY_CONFIG = {
        "url_template": "https://www.football-data.co.uk/mmz4281/{season_range}/{comp_name}.csv"
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.team_resolver = TeamResolver()
        self.synchronizer = MarketOddsSynchronizer()

    @cached_property
    def dataset_path(self) -> Path:
        return Path(self.config_manager.get_config("training.artifact.dataset"))

    def execute(self, *args, **kwargs) -> None:
        try:
            league_id = self.get_required_param("league_id")
            min_season = self.get_required_param("min_season")
            max_season = self.get_required_param("max_season")

            league_metadata = get_league_metadata(league_id, "football-data")
            comp_code = league_metadata["id"]
            comp_name = league_metadata["name"]
            timezone = league_metadata["timezone"]

            tasks = self.synchronizer.get_pending_tasks(
                self.site, comp_code, min_season, max_season, CompSyncFlag.MARKET_ODDS.value, is_force=self.is_force
            )
            if not tasks:
                self.logger.warning(f"No pending tasks found for {comp_name}({comp_code}) from {min_season} to {max_season}")
                return

            for season in tasks:
                source_matches = self.load_dataset(comp_name, season, timezone)
                if not source_matches:
                    self.logger.warning(f"No source matches loaded for {comp_name} {season}")
                    continue

                kickoff_time_key = MarketOdds.kickoff_time.key
                match_code_key = MarketOdds.match_code.key

                first_synced_time = source_matches[0].get(kickoff_time_key)
                target_matches = self.synchronizer.get_target_matches(comp_code, first_synced_time)
                self.team_resolver.resolve(source_matches, target_matches, with_target=True)

                for record in source_matches:
                    record[match_code_key] = record.pop('target').match_code

                last_synced_time = source_matches[-1].get(kickoff_time_key)
                self.synchronizer.sync(
                    self.site, comp_code, season, last_synced_time, source_matches
                )
        except Exception as e:
            self.logger.error(f"Failed to sync market odds: {e}", exc_info=True)

    def prepare_dataset_file(self, comp_name: str, season: int) -> Path:
        season_range = f"{season % 100:02d}{(season + 1) % 100:02d}"
        dataset_file = self.dataset_path / f"{comp_name}-{season_range}.csv"

        if self.is_force or not dataset_file.exists():
            with FileDownloader() as downloader:
                url = self.POLICY_CONFIG['url_template'].format(season_range=season_range, comp_name=comp_name)
                downloader.download(url, dataset_file)

        return dataset_file

    def _fix_time_corrections(self, df: pd.DataFrame) -> pd.DataFrame:
        for (date, home_team, away_team), correct_time in self.TIME_CORRECTIONS.items():
            mask = (df['Date'] == date) & (df['HomeTeam'] == home_team) & (df['AwayTeam'] == away_team)
            if mask.any():
                df.loc[mask, 'Time'] = correct_time
                self.logger.info(f"Fixed time for {date} {home_team} vs {away_team}: {correct_time}")
        return df

    def load_dataset(self, comp_name: str, season: int, timezone: str) -> List[Dict[str, Any]]:
        dataset_file = self.prepare_dataset_file(comp_name, season)

        if not dataset_file.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_file}")

        df = load_dataframe(dataset_file)

        df = self._fix_time_corrections(df)

        kickoff_time_key = MarketOdds.kickoff_time.key
        df[kickoff_time_key] = pd.to_datetime(
            df['Date'] + ' ' + df['Time'],
            format='%d/%m/%Y %H:%M'
        ).dt.tz_localize(timezone).dt.tz_convert('UTC')

        df[kickoff_time_key] = df[kickoff_time_key].apply(lambda x: x.to_pydatetime())
        df = df[self.COLUMN_MAPPING.keys()].rename(columns=self.COLUMN_MAPPING)

        records = df.to_dict('records')
        records.sort(key=lambda x: x[kickoff_time_key])
        return records
