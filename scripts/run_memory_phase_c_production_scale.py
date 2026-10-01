"""Provider-free production-path Phase C scale benchmark."""
from __future__ import annotations

import asyncio
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from bson import BSON, ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.migrations.memory_phase_c import migrate_memory_phase_c  # noqa: E402
from app.services.memory_phase_c_ranker import PHASE_C_RANKER_VERSION  # noqa: E402
from app.services.memory_phase_c_service import memory_phase_c_service  # noqa: E402
from app.services.memory_provider import NativeNovelForgeMemoryProvider  # noqa: E402
from app.services.memory_retrieval_service import index_memory  # noqa: E402
from scripts.run_memory_phase_c_bakeoff import _documents, _queries  # noqa: E402

SCALES = (10, 25, 50, 100, 250, 500)


def _percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int((len(ordered) - 1) * p)))] if ordered else 0.0


async def _run_scale(db, chapters: int) -> dict[str, Any]:
    await db.memory_embeddings.delete_many({})
    await db.memory_index_checkpoints.delete_many({})
    await db.memory_phase_c_checkpoints.delete_many({})
    pid = ObjectId()
    documents = _documents(chapters)
    lexical_bytes = 0
    total_bytes = 0
    for row in documents:
        row = dict(row); row.pop("_id", None); row["project_id"] = pid; row["active"] = True
        lexical = {key: row.get(key) for key in ("search_terms", "term_frequencies", "document_length", "phase_c_ranker_version")}
        lexical_bytes += len(BSON.encode(lexical)); total_bytes += len(BSON.encode(row))
        await db.memory_embeddings.insert_one(row)
    await db.memory_index_checkpoints.insert_one({
        "project_id": pid, "status": "READY", "index_complete": True,
        "processed_version": 1, "authority_state_version": 1,
        "pending_updates": 0, "failed_updates": 0,
    })
    await db.memory_phase_c_checkpoints.insert_one({
        "project_id": pid, "status": "READY", "complete": True,
        "ranker_version": PHASE_C_RANKER_VERSION, "processed_version": 1,
        "indexed_records": len(documents),
    })
    provider = NativeNovelForgeMemoryProvider(db)
    cold_latencies: list[float] = []; warm_latencies: list[float] = []
    case_results = []
    relevant = reciprocal = precision = unsafe = duplicates = 0.0
    scored: list[int] = []; candidate_counts: list[int] = []; context_tokens: list[int] = []
    cases = _queries(chapters)
    for repeat in range(3):
        for case in cases:
            start = time.perf_counter()
            recall = await provider.recall(
                project_id=str(pid), query=case["q"], top_k=8,
                retrieval_context={
                    "safe_for_writing": case.get("safe", True), "consumer": "phase_c_production_scale",
                    "as_of_chapter": case.get("as_of"), "pov_character": case.get("pov"),
                },
            )
            elapsed = (time.perf_counter() - start) * 1000
            (warm_latencies if repeat else cold_latencies).append(elapsed)
            ids = [str(hit.metadata.get("logical_identity") or "") for hit in recall.hits]
            positions = [
                i + 1 for i, hit in enumerate(recall.hits)
                if case.get("expected")
                and (
                    str(case["expected"]).lower() in str(hit.metadata.get("logical_identity") or "").lower()
                    or str(case["expected"]).lower() in hit.content.lower()
                )
                and (not case.get("contains") or case["contains"] in hit.content)
            ]
            success = not case.get("expected") or bool(positions)
            forbidden = case.get("forbidden")
            leaked = bool(forbidden and any(str(forbidden) in item for item in ids))
            if repeat == 0:
                relevant += float(success); reciprocal += (1.0 / positions[0]) if positions else (1.0 if not case.get("expected") else 0.0)
                precision += (1.0 / max(1, len(recall.hits))) if positions else 0.0
                unsafe += float(leaked)
                logical = [hit.metadata.get("logical_identity") for hit in recall.hits]
                duplicates += float(len(logical) != len(set(logical)))
                scored.append(int(recall.diagnostics.get("embedding_records_scored") or 0))
                candidate_counts.append(int(recall.diagnostics.get("candidate_count") or 0))
                context_tokens.append(recall.token_estimate)
                case_results.append({"id": case["id"], "first_relevant_rank": positions[0] if positions else None, "hits": ids, "records_scored": scored[-1], "latency_ms": round(elapsed, 3), "strategy": recall.strategy, "fallback_reason": recall.diagnostics.get("fallback_reason")})
    count = len(cases)
    stats = await db.command("collStats", "memory_embeddings")
    return {
        "chapters": chapters, "records": len(documents),
        "recall_at_8": round(relevant / count, 4), "mrr": round(reciprocal / count, 4),
        "precision_at_8": round(precision / count, 4),
        "p50_ms": round(statistics.median(cold_latencies), 3), "p95_ms": round(_percentile(cold_latencies, .95), 3),
        "warm_p50_ms": round(statistics.median(warm_latencies), 3), "warm_p95_ms": round(_percentile(warm_latencies, .95), 3),
        "mean_candidates": round(statistics.mean(candidate_counts), 2), "mean_records_scored": round(statistics.mean(scored), 2),
        "mean_context_tokens": round(statistics.mean(context_tokens), 2),
        "unsafe_leakage": int(unsafe), "duplicate_logical_hits": int(duplicates),
        "lexical_document_bytes": lexical_bytes, "total_document_bytes": total_bytes,
        "allocated_index_bytes": int(stats.get("totalIndexSize") or 0),
        "cases": case_results,
    }


async def main():
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[f"{settings.database_name}_phase_c_benchmark"]
    try:
        await db.drop_collection("memory_embeddings"); await db.drop_collection("memory_index_checkpoints"); await db.drop_collection("memory_phase_c_checkpoints")
        await migrate_memory_phase_c(db)
        results = [await _run_scale(db, scale) for scale in SCALES]
        await db.memory_embeddings.drop_index("memory_phase_c_lexical_terms")
        index_started = time.perf_counter(); await migrate_memory_phase_c(db)
        startup_index_build_ms = (time.perf_counter() - index_started) * 1000
        sample = await db.memory_embeddings.find_one({"active": True})
        mutation_latencies = []
        original_content = str(sample.get("content") or "")
        for index in range(20):
            mutation_started = time.perf_counter()
            await index_memory(
                db, project_id=str(sample["project_id"]), source_type=sample["source_type"],
                source_id=sample["source_id"], source_version=int(sample.get("source_version") or 1),
                physical_source_id=str((sample.get("metadata") or {}).get("physical_source_id") or sample["source_id"]),
                content=original_content + (" mutation-a" if index % 2 else " mutation-b"), metadata=sample.get("metadata") or {},
            )
            mutation_latencies.append((time.perf_counter() - mutation_started) * 1000)
        unchanged_started = time.perf_counter()
        unchanged = await index_memory(
            db, project_id=str(sample["project_id"]), source_type=sample["source_type"],
            source_id=sample["source_id"], source_version=int(sample.get("source_version") or 1),
            physical_source_id=str((sample.get("metadata") or {}).get("physical_source_id") or sample["source_id"]),
            content=original_content + " mutation-a", metadata=sample.get("metadata") or {},
        )
        unchanged_ms = (time.perf_counter() - unchanged_started) * 1000
        payload = {
            "provider_calls": 0, "ranker_version": PHASE_C_RANKER_VERSION, "results": results,
            "operational": {
                "startup_index_build_500_ms": round(startup_index_build_ms, 3),
                "single_mutation_p50_ms": round(statistics.median(mutation_latencies), 3),
                "single_mutation_p95_ms": round(_percentile(mutation_latencies, .95), 3),
                "unchanged_update_ms": round(unchanged_ms, 3), "unchanged_writes": int(unchanged.get("writes") or 0),
            },
        }
        output = ROOT / "artifacts" / "memory-phase-c" / "production-scale.json"; output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        print(json.dumps(payload, indent=2, default=str))
    finally:
        await client.drop_database(db.name); client.close()


if __name__ == "__main__": asyncio.run(main())
