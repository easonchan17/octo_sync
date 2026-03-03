import pandas as pd
from pathlib import Path
from core.types.enums import SiteName
from core.services.league import league_service
from core.utils.downloader import FileDownloader
from core.store.postgres.models import MarketOdds
from core.utils.pandas_utils import load_dataframe
from typing import Any, Dict, Optional, List, Tuple
from core.scheduler.tasks.base_task import BaseTask
from core.services.team_resolver import TeamResolver
from core.store.postgres.models.fotmob import Fixture
from core.store.postgres.daos.football_data import OddsDao
from core.registry import Registry

@Registry.task('sync.football_data.odds')
class SyncOdds(BaseTask):
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

    # TIME_CORRECTIONS: Dict[Tuple[str, str, str], str] = {
    #     ('20/04/2021', 'Chelsea', 'Brighton'): '20:15',
    #     ('19/12/2021', 'Newcastle', 'Man City'): '14:15',
    #     ('26/02/2022', 'Brighton', 'Aston Villa'): '15:00',
    # }

    URL_TEMPLATE = "https://www.football-data.co.uk/mmz4281/{season_code}/{league_code}.csv"

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.odds_dao = OddsDao()
        self.team_resolver = TeamResolver()

    @property
    def dataset_path(self) -> Path:
        return Path(self.config_manager.get_config("artifact.dataset.training"))

    def execute(self, *args, **kwargs) -> None:
        league_id = self.get_required_param("league_id")
        min_season = self.get_required_param("min_season")
        max_season = self.get_required_param("max_season")

        site_league = league_service.get(league_id).site_leagues.get(SiteName.FOTMOB.value)

        for season in range(min_season, max_season + 1):
            try:
                dataset_file = self.download_dataset(site_league.league_id, season, self.dataset_path)

                odds_records = self.parse_dataset(dataset_file, timezone)
                if not odds_records:
                    self.logger.warning(f"No records parsed for {comp_name} {season} market odds")
                    continue

                self.team_resolver.resolve(odds_records, Fixture, attach_ref=True)
                match_code_key = MarketOdds.match_code.key
                for record in odds_records:
                    record[match_code_key] = record.pop('ref_obj').match_code

                kickoff_time_key = MarketOdds.kickoff_time.key
                last_synced_time = odds_records[-1].get(kickoff_time_key)
                self.odds_dao.save_records(
                    comp_code, season, last_synced_time, odds_records, update_state=False
                )
            except Exception as e:
                self.logger.error(f"Failed to sync {comp_name} {season} market odds: {e}")

    def download_dataset(self, league_code: str, season: int, dataset_path: Path) -> Path:
        season_code = f"{season % 100:02d}{(season + 1) % 100:02d}"
        save_path = dataset_path / f"{league_code}-{season_code}.csv"

        url = self.URL_TEMPLATE.format(season_code=season_code, league_code=league_code)
        with FileDownloader() as downloader:
            if not downloader.download(url, save_path):
                raise Exception(f"Failed to download dataset from {url}")

        return save_path

    def parse_dataset(self, dataset_file: Path, timezone: str) -> List[Dict[str, Any]]:
        df = load_dataframe(dataset_file)

        # for (date, home_team, away_team), correct_time in self.TIME_CORRECTIONS.items():
        #     mask = (df['Date'] == date) & (df['HomeTeam'] == home_team) & (df['AwayTeam'] == away_team)
        #     if mask.any():
        #         df.loc[mask, 'Time'] = correct_time

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
