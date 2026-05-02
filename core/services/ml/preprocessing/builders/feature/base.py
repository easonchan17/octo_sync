import pandas as pd
from typing import Optional
from core.logger.logger_manager import LoggerManager
from core.store.postgres.postgresql_manager import PostgreSQLManager

class BaseFeatureBuilder:
    def __init__(self) -> None:
        self.db = PostgreSQLManager.get_instance()
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def build(self) -> Optional[pd.DataFrame]:
        try:
            df = self.load()
            if not df:
                self.logger.error("No raw data frame loaded")
                return None

            df = self.transform(df)
            if df is None or df.empty:
                self.logger.error("Empty transform result")
                return None

            return df
        except Exception as e:
            self.logger.error(f"Build failed: {e}", exc_info=True)
            return None