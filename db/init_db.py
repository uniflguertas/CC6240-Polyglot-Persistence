from app.db.postgres import engine
from app.models import Base  # noqa: F401 — importing Base also imports all mapped models


async def init_postgres_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
