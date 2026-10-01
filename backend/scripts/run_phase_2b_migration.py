"""Run the idempotent Phase 2B migration."""
import asyncio
import json
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.core.database import Database
from app.migrations.phase_2b import migrate_phase_2b


async def main():
    await Database.connect()
    result = await migrate_phase_2b(Database.get_db())
    print(json.dumps(result, indent=2, default=str))
    await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
