import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.store.postgres.models.fbref.match_result import MatchResult
from core.scheduler.tasks.sync.common.team_resolver import TeamResolver
from core.scheduler.synchronizers.fbref.market_odds_synchronizer import MarketOddsSynchronizer


class IngestMarketOdds(BaseTask):
    COLUMN_MAPPING = {
        'HomeTeam': 'home_team',
        'AwayTeam': 'away_team',

        'PSH':  'home_open',
        'PSD':  'draw_open',
        'PSA':  'away_open',
        'PSCH': 'home_close',
        'PSCD': 'draw_close',
        'PSCA': 'away_close',

        'AHh':   'ah_line_open',
        'PAHH':  'ah_home_open',
        'PAHA':  'ah_away_open',
        'AHCh':  'ah_line_close',
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
        comp_code = self.payload.get("comp_code")
        if not comp_code:
            self.logger.error("League ID is required")
            return

        timezone = self.payload.get("timezone")
        if not timezone:
            self.logger.error("Timezone is required")
            return

        dataset_path = self.config_manager.get_config("training.artifact.dataset")
        file_names = self.payload.get("file_names", [])

        df = self._load_dataset(Path(dataset_path), file_names)
        if df.empty:
            self.logger.warning("No CSV files loaded")
            return

        try:
            df['kickoff_time'] = pd.to_datetime(
                df['Date'] + ' ' + df['Time'],
                format='%d/%m/%Y %H:%M'
            ).dt.tz_localize(timezone).dt.tz_convert('UTC').dt.to_pydatetime()

            target_columns = ['kickoff_time'] + list(self.COLUMN_MAPPING.keys())
            df = df[target_columns].rename(columns=self.COLUMN_MAPPING)

            match_records = df.to_dict('records')
            match_records.sort(key=lambda x: x['kickoff_time'])

            target_matches = self.synchronizer.get_target_matches(
                comp_code,
                match_records[0]['kickoff_time']
            )
            self.team_resolver.resolve(match_records, target_matches)
            # self.synchronizer.sync(self.site, match_records)
        except Exception as e:
            self.logger.error(f"Error ingesting market odds: {e}", exc_info=True)

    def _load_dataset(self, dataset_path: Path, file_names: List[str]) -> pd.DataFrame:
        dfs = []
        for file_name in file_names:
            csv_file = dataset_path / file_name
            if not csv_file.exists():
                self.logger.warning(f"CSV file not found: {csv_file}")
                continue
            dfs.append(pd.read_csv(csv_file, encoding='utf-8'))

        return pd.concat(dfs, ignore_index=True).copy() if dfs else pd.DataFrame()