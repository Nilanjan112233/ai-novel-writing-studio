"""Provider-free Phase B atomic/episode storage and retrieval benchmark."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from bson import BSON, ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.services.memory_phase_b_service import build_episode_memory, derive_atomic_documents, episode_text  # noqa: E402
from app.services.memory_retrieval_policy import metadata_for_source  # noqa: E402
from app.services.memory_retrieval_service import embed_text, retrieve_relevant_context  # noqa: E402

SCALES = (10, 25, 50, 100, 250, 500)


def _indexed(pid: ObjectId, source_type: str, source_id: str, content: str, metadata: dict) -> dict:
    return {"project_id": pid, "source_type": source_type, "source_id": source_id, "source_version": int(metadata.get("owner_source_version") or 1), "active": True, "content": content, "content_hash": hashlib.sha256(content.encode()).hexdigest(), "embedding": embed_text(content), "metadata": metadata, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}


def _seed(pid: ObjectId, chapters: int) -> tuple[list[dict], list[dict], list[dict]]:
    episodes = []
    atomic_by_id: dict[str, dict] = {}
    midpoint = max(3, chapters // 2)
    for chapter in range(1, chapters + 1):
        intelligence = {
            "project_id": pid, "intelligence_id": f"intel-{chapter}", "chapter_draft_id": f"draft-{chapter}",
            "chapter_draft_version": 1, "chapter_number": chapter, "active": True,
            "chapter_summary": f"Mara crosses district {chapter} while the controlled mystery advances.",
            "important_events": [f"District {chapter} opens after bell {chapter}.", f"Mara records consequence {chapter}."],
            "characters_present": ["Mara", f"Witness-{chapter}"],
            "character_changes": [{"character": "Mara", "change": f"Her resolve reaches stage {chapter}."}],
            "future_obligations": [f"Return to dormant marker {chapter}."],
        }
        if chapter == midpoint:
            intelligence["important_events"].append("Mara's left palm has healed, leaving a pale scar.")
        episode = build_episode_memory(intelligence)
        episodes.append({**intelligence, "episode_memory": episode, "episode_derivation_version": 1})
        for atomic in derive_atomic_documents(str(pid), "chapter_intelligence", intelligence):
            atomic_by_id[atomic["memory_id"]] = atomic
    special_owners = [
        ("artifact", {"project_id": pid, "artifact_id": "northglass", "item": "Northglass", "owner": "Ivo", "status": "active", "authority_status": "confirmed", "valid_from_chapter": midpoint}),
        ("artifact", {"project_id": pid, "artifact_id": f"asterlock-{chapters}", "item": f"Asterlock-{chapters}", "owner": "Mara", "status": "opens the drowned archive", "authority_status": "confirmed", "valid_from_chapter": chapters}),
        ("relationship", {"project_id": pid, "relationship_id": "mara-ivo", "character_a": "Mara", "character_b": "Ivo", "relationship": "Mara cautiously trusts Ivo.", "status": "confirmed", "authority_status": "confirmed", "valid_from_chapter": midpoint}),
        ("knowledge", {"project_id": pid, "entry_id": "private-elias", "title": "Elias survival", "content": "Elias is alive in the eastern tower.", "known_by": ["Ivo"], "not_known_by": ["Mara"], "chapter_number": midpoint, "status": "confirmed"}),
        ("plot_thread", {"project_id": pid, "thread_id": "dormant", "title": "Silent bell", "description": "The silent bell from Chapter 1 must ring again.", "status": "open", "authority_status": "confirmed", "source_chapter": 1}),
        ("mystery", {"project_id": pid, "mystery_id": "river-name", "question": "What does the river remember?", "truth": "The river remembers every name spoken at the third bell.", "status": "confirmed", "source_chapter": 1}),
    ]
    for source_type, owner in special_owners:
        for atomic in derive_atomic_documents(str(pid), source_type, owner):
            atomic_by_id[atomic["memory_id"]] = atomic
    atomics = list(atomic_by_id.values())
    indexed = []
    for atomic in atomics:
        indexed.append(_indexed(pid, "atomic_memory", atomic["memory_id"], atomic["content"], {**metadata_for_source("atomic_memory", atomic), "predicate": atomic.get("predicate"), "subject": atomic.get("subject"), "compact_value": atomic.get("compact_value")}))
    for intelligence in episodes:
        indexed.append(_indexed(pid, "chapter_intelligence", intelligence["intelligence_id"], episode_text(intelligence), metadata_for_source("chapter_intelligence", intelligence)))
    return atomics, episodes, indexed


async def _scale(db, chapters: int) -> dict:
    pid = ObjectId(); atomics, episodes, indexed = _seed(pid, chapters)
    for start in range(0, len(indexed), 1000):
        await db.memory_embeddings.insert_many(indexed[start:start + 1000])
    queries = [
        (f"Asterlock-{chapters} drowned archive", f"Asterlock-{chapters}"),
        ("silent bell dormant marker", "silent bell"),
        ("Who owns Northglass?", "Ivo"),
        ("current trust between Mara and Ivo", "cautiously trusts"),
        ("current injury on Mara's hand", "pale scar"),
        ("what water remembers third chime", "river remembers"),
        ("Elias alive eastern tower", None),
    ]
    rows = []
    for query, expected in queries:
        started = time.perf_counter()
        hits = await retrieve_relevant_context(db, str(pid), query, top_k=8, safe_for_writing=True, consumer="phase_b_scale", as_of_chapter=chapters, pov_character="Mara")
        latency = (time.perf_counter() - started) * 1000
        ranks = [rank for rank, hit in enumerate(hits, 1) if expected and expected.lower() in str(hit.get("content") or "").lower()]
        rows.append({"query": query, "expected": expected, "matched": None if expected is None else bool(ranks), "rank": ranks[0] if ranks else None, "latency_ms": round(latency, 3), "duplicate_logical_hits": len(hits) - len({str(hit.get("logical_identity")) for hit in hits}), "future_leakage": sum(1 for hit in hits if int((hit.get("metadata") or {}).get("valid_from_chapter") or 0) > chapters), "knowledge_leakage": sum(1 for hit in hits if "mara" in [str(value).lower() for value in (hit.get("metadata") or {}).get("not_known_by") or []])})
    labelled = [row for row in rows if row["matched"] is not None]
    latencies = sorted(row["latency_ms"] for row in rows)
    return {
        "chapters": chapters, "atomic_records": len(atomics), "episode_records": len(episodes), "indexed_records": len(indexed),
        "atomic_per_chapter": round(len(atomics) / chapters, 3), "episode_bytes_per_chapter": round(sum(len(BSON.encode(item)) for item in episodes) / chapters, 1),
        "atomic_storage_bytes": sum(len(BSON.encode(item)) for item in atomics), "episode_storage_bytes": sum(len(BSON.encode(item)) for item in episodes),
        "recall_at_8": round(statistics.mean(1.0 if row["matched"] else 0.0 for row in labelled), 4),
        "mrr": round(statistics.mean(1.0 / row["rank"] if row["rank"] else 0.0 for row in labelled), 4),
        "retrieval_p50_ms": round(statistics.median(latencies), 3), "retrieval_p95_ms": latencies[-1],
        "duplicate_logical_hits": sum(row["duplicate_logical_hits"] for row in rows), "future_leakage": sum(row["future_leakage"] for row in rows), "knowledge_leakage": sum(row["knowledge_leakage"] for row in rows), "queries": rows,
    }


async def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    name = f"nf_phase_b_{uuid4().hex}"
    client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
    removed = False
    try:
        await client.admin.command("ping"); db = client[name]
        scales = [await _scale(db, value) for value in SCALES]
        await client.drop_database(name); removed = True
        payload = {"schema_version": 1, "provider_calls": 0, "derivation_version": 1, "temporary_database": name, "temporary_database_removed": True, "scales": scales}
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps({"output": str(args.output), "provider_calls": 0}, indent=2))
    finally:
        if not removed: await client.drop_database(name)
        client.close()


if __name__ == "__main__": asyncio.run(main())
