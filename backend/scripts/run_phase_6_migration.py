"""Run the idempotent Phase 6 migration against the configured database."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Database
from app.migrations.phase_6 import migrate_phase_6


async def main() -> None:
    await Database.connect()
    print(await migrate_phase_6(Database.get_db()))
    await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
