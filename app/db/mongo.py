from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

mongo_client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongo_url)
mongo_db: AsyncIOMotorDatabase = mongo_client[settings.mongo_db_name]


async def ping_mongo() -> None:
    await mongo_client.admin.command("ping")


async def close_mongo() -> None:
    mongo_client.close()
