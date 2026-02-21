import pandas as pd
from pathlib import Path
from functools import cached_property
from core.types.enums import SiteName
from core.store.postgres.models import Site
from core.utils.downloader import FileDownloader
from core.utils.pandas_utils import load_dataframe
from core.scheduler.tasks.base_task import BaseTask
from typing import Any, Dict, List, Optional, Tuple
from core.services.league import league_service
from core.store.postgres.models.fbref.market_odds import MarketOdds
from core.store.postgres.models.fbref import Fixture as FbrefFixture
from core.services.team_resolver import TeamResolver
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
        return Path(self.config_manager.get_config("artifact.dataset.training"))

    def execute(self, *args, **kwargs) -> None:
        league_id = self.get_required_param("league_id")
        min_season = self.get_required_param("min_season")
        max_season = self.get_required_param("max_season")

        league_config = league_service.get(league_id).site_leagues.get(SiteName.FOOTBALL_DATA.value)
        comp_code = league_config.league_id
        comp_name = league_config.league_name
        timezone = league_config.extra_data.get("timezone")

        seen_failed = True

        while seen_failed:
            tasks = self.synchronizer.get_pending_tasks(
                self.site, comp_code, min_season, max_season, CompSyncFlag.MARKET_ODDS.value, is_force=self.is_force
            )
            if not tasks:
                self.logger.warning(f"No pending tasks found for {comp_name}({comp_code}) from {min_season} to {max_season}")
                return

            seen_failed = False
            for season in tasks:
                try:
                    odds_records = self.load_dataset(comp_name, season, timezone)
                    if not odds_records:
                        self.logger.warning(f"No records loaded for {comp_name} {season} market odds")
                        continue

                    self.team_resolver.resolve(
                        odds_records,
                        SiteName.FBREF.value,
                        FbrefFixture,
                        attach_ref=True
                    )

                    kickoff_time_key = MarketOdds.kickoff_time.key
                    match_code_key = MarketOdds.match_code.key
                    for record in odds_records:
                        record[match_code_key] = record.pop('ref_obj').match_code

                    last_synced_time = odds_records[-1].get(kickoff_time_key)
                    self.synchronizer.sync(
                        self.site, comp_code, season, last_synced_time, odds_records
                    )
                except Exception as e:
                    self.logger.error(f"Failed to sync {comp_name} {season} market odds: {e}")
                    # seen_failed = True

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
