import pandas as pd
from abc import ABC, abstractmethod
from datetime import datetime
from core.store.postgres.models import Site
from typing import Any, Dict, Optional, List, Tuple
from core.logger.logger_manager import LoggerManager
from core.store.postgres.postgresql_manager import PostgreSQLManager

class BaseFeatureExtractor(ABC):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        self.site = site
        self.payload = payload
        self.db = PostgreSQLManager.get_instance()
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def analyze_batch(self, comp_code: str, min_season: int, max_season: int) -> Tuple[List[Dict[str, Any]], Optional[pd.DataFrame]]:
        try:
            stats = self.query_batch_raw_data(comp_code, min_season, max_season)
            if not stats:
                self.logger.warning(f"No data found for comp_code={comp_code}, seasons={min_season}-{max_season}")
                return None, None

            self.logger.info(f"Data queried for comp_code={comp_code}, seasons={min_season}-{max_season}")
            df = self.do_feature_engineering(stats)
            self.logger.info(f"Data feature engineering completed")
            return stats, df
        except Exception as e:
            self.logger.error(f"Error saving output: {e}", exc_info=True)
            return None, None

    def analyze_single(self, home_code: str, away_code: str, kickoff_time: datetime) -> Tuple[List[Dict[str, Any]], Optional[pd.DataFrame]]:
        try:
            stats = self.query_single_raw_data(home_code, away_code, kickoff_time)
            if not stats:
                self.logger.warning(f"No data found for home_code={home_code}, away_code={away_code}, kickoff_time={kickoff_time}")
                return None, None

            self.logger.info(f"Data queried for home_code={home_code}, away_code={away_code}, kickoff_time={kickoff_time}")
            df = self.do_feature_engineering(stats, is_single=True)
            self.logger.info(f"Data feature engineering completed")
            return stats, df
        except Exception as e:
            self.logger.error(f"Single analysis failed for {home_code}v{away_code}: {e}", exc_info=True)
            return None, None

    @abstractmethod
    def query_batch_raw_data(self, comp_code: str, min_season: int, max_season: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def query_single_raw_data(self, home_code: str, away_code: str, kickoff_time: datetime) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def do_feature_engineering(self, stats: List[Dict[str, Any]], is_single: bool = False) -> Optional[pd.DataFrame]:
        pass
