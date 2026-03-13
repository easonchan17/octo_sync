import traceback
import pandas as pd
from pathlib import Path
from core.registry import Registry
from core.types.enums import SiteName
from typing import Any, Dict, Optional, List
from core.services.league import league_service
from core.utils.downloader import FileDownloader
from core.store.postgres.models import Odds
from core.utils.pandas_utils import load_dataframe
from core.scheduler.tasks.base_task import BaseTask
from core.store.postgres.daos.football_data import OddsDao, LeagueDao

@Registry.task("sync.football_data.odds")
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

    URL_TEMPLATE = "https://www.football-data.co.uk/{ODDS_URI}"

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.odds_dao = OddsDao()

    def make_save_file(self, season: int, league_id: str) -> Path:
        sub_path = f"{SiteName.FOOTBALL_DATA.value}/{season}/{league_id}.csv"
        return Path(self.config_manager.get_config("artifact.dataset.odds")) / sub_path

    def download_dataset(self, url: str, save_file: Path) -> bool:
        with FileDownloader() as downloader:
            return downloader.download(url, save_file)

    def parse_dataset(self, dataset_file: Path, timezone: str) -> List[Dict[str, Any]]:
        df = load_dataframe(dataset_file)

        kickoff_time_key = Odds.kickoff_time.key
        df[kickoff_time_key] = pd.to_datetime(
            df['Date'] + ' ' + df['Time'],
            format='%d/%m/%Y %H:%M'
        ).dt.tz_localize(timezone).dt.tz_convert('UTC')

        df[kickoff_time_key] = df[kickoff_time_key].apply(lambda x: x.to_pydatetime())
        df = df[self.COLUMN_MAPPING.keys()].rename(columns=self.COLUMN_MAPPING)

        records = df.to_dict('records')
        records.sort(key=lambda x: x[kickoff_time_key])
        return records

    def execute(self) -> None:
        league_id = self.get_required_param("league_id")
        min_season = self.get_required_param("min_season")
        max_season = self.get_required_param("max_season")

        system_league = league_service.get(int(league_id))
        if not system_league:
            raise ValueError(f"League {league_id} not found")

        fd_site_league = system_league.site_leagues.get(SiteName.FOOTBALL_DATA.value)
        if not fd_site_league:
            raise ValueError(f"{SiteName.FOOTBALL_DATA.value} league not found for league {league_id}")

        fb_site_league = system_league.site_leagues.get(SiteName.FOTMOB.value)
        if not fb_site_league:
            raise ValueError(f"{SiteName.FOTMOB.value} league not found for league {league_id}")


        fd_league_id = fd_site_league.league_id
        fd_league_name = fd_site_league.league_name

        for season in range(min_season, max_season + 1):
            try:
                item = self.odds_dao.get_pending_fetch_item(season, fd_league_id)
                if not item or item.odds_url:
                    self.logger.error(f"No odds URL for {fd_league_name} in {season}")
                    continue

                # 是否要比较last_fetched_at经过的时间

                file_url = self.URL_TEMPLATE.format(ODDS_URI=item.odds_url.lstrip('/'))
                save_file = self.make_save_file(season, fd_league_id)

                if not self.download_dataset(file_url, save_file):
                    self.odds_dao.mark_fetch_failed(season, fd_league_id, "Download failed")
                    continue

                self.odds_dao.sync_raw_data({
                    "source_url": file_url,
                    "season": season,
                    "league_id": fd_league_id
                })
                self.odds_dao.mark_as_fetched(season, fd_league_id)
            except Exception as e:
                full_stack_trace = traceback.format_exc()
                self.odds_dao.mark_fetch_failed(season, fd_league_id, full_stack_trace)
                self.logger.error(f"Failed to download odds for {fd_league_name} {season}: {e}")



                # odds_records = self.parse_dataset(save_file, timezone)

                # if not odds_records:
                #     self.logger.error(f"No records parsed for {fd_site_league.league_name} {season}")
                #     continue

                # # Preserve original CSV team names before resolver overwrites them
                # for record in odds_records:
                #     record['_home_csv'] = record['home_team']
                #     record['_away_csv'] = record['away_team']

                # # Load all fotmob fixtures for this season (used for candidate hints)
                # start_time = odds_records[0]['kickoff_time']
                # fixtures = self._load_fixtures(start_time, fotmob_league_id)

                # # Auto-match: attaches ref_obj (Fixture) to matched records
                # self.team_resolver.resolve(odds_records, Fixture, attach_ref=True)

                # n_matched = sum(1 for r in odds_records if 'ref_obj' in r)
                # n_unmatched = len(odds_records) - n_matched
                # self.logger.info(f"{fd_site_league.league_name} {season}: {n_matched} auto-matched, {n_unmatched} unmatched")

                # # Manual resolution via visidata when running interactively
                # if n_unmatched > 0 and sys.stdin.isatty():
                #     self.visualize_mapping(odds_records, fixtures)
                # elif n_unmatched > 0:
                #     self.logger.warning(f"Non-interactive mode: {n_unmatched} unmatched records will be skipped")

                # # Collect valid records (those with a resolved match_id)
                # valid_records = []
                # match_code_key = Odds.match_code.key
                # for record in odds_records:
                #     ref = record.pop('ref_obj', None)
                #     match_code = record.get('match_code') or (ref.match_code if ref else None)
                #     if match_code:
                #         record[match_code_key] = match_code
                #         # Also set match_id if available from ref, as it is required by schema
                #         if ref:
                #             record['match_id'] = ref.match_id
                #         valid_records.append(record)
                #     else:
                #         self.logger.warning(f"Skipped: {record.get('_home_csv')} vs {record.get('_away_csv')} @ {record.get('kickoff_time')}")

                # if not valid_records:
                #     self.logger.warning(f"No valid records for {fd_site_league.league_name} {season}, skipping save")
                #     continue

                # kickoff_time_key = Odds.kickoff_time.key
                # last_synced_time = valid_records[-1].get(kickoff_time_key)
                # self.odds_dao.save_records(
                #     league_code, season, last_synced_time, valid_records, update_state=False
                # )


    # # -------------------------------------------------------------------------
    # # Visidata manual resolution
    # # -------------------------------------------------------------------------

    # def visualize_mapping(self, odds_records: List[Dict[str, Any]], fixtures: List[Any]) -> None:
    #     """Open visidata for manual review and correction of unmatched records.

    #     Columns shown:
    #       status       - OK / UNMATCHED
    #       kickoff_time - from the CSV
    #       home_csv     - original CSV home team name
    #       away_csv     - original CSV away team name
    #       home_fotmob  - matched fotmob home team (empty if unmatched)
    #       away_fotmob  - matched fotmob away team (empty if unmatched)
    #       match_code   - **editable** — populated from auto-match or typed by user
    #       cand1_*      - nearest fixture candidate #1 (for unmatched rows)
    #       cand2_*      - nearest fixture candidate #2 (for unmatched rows)

    #     After the user quits visidata (q), any match_code values typed into
    #     UNMATCHED rows are written back to odds_records.
    #     """
    #     for i, r in enumerate(odds_records):
    #         r['_index'] = i

    #     data = []
    #     for r in odds_records:
    #         ref = r.get('ref_obj')
    #         row = {
    #             '_index':       r['_index'],
    #             'status':       'OK' if ref else 'UNMATCHED',
    #             'kickoff_time': r.get('kickoff_time'),
    #             'home_csv':     r.get('_home_csv', r.get('home_team')),
    #             'away_csv':     r.get('_away_csv', r.get('away_team')),
    #             'home_fotmob':  ref.home_team if ref else '',
    #             'away_fotmob':  ref.away_team if ref else '',
    #             'match_code':   str(ref.match_code) if ref else '',
    #         }

    #         # Nearest fixture candidates — only populate for unmatched rows
    #         candidates = self._find_fixture_candidates(r['kickoff_time'], fixtures) if not ref else []
    #         for i_c in range(1, 3):
    #             cand = candidates[i_c - 1] if i_c - 1 < len(candidates) else None
    #             row[f'cand{i_c}_id']      = cand.match_code if cand else ''
    #             row[f'cand{i_c}_kickoff'] = cand.kickoff_time.strftime('%m-%d %H:%M') if cand else ''
    #             row[f'cand{i_c}_home']    = cand.home_team if cand else ''
    #             row[f'cand{i_c}_away']    = cand.away_team if cand else ''

    #         data.append(row)

    #     # Unmatched rows first so they're immediately visible
    #     data.sort(key=lambda x: (0 if x['status'] == 'UNMATCHED' else 1, x['kickoff_time']))

    #     df = pd.DataFrame(data)
    #     n_unmatched = (df['status'] == 'UNMATCHED').sum()
    #     self.logger.info(f"[visidata] {len(df)} records — {n_unmatched} UNMATCHED (shown first).")
    #     self.logger.info("Edit 'match_code' using cand*_id as reference, then press 'q' to continue.")

    #     visidata.run(visidata.PandasSheet("Odds ↔ Fotmob", source=df))

    #     # Read back match_code edits from the modified DataFrame
    #     resolved_count = 0
    #     for _, row in df.iterrows():
    #         idx = int(row['_index'])
    #         val = str(row.get('match_code', '')).strip()
    #         if val:
    #             odds_records[idx]['match_code'] = val
    #             resolved_count += 1

    #     self.logger.info(f"[visidata] Done — {resolved_count} records with match_code set.")

    # # -------------------------------------------------------------------------
    # # Helpers
    # # -------------------------------------------------------------------------

    # def _load_fixtures(self, start_time: datetime, league_id: Optional[int]) -> List[Any]:
    #     """Load fotmob fixtures from start_time for candidate lookup."""
    #     with PostgreSQLManager.get_instance().get_session() as session:
    #         q = session.query(Fixture).filter(Fixture.kickoff_time >= start_time)
    #         if league_id is not None:
    #             q = q.filter(Fixture.league_id == league_id)
    #         fixtures = q.order_by(Fixture.kickoff_time).all()
    #         if fixtures:
    #             session.expunge_all()
    #     return fixtures

    # def _find_fixture_candidates(
    #     self, kickoff_time: datetime, fixtures: List[Any], window_hours: int = 72
    # ) -> List[Any]:
    #     """Return up to 3 fixtures closest to kickoff_time within ±window_hours."""
    #     if not kickoff_time or not fixtures:
    #         return []
    #     window_sec = window_hours * 3600
    #     scored = []
    #     for f in fixtures:
    #         diff = abs((f.kickoff_time - kickoff_time).total_seconds())
    #         if diff <= window_sec:
    #             scored.append((diff, f))
    #     scored.sort(key=lambda x: x[0])
    #     return [f for _, f in scored[:3]]