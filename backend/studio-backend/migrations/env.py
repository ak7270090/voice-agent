"""Alembic runs migrations against DATABASE_URL from the API settings."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from studio_backend.after_call import models as after_call_models  # noqa: F401
from studio_backend.agents import models as agent_models  # noqa: F401 - registers the tables
from studio_backend.calls import models as call_models  # noqa: F401 - registers the tables
from studio_backend.campaigns import models as campaign_models  # noqa: F401
from studio_backend.config import get_settings
from studio_backend.credentials import models as secret_models  # noqa: F401
from studio_backend.database import Base
from studio_backend.flows import models as flow_models  # noqa: F401
from studio_backend.phone_numbers import models as number_models  # noqa: F401

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

target_metadata = Base.metadata


def run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(run_migrations)
    await engine.dispose()


asyncio.run(run_online())
