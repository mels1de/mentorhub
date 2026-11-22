import asyncio

from alembic import context
from alembic.runtime.environment import NameFilterParentNames, NameFilterType
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.models import Base

settings = get_settings()
configure_logging(settings)

target_metadata = Base.metadata

# Tables that extensions create in "public" (PostGIS) are not ours to manage.
EXTENSION_TABLES = frozenset({"spatial_ref_sys"})


def include_name(name: str | None, type_: NameFilterType, _: NameFilterParentNames) -> bool:
    return not (type_ == "table" and name in EXTENSION_TABLES)


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        include_name=include_name,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_name=include_name,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    # One-shot process: a pool would only keep idle connections until exit.
    engine = create_async_engine(settings.database_url, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
