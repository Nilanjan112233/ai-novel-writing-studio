"""Audit the latest final-browser RC7 amateur and multi-chapter projects."""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.database import Database  # noqa: E402
from app.services.database_audit_service import audit_project_database  # noqa: E402


PROJECT_PREFIXES = ("RC7 Amateur Draft", "The Crown of Emberfall")


async def main() -> None:
    await Database.connect()
    db = Database.get_db()
    projects: list[dict[str, Any]] = []
    for prefix in PROJECT_PREFIXES:
        project = await db.projects.find_one(
            {"title": {"$regex": f"^{prefix}"}},
            sort=[("created_at", -1)],
        )
        if not project:
            raise RuntimeError(f"No acceptance project found for {prefix}")
        audit = await audit_project_database(db, str(project["_id"]))
        projects.append(
            {
                "title": project.get("title"),
                "project_id": str(project["_id"]),
                "status": audit["status"],
                "findings": audit["findings"],
                "nonzero_collections": {
                    name: count
                    for name, count in audit["collection_counts"].items()
                    if count
                },
            }
        )

    result = {
        "generated_at_utc": datetime.utcnow().isoformat(),
        "projects": projects,
        "status": (
            "pass"
            if projects and all(project["status"] == "pass" for project in projects)
            else "fail"
        ),
    }
    output = ROOT / "artifacts" / "rc7-database-integrity.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
