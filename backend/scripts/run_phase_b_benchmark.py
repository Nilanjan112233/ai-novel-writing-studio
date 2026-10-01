"""Run the matched Phase B Develop Story workflow on a clean source snapshot."""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from bson import ObjectId

BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import scripts.run_phase_e_benchmark as phase_e  # noqa: E402
from app.core.database import Database  # noqa: E402
from app.services.memory_incremental_index_service import memory_incremental_index_service  # noqa: E402
from app.services.project_backup_service import project_backup_service  # noqa: E402


ARTIFACT_DIR = WORKSPACE_ROOT / "artifacts" / "memory-phase-b"


async def main() -> None:
    await Database.connect()
    try:
        db = Database.get_db()
        source = ObjectId(phase_e.SOURCE_PROJECT_ID)
        if not await db.projects.find_one({"_id": source}):
            raise RuntimeError(f"Benchmark source {source} is unavailable")
        backup = await project_backup_service.create(db, source, reason="phase_b_matched_benchmark")
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        restored = await project_backup_service.restore_as_copy(
            db, backup["backup_id"], title=f"Phase B Evidence {stamp}",
            request_id=f"phase-b-{backup['backup_id']}-{stamp}",
        )
        rebuilt = await memory_incremental_index_service.rebuild(db, restored["project_id"], resume=False)
        if rebuilt.get("status") != "READY":
            raise RuntimeError(f"Native rebuild failed: {rebuilt}")
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        phase_e.ARTIFACT_DIR = ARTIFACT_DIR
        artifact = await phase_e._run(db, label="phase_b", project_id=restored["project_id"])
        manifest = {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "source_project_id": phase_e.SOURCE_PROJECT_ID,
            "project_id": restored["project_id"],
            "backup_id": backup["backup_id"],
            "instruction": phase_e.INSTRUCTION,
            "agents": phase_e.AGENTS,
            "rebuild": rebuilt,
            "artifact": "phase-b-provider-run.json",
            "totals": artifact["totals"],
        }
        (ARTIFACT_DIR / "matched-run-manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    finally:
        await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
