import asyncio
from contextlib import asynccontextmanager
from typing import Awaitable, Callable

from fastapi import FastAPI

from app.api.v1 import carts, checkout, customers, products
from app.core.config import settings
from app.db.init_db import init_postgres_tables
from app.db.mongo import close_mongo, ping_mongo
from app.db.postgres import close_postgres, ping_postgres
from app.db.redis import close_redis, ping_redis

API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_postgres_tables()
    yield
    await close_postgres()
    await close_mongo()
    await close_redis()


app = FastAPI(
    title="polyglot_persistence_backend",
    description="E-commerce backend orchestrating PostgreSQL, MongoDB, and Redis.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(customers.router, prefix=API_V1_PREFIX)
app.include_router(products.router, prefix=API_V1_PREFIX)
app.include_router(carts.router, prefix=API_V1_PREFIX)
app.include_router(checkout.router, prefix=API_V1_PREFIX)


async def _safe_ping(name: str, ping_fn: Callable[[], Awaitable[None]]) -> tuple[str, str]:
    try:
        await ping_fn()
        return name, "ok"
    except Exception as exc:
        return name, f"error: {type(exc).__name__}: {exc}"


@app.get("/health")
async def health_check() -> dict:
    results = await asyncio.gather(
        _safe_ping("postgres", ping_postgres),
        _safe_ping("mongo", ping_mongo),
        _safe_ping("redis", ping_redis),
    )
    databases = dict(results)
    return {
        "status": "ok" if all(v == "ok" for v in databases.values()) else "degraded",
        "app_env": settings.app_env,
        "databases": databases,
    }
