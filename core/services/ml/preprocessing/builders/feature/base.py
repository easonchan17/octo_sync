import pandas as pd
from typing import Optional
from core.logger.logger_manager import LoggerManager
from core.store.postgres.postgresql_manager import PostgreSQLManager

class BaseFeatureBuilder:
    def __init__(self) -> None:
        self.db = PostgreSQLManager.get_instance()
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)