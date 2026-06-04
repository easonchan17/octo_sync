from functools import cache
from typing import Generator
from sqlalchemy import text
from typing import List, Any, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from core.config.config_manager import get_config_manager
from core.config.env_manager import get_env_manager
from core.logger.logger_manager import get_logger_manager

class PostgreSQLManager:
    def __init__(self, db_url: str, pool_config: dict) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.db_url = db_url
        self.pool_config = pool_config
        self.engine = None
        self.session_maker = None

    def startup(self) -> None:
        self.engine = create_engine(self.db_url, **self.pool_config)
        self.session_maker = sessionmaker(bind=self.engine)
        self.logger.info(f"PostgreSQLManager initialized with pool_size={self.pool_config['pool_size']}")

    def cleanup(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
            self.logger.info("PostgreSQLManager resources cleaned up")

    def create_schema(self, schema_name: str) -> None:
        with self.get_session() as session:
            session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            self.logger.info(f"Schema {schema_name} created")

    def create_tables(self, table_classes: List[Any], schema_name: str = None) -> None:
            options = {}
            if schema_name:
                options["schema_translate_map"] = {"{schema}": schema_name}

            with self.engine.connect().execution_options(**options) as conn:
                with conn.begin():
                    for table_class in table_classes:
                        table_class.__table__.create(conn, checkfirst=True)
                        table_name = table_class.__table__.name if schema_name is None else f"{schema_name}.{table_class.__table__.name}"
                        self.logger.info(f"Table {table_name} created successfully")

    def get_conn_string(self) -> str:
        return self.db_url

    def get_checkpoint_pool_size(self) -> tuple[int, int]:
        pool_size = self.pool_config['pool_size']
        return 2, max(2, pool_size // 4)

    @contextmanager
    def get_session(self, schema_name: Optional[str] = None, session: Optional[Session] = None) -> Generator[Session, None, None]:
        if session:
            yield session
            return

        session = self.session_maker()
        if schema_name:
            options = {"schema_translate_map": {"{schema}": schema_name}}
            session.connection().execution_options(**options)

        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()


@cache
def get_postgresql_manager() -> PostgreSQLManager:
    env_manager = get_env_manager()
    pool_config = get_config_manager().get_config("database.pool_config")
    return PostgreSQLManager(db_url=env_manager.DB_URL, pool_config=pool_config)