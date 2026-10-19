from contextlib import asynccontextmanager
from functools import cache
from typing import AsyncGenerator, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config.config_manager import get_config_manager
from core.config.env_manager import get_env_manager
from core.logger.logger_manager import get_logger_manager


class AsyncPostgreSQLManager:
    def __init__(self, db_url: str, pool_config: dict) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.db_url = db_url
        self.pool_config = pool_config
        self.engine: Optional[AsyncEngine] = None
        self.session_maker: Optional[async_sessionmaker[AsyncSession]] = None

    def startup(self) -> None:
        if self.engine is not None:
            raise RuntimeError("AsyncPostgreSQLManager is already started")

        self.engine = create_async_engine(self.db_url, **self.pool_config)
        self.session_maker = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )
        self.logger.info(
            f"AsyncPostgreSQLManager initialized with pool_size={self.pool_config.get('pool_size')}"
        )

    async def cleanup(self) -> None:
        if self.engine is None:
            raise RuntimeError("AsyncPostgreSQLManager is not started")

        await self.engine.dispose()
        self.engine = None
        self.session_maker = None
        self.logger.info("AsyncPostgreSQLManager resources cleaned up")

    def get_conn_string(self) -> str:
        return self.db_url

    def get_checkpoint_pool_size(self) -> tuple[int, int]:
        pool_size = self.pool_config.get("pool_size", 10)
        return 2, max(2, pool_size // 4)

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        if self.session_maker is None:
            raise RuntimeError("AsyncPostgreSQLManager is not started")

        async_session = self.session_maker()
        try:
            yield async_session
            await async_session.commit()
        except SQLAlchemyError as e:
            await async_session.rollback()
            self.logger.error(f"Database session error: {e}")
            raise
        except Exception:
            await async_session.rollback()
            raise
        finally:
            await async_session.close()


@cache
def get_async_postgresql_manager() -> AsyncPostgreSQLManager:
    env_manager = get_env_manager()
    pool_config = get_config_manager().get_config("database.pool_config")
    return AsyncPostgreSQLManager(db_url=env_manager.ASYNC_DB_URL, pool_config=pool_config)