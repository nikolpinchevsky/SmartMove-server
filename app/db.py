import os
from motor.motor_asyncio import AsyncIOMotorClient


MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartmove_db")


client = AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB_NAME]


# Collections
users_collection = db["users"]
projects_collection = db["projects"]
boxes_collection = db["boxes"]
rooms_collection = db["rooms"]