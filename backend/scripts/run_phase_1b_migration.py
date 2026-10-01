"""Run and report the idempotent Phase 1B MongoDB migration."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.migrations.phase_1b import migrate_phase_1b


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongodb_url)
    try:
        result = await migrate_phase_1b(client[settings.database_name])
        print(json.dumps(result, default=str, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
