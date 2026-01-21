import sys
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Callable, List
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import text, MetaData, pool
from alembic.script import ScriptDirectory
from alembic import context
from alembic.config import Config

# --- Path Setup ---
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
MIGRATIONS_DIR = project_root / "core/store/postgres/migrations"
VERSIONS_DIR = project_root / "alembic/versions"

# Import models after sys.path setup
from core.store.postgres.models import Base
from core.domain.enums import SiteName

def require_target_schema() -> str:
    schema = os.getenv('DB_SCHEMA')
    valid_sites = [site.value for site in SiteName] + ['public']

    if not schema:
        print("\n❌ [ERROR] Missing environment variable: DB_SCHEMA", file=sys.stderr)
        print(f"   Valid:   {valid_sites}", file=sys.stderr)
        sys.exit(1)

    if schema not in valid_sites:
        print(f"\n❌ [ERROR] Invalid schema: '{schema}'", file=sys.stderr)
        print(f"   Valid:   {valid_sites}", file=sys.stderr)
        sys.exit(1)

    print(f"🚀 [Alembic] Target Schema: {schema}")
    return schema

def prepare_migration_sql_path(config: Config, schema: str) -> Optional[Path]:
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

    output_dir = MIGRATIONS_DIR / schema

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        sys.stderr.write(f"\nError: Cannot create directory: {output_dir}\nDetail: {e}\n")
        return None

    return output_dir / filename

def make_filters(target_schema: str) -> Tuple[Callable, Callable]:
    def include_name(name, type_, parent_names):
        if type_ == "schema":
            if name is None and target_schema == 'public':
                return True

            return name == target_schema

        if type_ == "table":
            if name.startswith('alembic_version_'):
                return False

            schema_name = parent_names.get("schema")

            if schema_name is None:
                return True

            if schema_name == 'public':
                return target_schema == 'public'

            return schema_name == target_schema

        return True

    def include_object(object, name, type_, reflected, compare_to):
        if type_ == "table":
            if name.startswith('alembic_version_'):
                return False

            schema_name = getattr(object, 'schema', None)

            if schema_name is None:
                return True

            if schema_name == 'public':
                return target_schema == 'public'

            allowed_sites = object.info.get('sites', [])
            return target_schema in allowed_sites

        return True

    return include_name, include_object

def make_process_revision_directives(target_schema: str) -> Callable:
    def process_revision_directives(context, revision, directives):
        if not directives:
            return

        script = directives[0]
        if not script.message or not script.message.strip():
            auto_message = f"upgrade_{target_schema}"
            print(f"⚠️ [Alembic] No message provided. Auto-naming to: '{auto_message}'", file=sys.stderr)
            script.message = auto_message

    return process_revision_directives

def init_version_locations(config: Config, schema: str) -> None:
    version_dir = str(VERSIONS_DIR / schema)
    os.makedirs(version_dir, exist_ok=True)

    if hasattr(context, 'script') and context.script:
        context.script.version_locations = [version_dir]

    config.set_main_option("version_locations", version_dir)
    print(f"📂 [Alembic] Final Version Directory: {version_dir}")

def build_target_metadata(target_schema: str) -> MetaData:
    target_metadata = MetaData()

    for table in Base.metadata.tables.values():
        schema = table.schema

        if target_schema != 'public' and table.schema == '{schema}':
            schema = target_schema

        table.to_metadata(target_metadata, schema=schema)

    return target_metadata

def run_migrations_offline(config: Config, metadata: MetaData, schema: str) -> None:
    url = config.get_main_option("sqlalchemy.url")
    file_path = prepare_migration_sql_path(config, schema)

    if not file_path:
        print("❌ [Alembic] No revisions found to generate SQL for.", file=sys.stderr)
        return

    print(f"📄 [Alembic] Generating SQL to: {file_path}", file=sys.stderr)

    with open(file_path, "w", encoding="utf-8") as f:
        include_name, include_object = make_filters(schema)

        context.configure(
            url=url,
            target_metadata=metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            include_schemas=True,
            version_table_schema='public',
            version_table=f'alembic_version_{schema}',
            include_name=include_name,
            include_object=include_object,
            compare_type=True,
            output_buffer=f,
        )

        with context.begin_transaction():
            context.run_migrations()

def run_migrations_online(config: Config, metadata: MetaData, schema: str) -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        # connection.execute(text(f"SET search_path TO {schema}, public"))
        connection.commit()

        include_name, include_object = make_filters(schema)
        process_revision_directives = make_process_revision_directives(schema)

        context.configure(
            connection=connection,
            target_metadata=metadata,
            include_schemas=True,
            version_table_schema='public',
            version_table=f'alembic_version_{schema}',
            include_name=include_name,
            include_object=include_object,
            compare_type=True,
            process_revision_directives=process_revision_directives
        )

        with context.begin_transaction():
            context.run_migrations()

# --- Main Execution Flow ---

alembic_config = context.config
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

# Init Schema
target_schema = require_target_schema()

# Configure version locations based on schema
init_version_locations(alembic_config, target_schema)

# Dynamic Metadata Generation
target_metadata = build_target_metadata(target_schema)

# Dispatch
if context.is_offline_mode():
    run_migrations_offline(alembic_config, target_metadata, target_schema)
else:
    run_migrations_online(alembic_config, target_metadata, target_schema)