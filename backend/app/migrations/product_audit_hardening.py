"""Indexes for authoritative orchestration recovery and decision propagation."""


async def migrate_product_audit_hardening(db) -> dict[str, int]:
    await db.planning_invalidations.create_index(
        [("project_id", 1), ("status", 1), ("created_at", -1)],
        name="planning_invalidations_project_status",
    )
    await db.runs.create_index(
        [("status", 1), ("started_at", -1)],
        name="runs_recovery_status",
    )
    return {"indexes": 2}
