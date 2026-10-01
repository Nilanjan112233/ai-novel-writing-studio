import asyncio
import json

from app.core.config import settings
from app.migrations.phase_3c import migrate_phase_3c
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    client = AsyncIOMotorClient(settings.mongodb_url)
    try:
        result = await migrate_phase_3c(client[settings.database_name])
        print(json.dumps(result, default=str, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
