import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://order-mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "order_db")

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URL)
    return _client


def get_db():
    client = get_client()
    return client[MONGO_DB]


orders_collection = get_db()["orders"]
