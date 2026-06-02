import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool, text
from sqlalchemy.engine import URL
from alembic.script import ScriptDirectory
from alembic import context
from alembic.config import Config

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
MIGRATIONS_DIR = project_root / "core/store/postgres/migrations"

from core.store.postgres.models import Base
from core.config.env_manager import get_env_manager


def apply_db_url(config: Config) -> None:
    env_manager = get_env_manager()
    url = URL.create(
        drivername=env_manager.DB_DRIVER,
        username=env_manager.DB_USER,
        password=env_manager.DB_PASSWORD or None,
        host=env_manager.DB_HOST,
        port=env_manager.DB_PORT,
        database=env_manager.DB_NAME,
    )
    config.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))

def prepare_migration_sql_path(config: Config) -> Optional[Path]:
    script = ScriptDirectory.from_config(config)
    head_revision_id = script.get_current_head()
    if not head_revision_id:
        return None

    if isinstance(head_revision_id, tuple):
        head_revision_id = head_revision_id[0]

    head_revision = script.get_revision(head_revision_id)

    if not head_revision.doc or not head_revision.doc.strip():
        sys.stderr.write(f"\nError: Empty docstring for revision {head_revision.revision}!\n")
        return None

    slug = re.sub(r'[^a-z0-9]+', '_', head_revision.doc.lower()).strip('_')
    timestamp = datetime.now().strftime("%Y_%m_%d_%H%M")
    filename = f"{timestamp}-{head_revision.revision}_{slug}.sql"

    try:
        MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        sys.stderr.write(f"\nError: Cannot create directory: {MIGRATIONS_DIR}\nDetail: {e}\n")
        return None

    return MIGRATIONS_DIR / filename

def make_process_revision_directives() -> Callable:
    def process_revision_directives(context, revision, directives):
        if not directives:
            return

        script = directives[0]
        if not script.upgrade_ops.ops:
            directives[:] = []
            print(" [Alembic] No changes detected, skipping.", file=sys.stderr)

    return process_revision_directives

CHECKPOINTER_TABLES = {"checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations"}

def is_checkpointer_table(schema, name) -> bool:
    return schema in (None, "public") and name in CHECKPOINTER_TABLES

def include_object(obj, name, type_, reflected, compare_to) -> bool:
    if type_ == "table":
        return not is_checkpointer_table(obj.schema, name)

    if type_ == "index":
        table = getattr(obj, "table", None)
        if table is not None and is_checkpointer_table(table.schema, table.name):
            return False

    return True

def run_migrations_offline(config: Config) -> None:
    url = config.get_main_option("sqlalchemy.url")
    file_path = prepare_migration_sql_path(config)

    if not file_path:
        print(" [Alembic] No revisions found to generate SQL for.", file=sys.stderr)
        return

    print(f" [Alembic] Generating SQL to: {file_path}", file=sys.stderr)

    with open(file_path, "w", encoding="utf-8") as f:
        context.configure(
            url=url,
            target_metadata=Base.metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            include_schemas=True,
            compare_type=True,
            output_buffer=f,
        )

        with context.begin_transaction():
            context.run_migrations()

def ensure_schemas(connection) -> None:
    schemas = {t.schema for t in Base.metadata.tables.values() if t.schema}
    for schema in schemas:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    connection.commit()

def run_migrations_online(config: Config) -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        ensure_schemas(connection)

        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            include_schemas=True,
            compare_type=True,
            include_object=include_object,
            process_revision_directives=make_process_revision_directives()
        )

        with context.begin_transaction():
            context.run_migrations()

alembic_config = context.config
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

apply_db_url(alembic_config)

if context.is_offline_mode():
    run_migrations_offline(alembic_config)
else:
    run_migrations_online(alembic_config)
