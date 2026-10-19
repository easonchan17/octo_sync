from functools import cache
from typing import Generator, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from core.config.config_manager import get_config_manager
from core.config.env_manager import get_env_manager
from core.logger.logger_manager import get_logger_manager

class PostgreSQLManager:
    def __init__(self, db_url: str, pool_config: dict) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.db_url = db_url
        self.pool_config = pool_config
        self.engine: Optional[Engine] = None
        self.session_maker: Optional[sessionmaker[Session]] = None

    def startup(self) -> None:
        if self.engine is not None:
            raise RuntimeError("PostgreSQLManager is already started")

        self.engine = create_engine(self.db_url, **self.pool_config)
        self.session_maker = sessionmaker(bind=self.engine)
        self.logger.info(f"PostgreSQLManager initialized with pool_size={self.pool_config['pool_size']}")

    def cleanup(self) -> None:
        if self.engine is None:
            raise RuntimeError("PostgreSQLManager is not started")

        self.engine.dispose()
        self.engine = None
        self.session_maker = None
        self.logger.info("PostgreSQLManager resources cleaned up")

    def get_conn_string(self) -> str:
        return self.db_url

    def get_checkpoint_pool_size(self) -> tuple[int, int]:
        pool_size = self.pool_config['pool_size']
        return 2, max(2, pool_size // 4)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        if self.session_maker is None:
            raise RuntimeError("PostgreSQLManager is not started")

        session = self.session_maker()

        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database session error: {e}")
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


@cache
def get_postgresql_manager() -> PostgreSQLManager:
    env_manager = get_env_manager()
    pool_config = get_config_manager().get_config("database.pool_config")
    return PostgreSQLManager(db_url=env_manager.DB_URL, pool_config=pool_config)