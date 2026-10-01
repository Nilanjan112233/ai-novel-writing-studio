"""Phase 6 Narrative Intelligence graph and incremental-analysis indexes."""
from datetime import datetime

from pymongo import ASCENDING, DESCENDING


async def migrate_phase_6(db):
    specs = [
        ("narrative_nodes", [("project_id", ASCENDING), ("node_id", ASCENDING)], {"unique": True, "name": "narrative_node_identity"}),
        ("narrative_nodes", [("project_id", ASCENDING), ("kind", ASCENDING), ("analyzed_at", DESCENDING)], {"name": "narrative_nodes_domain"}),
        ("narrative_edges", [("project_id", ASCENDING), ("edge_id", ASCENDING)], {"unique": True, "name": "narrative_edge_identity"}),
        ("narrative_findings", [("project_id", ASCENDING), ("finding_id", ASCENDING)], {"unique": True, "name": "narrative_finding_identity"}),
        ("narrative_findings", [("project_id", ASCENDING), ("domain", ASCENDING), ("status", ASCENDING), ("severity", ASCENDING)], {"name": "narrative_findings_workspace"}),
        ("narrative_analysis_snapshots", [("project_id", ASCENDING), ("calculated_at", DESCENDING)], {"name": "narrative_snapshot_latest"}),
        ("narrative_analysis_jobs", [("project_id", ASCENDING), ("created_at", DESCENDING)], {"name": "narrative_jobs_latest"}),
    ]
    for collection, keys, options in specs:
        await db[collection].create_index(keys, **options)
    await db.app_settings.update_one(
        {"_id": "global_settings"},
        {"$set": {"migrations.phase_6_completed_at": datetime.utcnow(), "migrations.phase_6_version": 1}},
        upsert=True,
    )
    return {"indexes_installed": True, "version": 1}
