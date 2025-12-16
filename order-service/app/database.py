import os
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

def get_mongo_client() -> MongoClient:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    # serverSelectionTimeoutMS evita travar muito tempo se o Mongo estiver fora
    return MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

def get_database(client: MongoClient | None = None) -> Database:
    if client is None:
        client = get_mongo_client()
    db_name = os.getenv("MONGO_DB", "orders_db")
    return client[db_name]

def get_orders_collection(db: Database) -> Collection:
    collection_name = os.getenv("MONGO_COLLECTION", "orders")
    return db[collection_name]
