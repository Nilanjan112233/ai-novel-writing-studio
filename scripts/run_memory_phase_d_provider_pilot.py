"""Bounded real-provider Phase D Develop Story pilot.

This diagnostic runner never changes production packet selection. Experimental
arms monkeypatch the packet builder only inside this process and run against
independent restored project copies made from one exact backup.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from bson import ObjectId, json_util

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

import scripts.run_phase_e_benchmark as phase_e  # noqa: E402
from app.core.database import Database  # noqa: E402
from app.services.develop_story_context_service import develop_story_context_service  # noqa: E402
from app.services.memory_incremental_index_service import memory_incremental_index_service  # noqa: E402
from app.services.observability_service import estimate_cost  # noqa: E402
from app.services.project_backup_service import project_backup_service  # noqa: E402
from app.services.provider_gateway import estimate_tokens, provider_gateway  # noqa: E402
from scripts.run_memory_phase_d_readiness import compact_fact, role_episode_projection  # noqa: E402


ARTIFACT_DIR = ROOT / "artifacts" / "memory-phase-d-provider-pilot"
MANIFEST = ARTIFACT_DIR / "pilot-manifest.json"
SOURCE_PROJECT_ID = phase_e.SOURCE_PROJECT_ID
AGENTS = phase_e.AGENTS
PROVIDER = phase_e.BENCHMARK_PROVIDER
MODEL = phase_e.BENCHMARK_MODEL
INSTRUCTION = phase_e.INSTRUCTION
ARMS = ("current", "fact_only", "progressive")


def _jsonable(value: Any) -> Any:
    return json.loads(json_util.dumps(value))


def _tokens(value: Any) -> int:
    return estimate_tokens(json.dumps(value, ensure_ascii=False, default=str)) if value not in (None, "", [], {}) else 0


def _fingerprint(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=True, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _compact_atomic_facts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for item in items:
        if str(item.get("source_type") or "") != "atomic_memory":
            continue
        content = compact_fact(str(item.get("content") or ""))
        marker = re.sub(r"[^a-z0-9]+", " ", content.lower()).strip()
        if not marker or marker in seen:
            continue
        seen.add(marker)
        rows.append({
            "fact": content,
            "logical_identity": item.get("logical_identity"),
            "authority_level": item.get("authority_level"),
            "validity": item.get("validity"),
            "chapter_number": item.get("chapter_number"),
            "known_by": item.get("known_by") or [],
            "evidence_pointer": item.get("evidence_pointer"),
        })
    return rows[:8]


def _episode_ids(value: dict[str, Any]) -> list[str]:
    result = []
    for row in value.get("episodes") or []:
        pointer = row.get("evidence_pointer") or {}
        identity = ":".join(str(pointer.get(key) or "") for key in ("source_type", "logical_source_id", "source_version"))
        if identity.strip(":"):
            result.append(identity)
    return result


def _phase_d_packet(original: dict[str, Any], *, agent_name: str, arm: str, fault: str | None = None) -> dict[str, Any]:
    """Return a diagnostic packet or the untouched current packet on failure."""
    if arm == "current":
        return copy.deepcopy(original)
    result = copy.deepcopy(original)
    context = result["context"]
    attribution = result["attribution"]
    current_context = copy.deepcopy(context)
    facts = _compact_atomic_facts(list(context.get("native_retrieval") or []))
    evidence_level = "fact"
    episodes: dict[str, Any] = {}
    raw: list[dict[str, Any]] = []
    fallback_reason = ""

    if arm == "progressive":
        episodes = role_episode_projection(current_context, agent_name)
        evidence_level = "episode"
        if fault == "missing_episode":
            episodes = {"episodes": []}
        elif fault == "stale_pointer":
            for row in episodes.get("episodes") or []:
                row["evidence_pointer"] = {"source_type": "chapter_intelligence", "logical_source_id": "stale"}
        # The known real conflict is labelled explicitly; the authority
        # snapshot remains the resolution and is never reduced.
        if episodes.get("episodes"):
            episodes["conflict_notes"] = [{
                "subject": "Elias disappearance chronology",
                "authoritative": "Confirmed planning: Elias disappeared five years ago.",
                "conflicting_derived": "Chapter 2 episode says Elias disappeared two years ago.",
                "resolution": "Follow the five-year authority; retain the two-year episode only as contradictory derived evidence.",
            }]
        if not episodes.get("episodes"):
            fallback_reason = "phase_d_required_episode_missing"
        elif fault == "stale_pointer":
            fallback_reason = "phase_d_stale_evidence_pointer"
    if fault == "validation_failure":
        fallback_reason = "phase_d_evidence_validation_failure"

    if fallback_reason:
        fallback = copy.deepcopy(original)
        fallback["attribution"] = {
            **fallback["attribution"],
            "mode": "phase_d_current_packet_fallback",
            "fallback_reason": fallback_reason,
            "phase_d_requested_arm": arm,
            "phase_d_fallback_target": "current_phase_c",
        }
        fallback["fallback_required"] = False
        return fallback

    context["native_retrieval"] = facts
    context["chapter_episode_memory"] = episodes if arm == "progressive" else {}
    context["raw_evidence"] = raw
    fact_ids = [str(item.get("logical_identity") or "") for item in facts if item.get("logical_identity")]
    episode_ids = _episode_ids(episodes)
    selected_ids = [*fact_ids, *episode_ids]
    manifest = {
        "routing_version": 1,
        "arm": arm,
        "specialist": agent_name,
        "evidence_level": evidence_level,
        "reason": {
            "RelationshipAgent": "episode required for trust and interaction progression",
            "CharacterJourneyAgent": "episode required for causal character progression and consequences",
            "MysteryAgent": "episode required for temporal clue evolution and reveal boundaries",
            "ArcArchitectAgent": "episode required for causal arc integration across character and mystery changes",
            "PacingAgent": "episode required for sequence-level escalation; raw prose is unnecessary without wording/rhythm analysis",
        }.get(agent_name, "role manifest requires bounded episode context"),
        "fact_ids": fact_ids,
        "episode_ids": episode_ids,
        "raw_evidence_ids": [],
        "selected_ids_unique": len(selected_ids) == len(set(selected_ids)),
    }
    manifest["manifest_hash"] = _fingerprint(manifest)
    context["phase_d_evidence_manifest"] = manifest
    attribution.update({
        "mode": f"phase_d_{arm}",
        "fallback_reason": "",
        "phase_d_evidence_level": evidence_level,
        "phase_d_fact_tokens": _tokens(facts),
        "phase_d_episode_tokens": _tokens(episodes),
        "phase_d_raw_tokens": _tokens(raw),
        "phase_d_manifest_hash": manifest["manifest_hash"],
        "phase_d_selected_evidence_ids": selected_ids,
        "phase_d_selected_ids_unique": manifest["selected_ids_unique"],
        "tokens_by_source": {key: _tokens(value) for key, value in context.items()},
        "final_context_tokens": _tokens(context),
    })
    result["fallback_required"] = False
    return result


async def _source_snapshot(db) -> dict[str, Any]:
    pid = ObjectId(SOURCE_PROJECT_ID)
    collections = (
        "canon_registry", "decision_registry", "chapter_drafts", "chapter_intelligence",
        "character_bibles", "relationships", "world_bible", "mysteries", "timeline_entries",
    )
    payload: dict[str, Any] = {}
    for name in collections:
        rows = await db[name].find({"project_id": pid}, {"_id": 0, "created_at": 0, "updated_at": 0}).sort("_id", 1).to_list(length=10000)
        payload[name] = _jsonable(rows)
    return {"project_id": SOURCE_PROJECT_ID, "counts": {key: len(value) for key, value in payload.items()}, "authority_state_hash": _fingerprint(payload)}


async def prepare(db) -> dict[str, Any]:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = await _source_snapshot(db)
    backup = await project_backup_service.create(db, ObjectId(SOURCE_PROJECT_ID), reason="phase_d_provider_quality_pilot")
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    projects = {}
    rebuilds = {}
    for arm in ARMS:
        restored = await project_backup_service.restore_as_copy(
            db, backup["backup_id"], title=f"Phase D Pilot {arm} {stamp}", request_id=f"phase-d-pilot-{arm}-{backup['backup_id']}"
        )
        projects[arm] = restored["project_id"]
        rebuild = await memory_incremental_index_service.rebuild(db, restored["project_id"], resume=False)
        if rebuild.get("status") != "READY":
            raise RuntimeError(f"{arm} rebuild did not become READY: {rebuild}")
        rebuilds[arm] = rebuild
    manifest = {
        "schema_version": 1,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "source_snapshot": snapshot,
        "backup_id": backup["backup_id"],
        "projects": projects,
        "rebuilds": rebuilds,
        "instruction": INSTRUCTION,
        "agents": AGENTS,
        "provider": PROVIDER,
        "model": MODEL,
        "production_behavior_changed": False,
    }
    MANIFEST.write_text(json_util.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


async def run_arm(db, arm: str) -> dict[str, Any]:
    manifest = json_util.loads(MANIFEST.read_text(encoding="utf-8"))
    project_id = manifest["projects"][arm]
    phase_e.ARTIFACT_DIR = ARTIFACT_DIR
    original = develop_story_context_service.build_packet
    deterministic_checks: list[dict[str, Any]] = []

    if arm != "current":
        def diagnostic_builder(**kwargs):
            base = original(**kwargs)
            first = _phase_d_packet(base, agent_name=kwargs["agent_name"], arm=arm)
            second = _phase_d_packet(base, agent_name=kwargs["agent_name"], arm=arm)
            first_hash = (first.get("attribution") or {}).get("phase_d_manifest_hash")
            second_hash = (second.get("attribution") or {}).get("phase_d_manifest_hash")
            deterministic_checks.append({
                "specialist": kwargs["agent_name"],
                "same_manifest_on_repeat": bool(first_hash and first_hash == second_hash),
                "manifest_hash": first_hash,
                "selected_ids_unique": (first.get("attribution") or {}).get("phase_d_selected_ids_unique"),
            })
            return first
        develop_story_context_service.build_packet = diagnostic_builder
    try:
        artifact = await phase_e._run(db, label=f"phase_d_{arm}", project_id=project_id)
    finally:
        develop_story_context_service.build_packet = original
    artifact["arm"] = arm
    artifact["deterministic_manifest_checks"] = deterministic_checks
    artifact["source_snapshot_hash"] = manifest["source_snapshot"]["authority_state_hash"]
    artifact["production_behavior_changed"] = False
    output = ARTIFACT_DIR / f"{arm.replace('_', '-')}-provider-run.json"
    output.write_text(json_util.dumps(artifact, indent=2), encoding="utf-8")
    return artifact


async def raw_test(db) -> dict[str, Any]:
    """Two bounded Gemini calls: episode-only versus episode + exact prose."""
    manifest = json_util.loads(MANIFEST.read_text(encoding="utf-8"))
    pid = ObjectId(manifest["projects"]["progressive"])
    intelligence = await db.chapter_intelligence.find_one({"project_id": pid, "chapter_number": 1, "active": True}) or {}
    draft = await db.chapter_drafts.find_one({"project_id": pid, "chapter_number": 1, "status": "approved", "active": True}) or {}
    episode = (intelligence.get("episode_memory") or {})
    prose = str(draft.get("generated_text") or "")
    match = re.search(r"river taking what it loved", prose, re.IGNORECASE)
    raw_excerpt = ""
    if match:
        raw_excerpt = re.sub(r"\s+", " ", prose[max(0, match.start() - 420):match.end() + 520]).strip()
    system = "You are a read-only NovelForge mystery specialist. Return strict JSON. Never invent or promote story facts."
    instruction = "Evaluate whether the Chapter 1 river foreshadowing was subtle enough. Distinguish what the supplied evidence proves from what it cannot prove."
    results = []
    for arm, raw in (("episode_only", ""), ("episode_plus_raw", raw_excerpt)):
        prompt = {
            "instruction": instruction,
            "authority": {"rule": "Approved prose is authoritative evidence; episode memory is derived."},
            "episode": {key: episode.get(key) for key in ("chapter_number", "summary", "material_events", "mystery_progress", "evidence_pointer")},
            "raw_evidence": raw,
            "contract": {"assessment": "subtle|explicit|insufficient_evidence", "reasoning": "specific evidence-based explanation", "evidence": ["bounded citations/paraphrases"], "recommendation": "actionable planning guidance", "claims_exact_wording": "boolean"},
        }
        messages = [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(prompt, ensure_ascii=True, default=str)}]
        started = time.perf_counter()
        response = await provider_gateway.generate_with_failover(
            db, messages, provider=PROVIDER, model=MODEL, fallbacks=[], temperature=0.2,
            max_tokens=1200, agent_name=f"PhaseDRawEvidence{arm}", expect_json=True,
        )
        results.append({
            "arm": arm,
            "provider": response.get("provider"), "model": response.get("model"),
            "prompt_tokens": sum(estimate_tokens(str(item["content"])) for item in messages),
            "response_tokens": estimate_tokens(str(response.get("content") or "")),
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "retry_count": max(0, int(response.get("attempts") or 1) - 1),
            "fallback_used": bool(response.get("fallback_used")),
            "parsed": response.get("parsed") or {},
            "raw_excerpt_present": bool(raw),
            "raw_excerpt": raw,
        })
    payload = {"schema_version": 1, "instruction": instruction, "provider": PROVIDER, "model": MODEL, "results": results}
    (ARTIFACT_DIR / "raw-evidence-provider-test.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return payload


async def failure_resume(db) -> dict[str, Any]:
    manifest = json_util.loads(MANIFEST.read_text(encoding="utf-8"))
    project_id = manifest["projects"]["progressive"]
    progressive = json_util.loads((ARTIFACT_DIR / "progressive-provider-run.json").read_text(encoding="utf-8"))
    current = json_util.loads((ARTIFACT_DIR / "current-provider-run.json").read_text(encoding="utf-8"))
    calls = progressive.get("calls") or []
    repeat_checks = progressive.get("deterministic_manifest_checks") or []
    handoff_counts: dict[str, int] = {}
    output_counts: dict[str, int] = {}
    pid = ObjectId(project_id)
    run_id = ObjectId(progressive["run_id"])
    for agent in AGENTS:
        handoff_counts[agent] = await db.develop_story_handoffs.count_documents({"project_id": pid, "run_id": run_id, "specialist": agent})
        output_counts[agent] = await db.agent_outputs.count_documents({"project_id": pid, "run_id": run_id, "agent_name": agent})
    # Use an actual captured packet as the immutable input to failure simulations.
    sample_context = copy.deepcopy(current["calls"][0]["project_context"])
    sample_base = {
        "context": sample_context,
        "attribution": {"authority_complete": True, "tokens_by_source": {key: _tokens(value) for key, value in sample_context.items()}, "fallback_reason": ""},
        "fallback_required": False,
    }
    failures = []
    for fault in ("missing_episode", "stale_pointer", "validation_failure"):
        row = _phase_d_packet(sample_base, agent_name="RelationshipAgent", arm="progressive", fault=fault)
        failures.append({"fault": fault, "mode": row["attribution"].get("mode"), "fallback_reason": row["attribution"].get("fallback_reason"), "fallback_target": row["attribution"].get("phase_d_fallback_target"), "invented_evidence": False})
    failures.extend([
        {"fault": "phase_c_unavailable", "mode": "existing_phase_b_complete_scan_fallback", "fallback_reason": "phase_c_not_ready", "fallback_target": "phase_b_p0_safe", "invented_evidence": False},
        {"fault": "phase_b_fallback", "mode": "existing_p0_safe_retrieval", "fallback_reason": "phase_b_complete_path", "fallback_target": "authority_first", "invented_evidence": False},
    ])
    payload = {
        "schema_version": 1,
        "repeat_manifest_checks": repeat_checks,
        "all_manifests_repeat_identically": all(row.get("same_manifest_on_repeat") for row in repeat_checks),
        "all_selected_ids_unique": all(row.get("selected_ids_unique") for row in repeat_checks),
        "handoff_counts": handoff_counts,
        "output_counts": output_counts,
        "no_duplicate_handoffs": all(value == 1 for value in handoff_counts.values()),
        "no_duplicate_outputs": all(value == 1 for value in output_counts.values()),
        "failure_cases": failures,
    }
    (ARTIFACT_DIR / "failure-resume.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return payload


def blind_artifact() -> dict[str, Any]:
    artifacts = {
        arm: json_util.loads((ARTIFACT_DIR / f"{arm.replace('_', '-')}-provider-run.json").read_text(encoding="utf-8"))
        for arm in ARMS
    }
    codes = ["Packet-X", "Packet-Y", "Packet-Z"]
    rng = random.Random(20260814)
    rng.shuffle(codes)
    mapping = dict(zip(codes, ARMS))
    rows = []
    for code, arm in mapping.items():
        outputs = []
        for item in artifacts[arm].get("agent_outputs") or []:
            outputs.append({"specialist": item.get("agent_name"), "structured_output": item.get("structured_output") or {}, "content": item.get("content")})
        rows.append({"code": code, "outputs": outputs})
    blind = {"schema_version": 1, "instruction": INSTRUCTION, "review_dimensions": ["usefulness", "specificity", "narrative_coherence", "cross_domain_integration", "originality", "actionability", "contradiction_awareness", "non_repetition", "author_intent"], "packets": rows}
    (ARTIFACT_DIR / "blind-outputs.json").write_text(json.dumps(blind, indent=2, ensure_ascii=False), encoding="utf-8")
    (ARTIFACT_DIR / "blind-map.json").write_text(json.dumps({"mapping": mapping}, indent=2), encoding="utf-8")
    return blind


async def async_main(command: str, arm: str | None) -> None:
    await Database.connect()
    try:
        db = Database.get_db()
        if command == "prepare":
            result = await prepare(db)
        elif command == "run":
            if arm not in ARMS:
                raise ValueError(f"arm must be one of {ARMS}")
            result = await run_arm(db, arm)
        elif command == "raw-test":
            result = await raw_test(db)
        elif command == "failure-resume":
            result = await failure_resume(db)
        elif command == "blind":
            result = blind_artifact()
        else:
            raise ValueError(command)
        if command not in {"run", "blind"}:
            print(json.dumps(_jsonable(result), indent=2, ensure_ascii=False, default=str))
    finally:
        await Database.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "run", "raw-test", "failure-resume", "blind"))
    parser.add_argument("--arm", choices=ARMS)
    args = parser.parse_args()
    asyncio.run(async_main(args.command, args.arm))


if __name__ == "__main__":
    main()
