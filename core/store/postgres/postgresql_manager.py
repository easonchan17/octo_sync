import os
from functools import cache
from typing import Generator
from sqlalchemy import text
from typing import List, Any, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from core.config.config_manager import get_config_manager
from core.logger.logger_manager import get_logger_manager

class PostgreSQLManager:
    def __init__(self, config: dict) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.config = config
        self.engine = None
        self.session_maker = None

    def startup(self) -> None:
        db_url = f"postgresql://{self.config['db_user']}:{self.config['db_password']}@{self.config['db_host']}:{self.config['db_port']}/{self.config['db_name']}"
        pool_config = self.config['pool_config']

        self.engine = create_engine(db_url, **pool_config)
        self.session_maker = sessionmaker(bind=self.engine)
        self.logger.info(f"PostgreSQLManager initialized with pool_size={pool_config['pool_size']}")

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
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    pool_size = os.getenv('DB_POOL_SIZE')
    max_overflow = os.getenv('DB_MAX_OVERFLOW')
    pool_timeout = os.getenv('DB_POOL_TIMEOUT')
    pool_recycle = os.getenv('DB_POOL_RECYCLE')

    if all([db_host, db_port, db_name, db_user, db_password, pool_size, max_overflow, pool_timeout, pool_recycle]):
        config = {
            'db_host': db_host,
            'db_port': int(db_port),
            'db_name': db_name,
            'db_user': db_user,
            'db_password': db_password,
            'pool_config': {
                'pool_size': int(pool_size),
                'max_overflow': int(max_overflow),
                'pool_timeout': int(pool_timeout),
                'pool_recycle': int(pool_recycle)
            }
        }
    else:
        config = get_config_manager().get_config("database")

    return PostgreSQLManager(config=config)