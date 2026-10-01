"""Run the idempotent Phase 3A migration."""
import asyncio
import json
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.core.database import Database
from app.migrations.phase_3a import migrate_phase_3a


async def main():
    await Database.connect()
    result = await migrate_phase_3a(Database.get_db())
    print(json.dumps(result, indent=2, default=str))
    await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
