import pandas as pd
from abc import abstractmethod
from core.store.postgres.models import Site
from typing import Any, Dict, Optional, List
from core.logger.logger_manager import LoggerManager
from core.store.postgres.postgresql_manager import PostgreSQLManager

class BaseAnalyzer:
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        self.site = site
        self.payload = payload
        self.db = PostgreSQLManager.get_instance()
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def analyze(self, *args, **kwargs) -> Optional[pd.DataFrame]:
        try:
            comp_code = self.payload["comp_code"]
            min_season = self.payload["min_season"]
            max_season = self.payload["max_season"]

            stats = self.query_raw_data(comp_code, min_season, max_season)
            if not stats:
                self.logger.warning(f"No data found for comp_code={comp_code}, seasons={min_season}-{max_season}")
                return None

            self.logger.info(f"Data queried for comp_code={comp_code}, seasons={min_season}-{max_season}")
            df = self.do_feature_engineering(stats, options=self.payload)
            self.logger.info(f"Data feature engineering completed")
            return df
        except Exception as e:
            self.logger.error(f"Error saving output: {e}", exc_info=True)
            return None

    @abstractmethod
    def query_raw_data(self, comp_code: str, min_season: int, max_season: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def do_feature_engineering(
        self,
        stats: List[Dict[str, Any]],
        options: Dict[str, Any]
    ) -> Optional[pd.DataFrame]:
        pass