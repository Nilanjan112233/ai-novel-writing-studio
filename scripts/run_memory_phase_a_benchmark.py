"""Provider-free Phase A rebuild, retrieval, scale, and mutation benchmark."""
from __future__ import annotations

import argparse
import asyncio
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
from app.migrations.memory_phase_a import migrate_memory_phase_a  # noqa: E402
from app.services.memory_incremental_index_service import memory_incremental_index_service  # noqa: E402
from app.services.memory_retrieval_policy import SOURCE_ID_FIELDS  # noqa: E402
from app.services.memory_retrieval_service import SOURCE_SPECS, retrieve_relevant_context  # noqa: E402

SCALES = (10, 25, 50, 100, 250, 500)


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--output", type=Path, required=True)
    value.add_argument("--scales", default="10,25,50,100,250,500")
    return value


def _p95(values):
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, int(len(ordered) * .95) - 1))]


def owner(pid, source_type, source_id, content, *, version=1, **metadata):
    collection, fields = SOURCE_SPECS[source_type]
    row = {
        "_id": ObjectId(), "project_id": pid,
        "version_number": version, "source_version": version,
        "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
        **metadata,
    }
    id_fields = SOURCE_ID_FIELDS.get(source_type) or ()
    if id_fields:
        row[id_fields[0]] = source_id
    else:
        row["source_id"] = source_id
    row[fields[0]] = content
    return collection, row


def seed_owners(pid, chapters):
    rows = []
    for chapter in range(1, chapters + 1):
        rows.extend([
            owner(pid, "chapter_intelligence", f"chapter-{chapter}", f"Chapter {chapter}: controlled event sequence and consequence {chapter}.", chapter_number=chapter, active=True),
            owner(pid, "plot_thread", f"thread-{chapter}", f"Plot thread {chapter} remains open under controlled pressure.", chapter_number=chapter, status="open"),
            owner(pid, "world", f"world-{chapter}", f"World observation {chapter}: the numbered district follows rule {chapter}.", chapter_number=chapter),
            owner(pid, "foreshadow_v2", f"promise-{chapter}", f"Promise {chapter} waits for a later payoff.", chapter_number=chapter, status="open"),
            owner(pid, "scene", f"scene-{chapter}", f"Scene {chapter} links cause {chapter} to consequence {chapter}.", chapter_number=chapter),
        ])
    midpoint = max(3, chapters // 2)
    rows.extend([
        owner(pid, "artifact", "northglass-owner", "Northglass belongs to Mara.", version=1, authority_status="approved", valid_from_chapter=1, valid_to_chapter=midpoint - 1),
        owner(pid, "artifact", "northglass-owner", "Northglass belongs to Ivo.", version=2, authority_status="approved", valid_from_chapter=midpoint),
        owner(pid, "relationship", "mara-ivo", "Mara distrusts Ivo.", version=1, authority_status="confirmed", valid_from_chapter=1, valid_to_chapter=midpoint - 1),
        owner(pid, "relationship", "mara-ivo", "Mara cautiously trusts Ivo.", version=2, authority_status="confirmed", valid_from_chapter=midpoint),
        owner(pid, "character_progression", "mara-injury", "Mara's left palm was cut and painful.", version=1, authority_status="approved", valid_from_chapter=2, valid_to_chapter=midpoint - 1),
        owner(pid, "character_progression", "mara-injury", "Mara's left palm has healed, leaving a pale scar.", version=2, authority_status="approved", valid_from_chapter=midpoint),
        owner(pid, "mystery", "river-name", "The river remembers every name spoken at the third bell.", authority_status="confirmed", valid_from_chapter=1, status="open"),
        owner(pid, "plot_thread", "dormant-callback", "Dormant callback: the silent bell from Chapter 1 must ring again.", status="open", valid_from_chapter=1, authority_status="confirmed"),
        owner(pid, "knowledge", "private-elias", "Elias is alive in the eastern tower.", authority_status="confirmed", valid_from_chapter=midpoint, known_by=["Ivo"], not_known_by=["Mara"]),
        owner(pid, "knowledge", "future-trap", "The Queen is unmasked after the current manuscript boundary.", authority_status="confirmed", valid_from_chapter=chapters + 5, known_by=["Ivo"]),
        owner(pid, "timeline", "rejected-villain", "Maybe Elias is secretly the villain.", status="rejected"),
        owner(pid, "character", "candidate-villain", "Candidate: Elias is secretly the villain.", authority_status="candidate"),
        owner(pid, "chapter_intelligence", "revision-logical", "Revised chapter memory: the funeral precedes the river search.", version=2, chapter_number=1, active=True),
        owner(pid, "chapter_intelligence", "revision-logical", "Chapter revision: the funeral precedes the river search.", version=2, chapter_number=1, active=True),
        owner(pid, "artifact", f"asterlock-{chapters}", f"Rare artifact Asterlock-{chapters} opens the drowned archive.", authority_status="approved", valid_from_chapter=chapters),
    ])
    return rows


QUERIES = (
    (lambda n: f"Asterlock-{n} drowned archive", lambda n: f"asterlock-{n}", "opens the drowned archive"),
    (lambda n: "silent bell dormant callback", lambda n: "dormant-callback", "silent bell"),
    (lambda n: "Who owns Northglass now?", lambda n: "northglass-owner", "belongs to Ivo"),
    (lambda n: "current trust between Mara and Ivo", lambda n: "mara-ivo", "cautiously trusts"),
    (lambda n: "current injury on Mara's hand", lambda n: "mara-injury", "has healed"),
    (lambda n: "what water remembers when the third chime sounds", lambda n: "river-name", "remembers every name"),
)


async def insert_seed(db, pid, chapters):
    rows = seed_owners(pid, chapters)
    await db.projects.insert_one({"_id": pid, "title": f"Scale {chapters}", "premise": "Controlled Phase A scale corpus."})
    grouped = {}
    for collection, row in rows:
        grouped.setdefault(collection, []).append(row)
    for collection, documents in grouped.items():
        for offset in range(0, len(documents), 1000):
            await db[collection].insert_many(documents[offset:offset + 1000])
    return len(rows) + 1


async def retrieve_once(db, pid, chapters, query):
    status_start = time.perf_counter()
    status = await memory_incremental_index_service.get_status(db, str(pid))
    checkpoint_ms = (time.perf_counter() - status_start) * 1000
    diagnostics = {}
    started = time.perf_counter()
    hits = await retrieve_relevant_context(
        db, str(pid), query, top_k=8, safe_for_writing=True,
        consumer="phase_a_scale", as_of_chapter=chapters, pov_character="Mara",
        index_revision=status["processed_version"], resolve_legacy_aliases=False,
        diagnostics=diagnostics,
    )
    return hits, (time.perf_counter() - started) * 1000, checkpoint_ms, diagnostics


def safety(hits, chapters):
    bad = {"candidate", "rejected", "reconsidered", "stale", "superseded", "inactive"}
    leakage = future = knowledge = 0
    keys = []
    for hit in hits:
        meta = hit.get("metadata") or {}
        statuses = {str(meta.get(key) or "").lower() for key in ("status", "authority_status", "approval_status")}
        leakage += int(bool(statuses & bad))
        valid_from = meta.get("valid_from_chapter")
        future += int(valid_from is not None and int(valid_from) > chapters)
        known = {str(v).lower() for v in meta.get("known_by") or []}
        unknown = {str(v).lower() for v in meta.get("not_known_by") or []}
        knowledge += int("mara" in unknown or bool(known and "mara" not in known))
        keys.append(hit.get("logical_identity"))
    return leakage, future, knowledge, len(keys) - len(set(keys))


async def mutation_workload(db, pid, chapters):
    workloads = []

    async def perform(label, source_type, document, operation):
        collection = SOURCE_SPECS[source_type][0]
        await db[collection].insert_one(document)
        event = await memory_incremental_index_service.enqueue_change(
            db, str(pid), source_type=source_type, operation=operation,
            physical_source_id=str(document["_id"]), event_key=f"mutation:{label}",
        )
        result = await memory_incremental_index_service.process_pending(db, str(pid), limit=8)
        workloads.append({"mutation": label, "event": event, **result})

    collection, chapter = owner(pid, "chapter_intelligence", "chapter-501", "Chapter 501: Asterlock opens the archive.", chapter_number=501, active=True)
    await perform("approve_chapter_501", "chapter_intelligence", chapter, "approve")
    collection, relationship = owner(pid, "relationship", "mara-lindon-new", "Mara and Lindon are confirmed allies.", authority_status="confirmed")
    await perform("modify_relationship", "relationship", relationship, "update")
    collection, decision = owner(pid, "decision", "planning-501", "Elias disappeared five years ago.", status="confirmed")
    await perform("confirm_planning", "decision", decision, "confirm")
    collection, rejected = owner(pid, "character", "rejected-501", "Maybe Mara abandons the city.", authority_status="rejected")
    await perform("reject_candidate", "character", rejected, "reject")
    collection, artifact = owner(pid, "artifact", "northglass-owner", "Northglass is transferred to Mara's archive.", version=3, authority_status="approved", valid_from_chapter=501)
    await perform("change_artifact_ownership", "artifact", artifact, "update")
    collection, revision = owner(pid, "chapter_intelligence", "chapter-250", "Revised Chapter 250: the funeral now precedes the crossing.", version=2, chapter_number=250, active=True)
    await perform("revise_approved_chapter", "chapter_intelligence", revision, "revision_apply")
    unchanged_event = await memory_incremental_index_service.enqueue_change(
        db, str(pid), source_type="chapter_intelligence", operation="refresh",
        physical_source_id=str(revision["_id"]), event_key="mutation:regenerate-unchanged-intelligence",
    )
    unchanged_result = await memory_incremental_index_service.process_pending(db, str(pid), limit=8)
    workloads.append({"mutation": "regenerate_unchanged_intelligence", "event": unchanged_event, **unchanged_result})
    return workloads


async def run_scale(db, chapters):
    pid = ObjectId()
    seeded = await insert_seed(db, pid, chapters)
    rebuild = await memory_incremental_index_service.rebuild(db, str(pid), resume=False)
    cold_query = f"Asterlock-{chapters} drowned archive"
    _cold_hits, cold_ms, cold_checkpoint_ms, cold_diag = await retrieve_once(db, pid, chapters, cold_query)
    labelled = []
    retrieval_latencies = []
    checkpoint_latencies = [cold_checkpoint_ms]
    all_leakage = [0, 0, 0, 0]
    diagnostics = []
    for query_fn, expected_fn, expected_text in QUERIES:
        query = query_fn(chapters)
        hits, latency, checkpoint_ms, diag = await retrieve_once(db, pid, chapters, query)
        retrieval_latencies.append(latency)
        checkpoint_latencies.append(checkpoint_ms)
        diagnostics.append(diag)
        ranks = [i for i, hit in enumerate(hits, 1) if hit.get("source_id") == expected_fn(chapters) and expected_text.lower() in hit.get("content", "").lower()]
        labelled.append({
            "query": query, "found": bool(ranks), "rank": ranks[0] if ranks else None,
            "selected_source_ids": [hit.get("source_id") for hit in hits],
        })
        values = safety(hits, chapters)
        all_leakage = [a + b for a, b in zip(all_leakage, values)]
    # Add repeated warm reads so latency percentiles do not combine indexing.
    for iteration in range(18):
        query = QUERIES[iteration % len(QUERIES)][0](chapters)
        _hits, latency, checkpoint_ms, _diag = await retrieve_once(db, pid, chapters, query)
        retrieval_latencies.append(latency)
        checkpoint_latencies.append(checkpoint_ms)
    mutation = await mutation_workload(db, pid, chapters) if chapters == 500 else []
    recovery = None
    if chapters in {100, 500}:
        interrupted = await memory_incremental_index_service.rebuild(db, str(pid), resume=False, interrupt_after_sources=3)
        resumed = await memory_incremental_index_service.rebuild(db, str(pid), resume=True)
        recovery = {"interrupted": interrupted, "resumed": resumed}
    return {
        "chapters": chapters,
        "seeded_records": seeded,
        "rebuild": rebuild,
        "cold_retrieval_ms": round(cold_ms, 3),
        "cold_diagnostics": cold_diag,
        "retrieval_p50_ms": round(statistics.median(retrieval_latencies), 3),
        "retrieval_p95_ms": round(_p95(retrieval_latencies), 3),
        "checkpoint_p50_ms": round(statistics.median(checkpoint_latencies), 3),
        "checkpoint_p95_ms": round(_p95(checkpoint_latencies), 3),
        "recall_at_8": round(sum(item["found"] for item in labelled) / len(labelled), 4),
        "mrr": round(sum((1 / item["rank"]) if item["rank"] else 0 for item in labelled) / len(labelled), 4),
        "safety": {
            "candidate_rejected_leakage": all_leakage[0], "future_leakage": all_leakage[1],
            "pov_knowledge_leakage": all_leakage[2], "duplicate_logical_hits": all_leakage[3],
        },
        "full_source_scans_per_query": max(item.get("full_source_scans_query", 0) for item in diagnostics),
        "owner_records_inspected_per_query": max(item.get("owner_records_inspected_query", 0) for item in diagnostics),
        "index_writes_per_query": max(item.get("index_writes_query", 0) for item in diagnostics),
        "labelled_queries": labelled,
        "mutations": mutation,
        "recovery": recovery,
    }


async def main():
    args = parser().parse_args()
    db_name = f"novelforge_memory_phase_a_{uuid4().hex}"
    client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
    dropped = False
    try:
        await client.admin.command("ping")
        db = client[db_name]
        await migrate_memory_phase_a(db)
        selected_scales = tuple(int(value.strip()) for value in args.scales.split(",") if value.strip())
        if not selected_scales or any(value not in SCALES for value in selected_scales):
            raise ValueError(f"scales must be selected from {SCALES}")
        scales = [await run_scale(db, chapters) for chapters in selected_scales]
        await client.drop_database(db_name)
        dropped = True
        payload = {
            "schema_version": 1, "phase": "A", "provider_calls": 0,
            "temporary_database": db_name, "temporary_database_removed": True,
            "scales": scales,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        print(json.dumps({"output": str(args.output), "provider_calls": 0, "scales": list(selected_scales)}, indent=2))
    finally:
        if not dropped:
            await client.drop_database(db_name)
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
