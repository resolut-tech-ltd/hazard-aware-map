from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.db.base import Base
from app.core.config import settings

# Import all models so Alembic can detect them
from app.db.models import User, Detection, Hazard, HazardVerification

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url with our settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
target_metadata = Base.metadata

# PostGIS system tables to ignore
POSTGIS_TABLES = {
    'spatial_ref_sys', 'tabblock', 'edges', 'faces', 'featnames',
    'place', 'cousub', 'county', 'state', 'zip_state_loc',
    'direction_lookup', 'secondary_unit_lookup', 'state_lookup',
    'street_type_lookup', 'zip_lookup', 'zip_lookup_all',
    'zip_lookup_base', 'county_lookup', 'countysub_lookup',
    'place_lookup', 'addr', 'addrfeat', 'bg', 'tract',
    'geocode_settings', 'geocode_settings_default', 'pagc_gaz',
    'pagc_lex', 'pagc_rules', 'topology', 'layer'
}

def include_object(object, name, type_, reflected, compare_to):
    """Filter out PostGIS system tables from migrations."""
    if type_ == "table" and name in POSTGIS_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())
