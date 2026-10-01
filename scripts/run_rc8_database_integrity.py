"""Produce the RC8 database-integrity and E2E-isolation evidence artifact."""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.core.database import Database  # noqa: E402
from app.services.database_audit_service import audit_project_database  # noqa: E402


PROJECT_PREFIXES = ("RC7 Amateur Draft", "The Crown of Emberfall")
E2E_STATE_PATH = ROOT / "artifacts" / "playwright-e2e-project-state.json"


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

    e2e_state = json.loads(E2E_STATE_PATH.read_text(encoding="utf-8"))
    client = AsyncIOMotorClient(settings.mongodb_url)
    e2e_db = client[e2e_state["databaseName"]]
    e2e_projects = await e2e_db.projects.count_documents({})
    e2e_models = await e2e_db.models.count_documents({})
    normal_projects = await db.projects.count_documents({})
    isolation = {
        "database": e2e_state["databaseName"],
        "projects_after_run": e2e_projects,
        "models_after_run": e2e_models,
        "exact_cleaned_project_ids": len(e2e_state.get("exactCleanedProjectIds", [])),
        "cleanup_completed_at": e2e_state.get("completedAt"),
        "normal_database": settings.database_name,
        "normal_project_count": normal_projects,
        "status": "pass" if e2e_projects == 0 and e2e_models == 0 else "fail",
    }

    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "projects": projects,
        "e2e_isolation": isolation,
        "status": (
            "pass"
            if projects
            and all(project["status"] == "pass" for project in projects)
            and isolation["status"] == "pass"
            else "fail"
        ),
    }
    output = ROOT / "artifacts" / "rc8-database-integrity.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    client.close()
    await Database.disconnect()
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
