from core.logger.logger_manager import get_logger_manager
from core.store.postgres.postgresql_manager import get_postgresql_manager

class BaseService:
    def __init__(self) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.db = get_postgresql_manager()