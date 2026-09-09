"""Compressed long-term narrative memory."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from bson import ObjectId


class MemoryCompactionService:
    async def compact_project_memory(self, db, project_id: str, before_cycle: int | None = None) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        cycle_filter: Dict[str, Any] = {"$lt": before_cycle} if before_cycle else {"$exists": True}
        messages = await db.timeline_messages.find({"project_id": pid, "cycle_number": cycle_filter}).sort("created_at", 1).to_list(length=200)
        outputs = await db.agent_outputs.find({"project_id": pid}).sort("created_at", 1).to_list(length=100)
        threads = await db.plot_threads.find({"project_id": pid, "status": {"$ne": "resolved"}}).to_list(length=50)
        characters = await db.character_bibles.find({"project_id": pid}).to_list(length=50)
        themes = await db.theme_registry.find_one({"project_id": pid}) or {}

        summary = "\n".join([
            f"Timeline: {len(messages)} messages with newest cycle {before_cycle or 'current'}.",
            "Unresolved threads: " + "; ".join(t.get("title", "") for t in threads[:8]),
            "Character arcs: " + "; ".join(f"{c.get('name')}: {c.get('current_arc_state', '')}" for c in characters[:8]),
            "Themes: " + "; ".join(themes.get("themes", [])[:8]),
            "Recent outputs: " + "; ".join(o.get("agent_name", "") for o in outputs[-8:]),
        ]).strip()
        doc = {
            "project_id": pid,
            "before_cycle": before_cycle,
            "summary": summary,
            "preserved_items": {
                "unresolved_threads": [t.get("title") for t in threads],
                "character_arcs": [{"name": c.get("name"), "arc": c.get("current_arc_state")} for c in characters],
                "themes": themes.get("themes", []),
            },
            "created_at": datetime.utcnow(),
        }
        await db.compressed_memories.insert_one(doc)
        return doc


memory_compaction_service = MemoryCompactionService()
