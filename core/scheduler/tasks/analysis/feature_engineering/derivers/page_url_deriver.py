from urllib.parse import urljoin
from ..processor import FeatureProcessor
from ..constants import (
    SITE_HOST,
    PAGE_URL_TEMPLATE,
    PAGE_URL_COL,
    MATCH_REPORT_COL,
    SEASON_COL,
    HOME_TEAM_COL,
    HOME_CODE_COL
)
from core.utils.html_utils import normalize_club_name

class PageUrlDeriver(FeatureProcessor):
    def process(self) -> None:
        self.ensure_column_does_not_exist(PAGE_URL_COL)
        self.ensure_column_exists(MATCH_REPORT_COL)
        self.ensure_column_exists(SEASON_COL)
        self.ensure_column_exists(HOME_TEAM_COL)
        self.ensure_column_exists(HOME_CODE_COL)

        def build_page_url(row):
            try:
                season = row[SEASON_COL]
                club_name = row[HOME_TEAM_COL]
                club_code = row[HOME_CODE_COL]

                season_range = f"{int(season)}-{int(season)+1}"
                _, club_name_with_dash = normalize_club_name(club_name)

                return PAGE_URL_TEMPLATE.format(
                    club_code=club_code,
                    season=season_range,
                    club_name=club_name_with_dash
                )
            except Exception as e:
                self.logger.warning(f"Failed to build page URL for row: {e}")
                return None

        def build_match_report_url(match_report):
            return urljoin(SITE_HOST.rstrip('/'), match_report)

        self.df[PAGE_URL_COL] = self.df.apply(build_page_url, axis=1)
        self.logger.info(f"Created {PAGE_URL_COL} column")
        self.df[MATCH_REPORT_COL] = self.df[MATCH_REPORT_COL].apply(build_match_report_url)
        self.logger.info(f"Updated {MATCH_REPORT_COL} column")
