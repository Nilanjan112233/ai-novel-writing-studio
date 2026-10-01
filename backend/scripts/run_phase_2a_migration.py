import asyncio
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.migrations.phase_2a import migrate_phase_2a


async def main():
    client = AsyncIOMotorClient(settings.mongodb_url)
    try:
        result = await migrate_phase_2a(client[settings.database_name])
        print(json.dumps(result, indent=2, default=str))
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
