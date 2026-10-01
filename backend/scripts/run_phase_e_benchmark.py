"""Run the provider-backed Phase E matched Develop Story benchmark.

The baseline command creates one portable backup, restores two identical project
copies, and runs the legacy packets on the first copy.  The optimized command
runs the same instruction and agent roster on the second copy after Phase E is
installed.  Provider prompts are captured at the gateway boundary so reported
prompt size includes the actual serialized request, not just an intermediate
context estimate.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from bson import ObjectId, json_util


BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.workflow import build_persistent_state, next_cycle_number  # noqa: E402
from app.core.database import Database  # noqa: E402
from app.services.memory_incremental_index_service import memory_incremental_index_service  # noqa: E402
from app.services.narrative_studio import narrative_studio_service  # noqa: E402
from app.services.observability_service import estimate_cost  # noqa: E402
from app.services.project_backup_service import project_backup_service  # noqa: E402
from app.services.provider_gateway import estimate_tokens, provider_gateway  # noqa: E402


SOURCE_PROJECT_ID = "6a788192066c6d634556c254"
AGENTS = [
    "RelationshipAgent",
    "CharacterJourneyAgent",
    "MysteryAgent",
    "ArcArchitectAgent",
    "PacingAgent",
]
BENCHMARK_PROVIDER = "gemini"
BENCHMARK_MODEL = "gemini-3.1-flash-lite"
INSTRUCTION = (
    "Develop the next planning pass for Mara's search for Elias in Northglass. Preserve the "
    "confirmed chronology that Elias disappeared five years ago, the central disappearance mystery, "
    "and the planned possibility-that-he-is-alive reveal around Chapter 10. Strengthen relationship "
    "progression, Mara's character journey, mystery escalation, arc coherence, and pacing without "
    "drafting prose or promoting candidate extraction about Lindon, the ledger, or Mara's memories."
)
ARTIFACT_DIR = WORKSPACE_ROOT / "artifacts" / "memory-phase-e"
MATCH_FILE = ARTIFACT_DIR / "matched-projects.json"


def _jsonable(value: Any) -> Any:
    return json.loads(json_util.dumps(value))


def _extract_project_context(messages: list[dict[str, Any]]) -> dict[str, Any]:
    for message in reversed(messages):
        content = str(message.get("content") or "")
        marker = "Project context:\n"
        if marker not in content:
            continue
        raw = content.split(marker, 1)[1]
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _token_map(value: dict[str, Any]) -> dict[str, int]:
    return {
        key: estimate_tokens(json.dumps(item, default=str, ensure_ascii=False))
        for key, item in value.items()
    }


async def _prepare_pair(db) -> dict[str, Any]:
    source_id = ObjectId(SOURCE_PROJECT_ID)
    if not await db.projects.find_one({"_id": source_id}):
        raise RuntimeError(f"Benchmark source project {SOURCE_PROJECT_ID} is unavailable")
    backup = await project_backup_service.create(db, source_id, reason="phase_e_matched_benchmark")
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    baseline = await project_backup_service.restore_as_copy(
        db,
        backup["backup_id"],
        title=f"Phase E Baseline {stamp}",
        request_id=f"phase-e-baseline-{backup['backup_id']}",
    )
    optimized = await project_backup_service.restore_as_copy(
        db,
        backup["backup_id"],
        title=f"Phase E Optimized {stamp}",
        request_id=f"phase-e-optimized-{backup['backup_id']}",
    )
    for project_id in (baseline["project_id"], optimized["project_id"]):
        rebuilt = await memory_incremental_index_service.rebuild(
            db, project_id, resume=False
        )
        if rebuilt.get("status") != "READY":
            raise RuntimeError(f"Native index rebuild did not become READY: {rebuilt}")
    manifest = {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "source_project_id": SOURCE_PROJECT_ID,
        "backup_id": backup["backup_id"],
        "baseline_project_id": baseline["project_id"],
        "optimized_project_id": optimized["project_id"],
        "instruction": INSTRUCTION,
        "agents": AGENTS,
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    MATCH_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


async def _run(db, *, label: str, project_id: str) -> dict[str, Any]:
    pid = ObjectId(project_id)
    project = await db.projects.find_one({"_id": pid})
    if not project:
        raise RuntimeError(f"Benchmark project {project_id} is unavailable")
    cycle_number = await next_cycle_number(db, project_id)
    message = {
        "project_id": pid,
        "cycle_number": cycle_number,
        "role": "user",
        "content": INSTRUCTION,
        "message_type": "instruction",
        "created_at": datetime.utcnow(),
    }
    message_result = await db.timeline_messages.insert_one(message)
    cycle_result = await db.cycles.insert_one({
        "project_id": pid,
        "cycle_number": cycle_number,
        "trigger_message_ids": [message_result.inserted_id],
        "agents_run": [],
        "started_at": datetime.utcnow(),
        "finished_at": None,
        "status": "running",
        "benchmark_label": label,
    })
    cycle_id = str(cycle_result.inserted_id)
    run_result = await db.runs.insert_one({
        "project_id": pid,
        "status": "running",
        "current_agent": "OrchestratorAgent",
        "started_at": datetime.utcnow(),
        "finished_at": None,
        "metadata": {
            "cycle_id": cycle_id,
            "cycle_number": cycle_number,
            "benchmark_label": label,
        },
    })
    run_id = str(run_result.inserted_id)
    state = await build_persistent_state(db, project, project_id, cycle_id)
    state["develop_story_context_mode"] = "legacy" if label.startswith("baseline") else "role_specific"
    state["agent_model_overrides"] = {
        agent: {"provider": BENCHMARK_PROVIDER, "model": BENCHMARK_MODEL}
        for agent in AGENTS
    }

    captured_calls: list[dict[str, Any]] = []
    original_gateway = provider_gateway.generate_with_failover
    replay_outputs: dict[str, Any] = {}
    if label.endswith("_replay"):
        optimized_artifact = json.loads(
            (ARTIFACT_DIR / "optimized-provider-run.json").read_text(encoding="utf-8")
        )
        replay_outputs = {
            row["agent_name"]: row.get("structured_output") or {}
            for row in optimized_artifact.get("agent_outputs") or []
        }

    async def capture_gateway(call_db, messages, **kwargs):
        started = time.perf_counter()
        context = _extract_project_context(messages)
        call = {
            "agent_name": kwargs.get("agent_name"),
            "provider_requested": kwargs.get("provider"),
            "model_requested": kwargs.get("model"),
            "max_output_tokens": kwargs.get("max_tokens"),
            "prompt_tokens": sum(estimate_tokens(str(item.get("content") or "")) for item in messages),
            "prompt_tokens_by_source": _token_map(context),
            "project_context": context,
            "messages": messages,
        }
        try:
            if label.endswith("_replay"):
                parsed = replay_outputs.get(str(kwargs.get("agent_name")))
                if not isinstance(parsed, dict):
                    raise RuntimeError(f"No optimized replay output for {kwargs.get('agent_name')}")
                content = json.dumps(parsed, ensure_ascii=False)
                result = {
                    "content": content,
                    "parsed": parsed,
                    "provider": "deterministic-replay",
                    "model": "matched-optimized-output",
                    "tokens_used": estimate_tokens(content),
                    "latency_ms": 0,
                    "attempts": 1,
                    "fallback_used": False,
                }
            else:
                result = await original_gateway(call_db, messages, **kwargs)
            call.update({
                "provider": result.get("provider"),
                "model": result.get("model"),
                "response_tokens": estimate_tokens(str(result.get("content") or "")),
                "provider_tokens_used": result.get("tokens_used", 0),
                "retry_count": max(0, int(result.get("attempts") or 1) - 1),
                "fallback_used": bool(result.get("fallback_used")),
                "provider_latency_ms": int(result.get("latency_ms") or 0),
                "rate_limit_wait_ms": int(result.get("rate_limit_wait_ms") or 0),
                "execution_trace_id": result.get("execution_trace_id"),
                "status": "success",
            })
            return result
        except Exception as exc:
            call.update({"status": "failed", "error_type": type(exc).__name__, "error": str(exc)})
            raise
        finally:
            call["wall_latency_ms"] = int((time.perf_counter() - started) * 1000)
            captured_calls.append(_jsonable(call))

    provider_gateway.generate_with_failover = capture_gateway
    started = time.perf_counter()
    try:
        result = await narrative_studio_service.run(
            db,
            project_id=project_id,
            state=state,
            run_id=run_id,
            agent_names=AGENTS,
            max_agent_calls=len(AGENTS),
            max_cycle_cost_usd=None,
        )
        status = "completed"
        error = None
    except Exception as exc:
        result = {}
        status = "failed"
        error = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        provider_gateway.generate_with_failover = original_gateway
    wall_latency_ms = int((time.perf_counter() - started) * 1000)
    await db.cycles.update_one(
        {"_id": cycle_result.inserted_id},
        {"$set": {
            "status": status,
            "finished_at": datetime.utcnow(),
            "agents_run": result.get("agents_run", []),
        }},
    )
    await db.runs.update_one(
        {"_id": run_result.inserted_id},
        {"$set": {
            "status": status,
            "current_agent": "",
            "finished_at": datetime.utcnow(),
        }},
    )

    packets = await db.context_packets.find({
        "project_id": pid,
        "cycle_number": cycle_number,
        "agent_name": {"$in": AGENTS},
    }).sort("created_at", 1).to_list(length=100)
    traces = await db.execution_traces.find({"run_id": run_id}).sort("created_at", 1).to_list(length=100)
    outputs = await db.agent_outputs.find({"run_id": run_result.inserted_id}).sort("created_at", 1).to_list(length=100)
    prompt_tokens = sum(int(item.get("prompt_tokens") or 0) for item in captured_calls)
    response_tokens = sum(int(item.get("response_tokens") or 0) for item in captured_calls)
    provider_cost = sum(
        estimate_cost(
            int(item.get("prompt_tokens") or 0) + int(item.get("response_tokens") or 0),
            str(item.get("provider") or item.get("provider_requested") or ""),
            str(item.get("model") or item.get("model_requested") or ""),
        )
        for item in captured_calls
    )
    artifact = {
        "label": label,
        "captured_at": datetime.utcnow().isoformat() + "Z",
        "status": status,
        "error": error,
        "source_project_id": SOURCE_PROJECT_ID,
        "project_id": project_id,
        "run_id": run_id,
        "cycle_id": cycle_id,
        "cycle_number": cycle_number,
        "instruction": INSTRUCTION,
        "agents": AGENTS,
        "matched_provider": BENCHMARK_PROVIDER,
        "matched_model": BENCHMARK_MODEL,
        "result": _jsonable(result),
        "totals": {
            "provider_calls": len(captured_calls),
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "estimated_provider_cost_usd": provider_cost,
            "wall_latency_ms": wall_latency_ms,
            "retries": sum(int(item.get("retry_count") or 0) for item in captured_calls),
            "fallbacks": sum(1 for item in captured_calls if item.get("fallback_used")),
        },
        "calls": captured_calls,
        "context_packets": _jsonable(packets),
        "execution_traces": _jsonable(traces),
        "agent_outputs": _jsonable(outputs),
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    output = ARTIFACT_DIR / f"{label.replace('_', '-')}-provider-run.json"
    output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(output), "status": status, **artifact["totals"]}, indent=2))
    if status != "completed":
        raise RuntimeError(f"{label} benchmark failed: {error}")
    return artifact


async def async_main(mode: str) -> None:
    await Database.connect()
    try:
        db = Database.get_db()
        if mode == "prepare":
            manifest = await _prepare_pair(db)
            print(json.dumps(manifest, indent=2))
        elif mode == "baseline":
            if not MATCH_FILE.exists():
                raise RuntimeError("Run the prepare command first")
            manifest = json.loads(MATCH_FILE.read_text(encoding="utf-8"))
            await _run(db, label="baseline", project_id=manifest["baseline_project_id"])
        elif mode == "optimized":
            if not MATCH_FILE.exists():
                raise RuntimeError("Run the baseline benchmark first")
            manifest = json.loads(MATCH_FILE.read_text(encoding="utf-8"))
            await _run(db, label="optimized", project_id=manifest["optimized_project_id"])
        else:
            if not MATCH_FILE.exists():
                raise RuntimeError("Run the prepare command first")
            manifest = json.loads(MATCH_FILE.read_text(encoding="utf-8"))
            label = "baseline_replay" if mode == "baseline_replay" else "optimized_replay"
            project_key = "baseline_project_id" if mode == "baseline_replay" else "optimized_project_id"
            await _run(db, label=label, project_id=manifest[project_key])
    finally:
        await Database.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "baseline", "optimized", "baseline-replay", "optimized-replay"))
    args = parser.parse_args()
    if args.mode == "baseline-replay":
        args.mode = "baseline_replay"
    elif args.mode == "optimized-replay":
        args.mode = "optimized_replay"
    asyncio.run(async_main(args.mode))


if __name__ == "__main__":
    main()
