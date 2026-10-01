"""One matched real-provider Phase C Develop Story validation."""
from __future__ import annotations

import asyncio
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from bson import ObjectId, json_util

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.core.database import Database  # noqa: E402
from app.services.memory_incremental_index_service import memory_incremental_index_service  # noqa: E402
from app.services.narrative_studio import narrative_studio_service  # noqa: E402
from app.services.project_backup_service import project_backup_service  # noqa: E402
from app.api.workflow import build_persistent_state  # noqa: E402

BACKUP_ID = "7b796168-83ce-42ae-bb79-1dffb9f622cc"
INSTRUCTION = "Develop the next planning pass for Mara's search for Elias in Northglass. Preserve the confirmed chronology that Elias disappeared five years ago, the central disappearance mystery, and the planned possibility-that-he-is-alive reveal around Chapter 10. Strengthen relationship progression, Mara's character journey, mystery escalation, arc coherence, and pacing without drafting prose or promoting candidate extraction about Lindon, the ledger, or Mara's memories."
AGENTS = ["RelationshipAgent", "CharacterJourneyAgent", "MysteryAgent", "ArcArchitectAgent", "PacingAgent"]
PROVIDER = "gemini"
MODEL = "gemini-3.1-flash-lite"


async def main():
    await Database.connect()
    db = Database.get_db()
    started = time.perf_counter()
    try:
        args = argparse.ArgumentParser()
        args.add_argument("--refresh-artifact-project")
        parsed = args.parse_args()
        if parsed.refresh_artifact_project:
            output = ROOT / "artifacts" / "memory-phase-c" / "phase-c-provider-run.json"
            payload = json_util.loads(output.read_text(encoding="utf-8"))
            traces = await db.execution_traces.find({
                "project_id": ObjectId(parsed.refresh_artifact_project),
                "run_id": ObjectId(payload["run_id"]),
            }).sort("created_at", 1).to_list(length=30)
            payload["execution_traces"] = traces
            payload["totals"].update({
                "provider_calls": len([item for item in traces if item.get("status") == "success"]),
                "response_tokens": sum(int(item.get("response_tokens") or 0) for item in traces if item.get("status") == "success"),
                "retries": sum(int(item.get("retry_count") or 0) for item in traces),
                "fallbacks": sum(int(bool(item.get("fallback_used"))) for item in traces),
            })
            output.write_text(json_util.dumps(payload, indent=2), encoding="utf-8")
            print(json.dumps({"output": str(output), "totals": payload["totals"]}, indent=2))
            return
        restored = await project_backup_service.restore_as_copy(
            db, BACKUP_ID, title=f"Phase C Ranking {datetime.utcnow():%Y%m%d-%H%M%S}",
            request_id=f"phase-c-{uuid4()}",
        )
        project_id = restored["project_id"]; pid = ObjectId(project_id)
        rebuild = await memory_incremental_index_service.rebuild(db, project_id)
        now = datetime.utcnow()
        message = await db.timeline_messages.insert_one({
            "project_id": pid, "cycle_number": 1, "role": "user", "content": INSTRUCTION,
            "message_type": "instruction", "created_at": now,
        })
        cycle = await db.cycles.insert_one({
            "project_id": pid, "cycle_number": 1, "trigger_message_ids": [message.inserted_id],
            "agents_run": [], "started_at": now, "finished_at": None, "status": "running",
        })
        run = await db.runs.insert_one({
            "project_id": pid, "status": "running", "current_agent": "OrchestratorAgent",
            "started_at": now, "finished_at": None, "metadata": {"cycle_id": str(cycle.inserted_id), "cycle_number": 1, "planned_agents": AGENTS},
        })
        state = await build_persistent_state(db, await db.projects.find_one({"_id": pid}), project_id, str(cycle.inserted_id))
        state["agent_model_overrides"] = {name: {"provider": PROVIDER, "model": MODEL, "fallbacks": []} for name in AGENTS}
        result = await narrative_studio_service.run(
            db, project_id=project_id, state=state, run_id=str(run.inserted_id),
            agent_names=AGENTS, max_cycle_cost_usd=2.0, max_agent_calls=5,
        )
        finished = datetime.utcnow()
        await db.cycles.update_one({"_id": cycle.inserted_id}, {"$set": {"status": "completed", "finished_at": finished, "agents_run": result.get("agents_run") or []}})
        await db.runs.update_one({"_id": run.inserted_id}, {"$set": {"status": "completed", "current_agent": "", "finished_at": finished}})
        packets = await db.context_packets.find({"project_id": pid, "cycle_number": 1, "agent_name": {"$in": AGENTS}}).sort("created_at", 1).to_list(length=20)
        traces = await db.execution_traces.find({"project_id": pid, "run_id": run.inserted_id}).sort("created_at", 1).to_list(length=30)
        outputs = await db.agent_outputs.find({"project_id": pid, "run_id": run.inserted_id}).sort("created_at", 1).to_list(length=20)
        prompt_tokens = sum(int(item.get("final_serialized_prompt_tokens") or item.get("prompt_tokens") or 0) for item in packets)
        response_tokens = sum(int(item.get("response_tokens") or 0) for item in traces if item.get("status") == "success")
        retries = sum(int(item.get("retry_count") or 0) for item in traces)
        fallbacks = sum(int(bool(item.get("fallback_used"))) for item in traces)
        compact_packets = [{
            "agent_name": item.get("agent_name"), "prompt_tokens": item.get("prompt_tokens"),
            "final_serialized_prompt_tokens": item.get("final_serialized_prompt_tokens"),
            "tokens_by_source": (item.get("phase_e_attribution") or {}).get("tokens_by_source") or {},
            "authority_complete": (item.get("phase_e_attribution") or {}).get("authority_complete"),
            "fallback_reason": (item.get("phase_e_attribution") or {}).get("fallback_reason"),
            "ranking_strategies": sorted({
                str(((hit.get("metadata") or {}).get("why_selected") or {}).get("ranking_strategy") or "")
                for hit in ((item.get("packet") or {}).get("retrieved_memory") or [])
            } - {""}),
        } for item in packets]
        payload = {
            "label": "phase_c", "captured_at": finished.isoformat() + "Z", "status": "completed",
            "source_project_id": restored.get("integrity", {}).get("project_id"), "project_id": project_id,
            "run_id": str(run.inserted_id), "cycle_id": str(cycle.inserted_id), "instruction": INSTRUCTION,
            "agents": AGENTS, "matched_provider": PROVIDER, "matched_model": MODEL,
            "rebuild": rebuild, "result": result,
            "totals": {
                "provider_calls": len([item for item in traces if item.get("status") == "success"]),
                "prompt_tokens": prompt_tokens, "response_tokens": response_tokens,
                "estimated_provider_cost_usd": round(float(result.get("actual_cost_usd") or 0), 6),
                "wall_latency_ms": round((time.perf_counter() - started) * 1000),
                "retries": retries, "fallbacks": fallbacks,
            },
            "context_packets": compact_packets,
            "execution_traces": traces,
            "agent_outputs": outputs,
        }
        output = ROOT / "artifacts" / "memory-phase-c" / "phase-c-provider-run.json"
        output.write_text(json_util.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps({"output": str(output), "project_id": project_id, "totals": payload["totals"], "agents_run": result.get("agents_run")}, indent=2))
    finally:
        await Database.disconnect()


if __name__ == "__main__": asyncio.run(main())
