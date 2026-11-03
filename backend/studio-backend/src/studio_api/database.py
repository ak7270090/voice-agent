"""SQLAlchemy engine, the declarative base, and the per-request session dependency."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Request
from pydantic import AfterValidator
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


def assume_utc(value: datetime) -> datetime:
    """Stored times are UTC; SQLite returns them without a timezone."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


UtcDateTime = Annotated[datetime, AfterValidator(assume_utc)]


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
