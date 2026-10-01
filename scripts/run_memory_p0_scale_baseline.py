"""Run provider-free Native retrieval baselines at 10-500 chapters.

The script creates one uniquely named temporary Mongo database, seeds labelled
derived records, compares the legacy capped ranker with the current safe
ranker, writes JSON, and drops only that exact temporary database.
"""
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

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.services.memory_retrieval_service import (  # noqa: E402
    _cosine,
    embed_text,
    narrative_relevance_score,
    retrieve_relevant_context,
)


SCALES = (10, 25, 50, 100, 250, 500)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--output", type=Path, required=True)
    return value


def record(
    pid: ObjectId,
    source_type: str,
    source_id: str,
    content: str,
    *,
    version: int = 1,
    metadata: dict | None = None,
) -> dict:
    return {
        "project_id": pid,
        "source_type": source_type,
        "source_id": source_id,
        "source_version": version,
        "active": True,
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content": content,
        "embedding": embed_text(content),
        "metadata": metadata or {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


def seed_documents(pid: ObjectId, chapters: int) -> list[dict]:
    documents: list[dict] = []
    for chapter in range(1, chapters + 1):
        documents.extend([
            record(pid, "chapter_intelligence", f"chapter-{chapter}", f"Chapter {chapter}: controlled event sequence and consequence {chapter}.", metadata={"logical_source_id": f"chapter-{chapter}", "owner_source_version": 1, "chapter_number": chapter, "valid_from_chapter": chapter}),
            record(pid, "plot_thread", f"thread-{chapter}", f"Plot thread {chapter} remains open under controlled pressure.", metadata={"status": "open", "valid_from_chapter": chapter}),
            record(pid, "world", f"world-{chapter}", f"World observation {chapter}: the numbered district follows rule {chapter}.", metadata={"valid_from_chapter": chapter}),
            record(pid, "foreshadow_v2", f"promise-{chapter}", f"Promise {chapter} waits for a later payoff.", metadata={"valid_from_chapter": chapter}),
            record(pid, "scene", f"scene-{chapter}", f"Scene {chapter} links cause {chapter} to consequence {chapter}.", metadata={"valid_from_chapter": chapter}),
        ])

    midpoint = max(3, chapters // 2)
    documents.extend([
        record(pid, "artifact", "northglass-owner", "Northglass belongs to Mara.", version=1, metadata={"logical_source_id": "northglass-owner", "owner_source_version": 1, "authority_status": "approved", "authority_level": "confirmed_planning", "valid_from_chapter": 1, "valid_to_chapter": midpoint - 1}),
        record(pid, "artifact", "northglass-owner", "Northglass belongs to Ivo.", version=2, metadata={"logical_source_id": "northglass-owner", "owner_source_version": 2, "authority_status": "approved", "authority_level": "confirmed_planning", "valid_from_chapter": midpoint}),
        record(pid, "relationship", "mara-ivo", "Mara distrusts Ivo.", version=1, metadata={"logical_source_id": "mara-ivo", "owner_source_version": 1, "authority_status": "confirmed", "authority_level": "confirmed_planning", "valid_from_chapter": 1, "valid_to_chapter": midpoint - 1}),
        record(pid, "relationship", "mara-ivo", "Mara cautiously trusts Ivo.", version=2, metadata={"logical_source_id": "mara-ivo", "owner_source_version": 2, "authority_status": "confirmed", "authority_level": "confirmed_planning", "valid_from_chapter": midpoint}),
        record(pid, "character_progression", "mara-injury", "Mara's left palm was cut and painful.", version=1, metadata={"logical_source_id": "mara-injury", "owner_source_version": 1, "authority_status": "approved", "authority_level": "confirmed_planning", "valid_from_chapter": 2, "valid_to_chapter": midpoint - 1}),
        record(pid, "character_progression", "mara-injury", "Mara's left palm has healed, leaving a pale scar.", version=2, metadata={"logical_source_id": "mara-injury", "owner_source_version": 2, "authority_status": "approved", "authority_level": "confirmed_planning", "valid_from_chapter": midpoint}),
        record(pid, "mystery", "river-name", "The river remembers every name spoken at the third bell.", metadata={"authority_status": "confirmed", "authority_level": "confirmed_planning", "valid_from_chapter": 1}),
        record(pid, "plot_thread", "dormant-callback", "Dormant callback: the silent bell from Chapter 1 must ring again.", metadata={"status": "open", "valid_from_chapter": 1}),
        record(pid, "knowledge", "private-elias", "Elias is alive in the eastern tower.", metadata={"authority_status": "confirmed", "valid_from_chapter": midpoint, "known_by": ["Ivo"], "not_known_by": ["Mara"]}),
        record(pid, "knowledge", "future-trap", "The Queen is unmasked after the current manuscript boundary.", metadata={"authority_status": "confirmed", "valid_from_chapter": chapters + 5, "known_by": ["Ivo"]}),
        record(pid, "timeline", "rejected-villain", "Maybe Elias is secretly the villain.", metadata={"status": "rejected"}),
        record(pid, "character", "candidate-villain", "Candidate: Elias is secretly the villain.", metadata={"authority_status": "candidate"}),
        record(pid, "chapter_intelligence", "revision-physical-a", "Revised chapter memory: the funeral precedes the river search.", metadata={"logical_source_id": "revision-logical", "owner_source_version": 2, "chapter_number": 1}),
        record(pid, "chapter_intelligence", "revision-logical", "Chapter revision: the funeral precedes the river search.", metadata={"logical_source_id": "revision-logical", "owner_source_version": 2, "chapter_number": 1}),
        # Deliberately last: legacy first-2,000 retrieval misses this at scale.
        record(pid, "artifact", f"asterlock-{chapters}", f"Rare artifact Asterlock-{chapters} opens the drowned archive.", metadata={"authority_status": "approved", "authority_level": "confirmed_planning", "valid_from_chapter": chapters}),
    ])
    return documents


def logical_key(document: dict) -> str:
    metadata = document.get("metadata") or {}
    return f"{document.get('source_type')}:{metadata.get('logical_source_id') or document.get('source_id')}:v{metadata.get('owner_source_version') or document.get('source_version') or 1}"


async def legacy_retrieve(db, pid: ObjectId, query: str, top_k: int = 8) -> tuple[list[dict], float]:
    started = time.perf_counter()
    # This intentionally preserves the audited V1 limit and exact-content-only
    # deduplication for a truthful same-corpus before measurement.
    sources = await db.memory_embeddings.find(
        {"project_id": pid, "active": {"$ne": False}}
    ).to_list(length=2000)
    query_vector = embed_text(query)
    scored = []
    seen_content: set[str] = set()
    for source in sources:
        content = str(source.get("content") or "")
        content_key = content.strip().lower()
        if content_key in seen_content:
            continue
        seen_content.add(content_key)
        base = _cosine(query_vector, source.get("embedding") or [])
        scored.append({**source, "score": narrative_relevance_score(query, source, base)})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k], round((time.perf_counter() - started) * 1000, 3)


def metrics(rows: list[dict], expected_id: str | None, expected_text: str | None, latency_ms: float, chapters: int) -> dict:
    ranks = [
        index for index, row in enumerate(rows, 1)
        if expected_id
        and str(row.get("source_id")) == expected_id
        and (not expected_text or expected_text.lower() in str(row.get("content") or "").lower())
    ]
    statuses = {
        "candidate", "rejected", "reconsidered", "stale", "superseded", "inactive",
    }
    leakage = 0
    future_leakage = 0
    character_knowledge_leakage = 0
    for row in rows:
        metadata = row.get("metadata") or {}
        values = {str(metadata.get(key) or row.get(key) or "").lower() for key in ("status", "authority_status", "approval_status")}
        if values & statuses:
            leakage += 1
        valid_from = metadata.get("valid_from_chapter")
        if valid_from is not None and int(valid_from) > chapters:
            future_leakage += 1
        known_by = {str(value).lower() for value in metadata.get("known_by") or []}
        not_known_by = {str(value).lower() for value in metadata.get("not_known_by") or []}
        if "mara" in not_known_by or (known_by and "mara" not in known_by):
            character_knowledge_leakage += 1
    keys = [logical_key(row) for row in rows]
    return {
        "recall_at_k": (1.0 if ranks else 0.0) if expected_id else None,
        "mrr": (1.0 / ranks[0] if ranks else 0.0) if expected_id else None,
        "leakage": leakage,
        "future_knowledge_leakage": future_leakage,
        "character_knowledge_leakage": character_knowledge_leakage,
        "duplicate_logical_hits": len(keys) - len(set(keys)),
        "retrieved_tokens": sum(max(1, len(str(row.get("content") or "")) // 4) for row in rows),
        "latency_ms": latency_ms,
        "selected_source_ids": [str(row.get("source_id") or "") for row in rows],
    }


async def run_scale(db, chapters: int) -> dict:
    pid = ObjectId()
    docs = seed_documents(pid, chapters)
    for start in range(0, len(docs), 1000):
        await db.memory_embeddings.insert_many(docs[start:start + 1000])
    queries = [
        (f"Asterlock-{chapters} drowned archive", f"asterlock-{chapters}", "opens the drowned archive"),
        ("silent bell dormant callback", "dormant-callback", "silent bell"),
        ("Who owns Northglass now?", "northglass-owner", "belongs to Ivo"),
        ("current trust between Mara and Ivo", "mara-ivo", "cautiously trusts"),
        ("current injury on Mara's hand", "mara-injury", "has healed"),
        ("what water remembers when the third chime sounds", "river-name", "remembers every name"),
        ("Could Elias secretly be the villain?", None, None),
        ("Elias alive eastern tower Queen unmasked", None, None),
    ]
    before_rows = []
    after_rows = []
    for query, expected, expected_text in queries:
        legacy, legacy_latency = await legacy_retrieve(db, pid, query)
        before_rows.append({"query": query, "expected_source_id": expected, "expected_text": expected_text, **metrics(legacy, expected, expected_text, legacy_latency, chapters)})
        started = time.perf_counter()
        current = await retrieve_relevant_context(
            db, str(pid), query, top_k=8, refresh_index=False,
            safe_for_writing=True, consumer="scale_replay",
            as_of_chapter=chapters, pov_character="Mara",
        )
        current_latency = round((time.perf_counter() - started) * 1000, 3)
        after_rows.append({"query": query, "expected_source_id": expected, "expected_text": expected_text, **metrics(current, expected, expected_text, current_latency, chapters)})

    def aggregate(rows: list[dict]) -> dict:
        latencies = [row["latency_ms"] for row in rows]
        labelled = [row for row in rows if row["recall_at_k"] is not None]
        return {
            "recall_at_k": round(statistics.mean(row["recall_at_k"] for row in labelled), 4),
            "mrr": round(statistics.mean(row["mrr"] for row in labelled), 4),
            "leakage": sum(row["leakage"] for row in rows),
            "future_knowledge_leakage": sum(row["future_knowledge_leakage"] for row in rows),
            "character_knowledge_leakage": sum(row["character_knowledge_leakage"] for row in rows),
            "duplicate_logical_hits": sum(row["duplicate_logical_hits"] for row in rows),
            "retrieved_tokens": sum(row["retrieved_tokens"] for row in rows),
            "retrieval_p50_ms": round(statistics.median(latencies), 3),
            "retrieval_p95_ms": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 3),
            "queries": rows,
        }

    before = aggregate(before_rows)
    after = aggregate(after_rows)
    return {
        "chapters": chapters,
        "seeded_records": len(docs),
        "before": before,
        "after": after,
        "result": "PASS" if (
            after["leakage"] == 0
            and after["future_knowledge_leakage"] == 0
            and after["character_knowledge_leakage"] == 0
            and after["duplicate_logical_hits"] == 0
        ) else "REGRESSION",
    }


async def main() -> None:
    args = parser().parse_args()
    database_name = f"novelforge_memory_p0_scale_{uuid4().hex}"
    client = AsyncIOMotorClient(
        settings.mongodb_url,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    dropped = False
    try:
        await client.admin.command("ping")
        db = client[database_name]
        results = [await run_scale(db, chapters) for chapters in SCALES]
        await client.drop_database(database_name)
        dropped = True
        payload = {
            "schema_version": 1,
            "provider_calls": 0,
            "temporary_database": database_name,
            "temporary_database_removed": True,
            "scales": results,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps({"output": str(args.output), "provider_calls": 0}, indent=2))
    finally:
        # The exact database name is generated above and never derived from an
        # environment variable or workspace database setting.
        if not dropped:
            await client.drop_database(database_name)
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
