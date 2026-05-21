from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def _to_psycopg_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


# prepare_threshold=None disables psycopg's server-side prepared statements,
# keeping us compatible with Supabase's transaction-mode pooler (PgBouncer).
engine: AsyncEngine = create_async_engine(
    _to_psycopg_url(settings.supabase_postgres_url),
    pool_pre_ping=True,
    connect_args={"prepare_threshold": None},
)

async_session_factory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


async def ping_postgres() -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def close_postgres() -> None:
    await engine.dispose()
