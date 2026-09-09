"""Deterministic, provider-free replay and context-attribution diagnostics.

The replay service is deliberately observational.  It reads existing Native
memory/context records, calls the normal Native ranker with index refresh
disabled, and emits JSON-safe attribution.  It never calls a text-generation
provider and never promotes derived memory into story authority.
"""
from __future__ import annotations

import json
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List

from bson import ObjectId

from app.services.memory_retrieval_service import retrieve_relevant_context
from app.services.provider_gateway import estimate_tokens


STRICT_BAD_STATUSES = {
    "candidate", "suggested", "rejected", "reconsidered", "stale",
    "superseded", "archived", "inactive",
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str, ensure_ascii=True))


def _tokens(value: Any) -> int:
    return estimate_tokens(json.dumps(value, default=str, ensure_ascii=True))


def _status_values(document: Dict[str, Any]) -> set[str]:
    metadata = document.get("metadata") or {}
    values = {
        str(document.get(key) or "").strip().lower()
        for key in ("status", "authority_status", "candidate_status")
    }
    values.update(
        str(metadata.get(key) or "").strip().lower()
        for key in ("status", "authority_status", "candidate_status")
    )
    return {value for value in values if value}


def _logical_key(document: Dict[str, Any]) -> str:
    metadata = document.get("metadata") or {}
    logical_source = (
        metadata.get("logical_source_id")
        or metadata.get("intelligence_id")
        or document.get("source_id")
        or document.get("id")
        or ""
    )
    source_version = (
        metadata.get("owner_source_version")
        or metadata.get("source_version")
        or document.get("source_version")
        or 1
    )
    return f"{document.get('source_type') or 'memory'}:{logical_source}:v{source_version}"


@dataclass(slots=True)
class ReplayRequest:
    project_id: str
    query: str
    consumer: str = "discovery_writer"
    current_chapter: int | None = None
    current_scene: int | None = None
    pov_character: str | None = None
    branch_id: str | None = None
    top_k: int = 8
    expected_terms: List[str] = field(default_factory=list)
    context_packet_id: str | None = None
    label: str = ""
    respect_index_readiness: bool = False


class MemoryReplayService:
    async def _owner_identity(
        self,
        db,
        project_id: str,
        embedding: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resolve domain identity without changing the indexed document."""
        source_type = str(embedding.get("source_type") or "memory")
        source_id = str(embedding.get("source_id") or "")
        metadata = dict(embedding.get("metadata") or {})
        logical_source_id = str(metadata.get("logical_source_id") or source_id)
        owner_source_version = int(
            metadata.get("owner_source_version")
            or metadata.get("source_version")
            or embedding.get("source_version")
            or 1
        )
        owner_physical_id = str(metadata.get("physical_source_id") or source_id)
        owner: Dict[str, Any] | None = None

        if source_type == "chapter_intelligence":
            clauses: list[Dict[str, Any]] = [{"intelligence_id": source_id}]
            if ObjectId.is_valid(source_id):
                clauses.append({"_id": ObjectId(source_id)})
            owner = await db.chapter_intelligence.find_one(
                {"project_id": ObjectId(project_id), "$or": clauses}
            )
            if owner:
                logical_source_id = str(owner.get("intelligence_id") or source_id)
                owner_physical_id = str(owner.get("_id") or owner_physical_id)
                owner_source_version = int(
                    owner.get("version_number")
                    or owner.get("source_version")
                    or owner_source_version
                )

        return {
            "logical_source_id": logical_source_id,
            "logical_identity": f"{source_type}:{logical_source_id}:v{owner_source_version}",
            "owner_source_version": owner_source_version,
            "owner_physical_id": owner_physical_id,
            "owner_authority_status": (owner or {}).get("authority_status"),
            "owner_status": (owner or {}).get("status"),
            "owner_chapter": (owner or {}).get("chapter_number"),
            "owner_provenance": (owner or {}).get("provenance"),
        }

    async def _context_packet(
        self,
        db,
        request: ReplayRequest,
        replayed_hits: List[Dict[str, Any]],
    ) -> Dict[str, Any] | None:
        query: Dict[str, Any] = {"project_id": ObjectId(request.project_id)}
        if request.context_packet_id and ObjectId.is_valid(request.context_packet_id):
            query["_id"] = ObjectId(request.context_packet_id)
        row = await db.context_packets.find_one(query, sort=[("created_at", -1)])
        if not row:
            return None
        recorded_packet = row.get("packet") or {}
        packet = dict(recorded_packet)
        packet["retrieved_memory"] = [
            {
                "source_type": item.get("source_type"),
                "source_id": item.get("logical_source_id"),
                "content": item.get("content"),
                "score": item.get("score"),
                "metadata": {
                    "logical_identity": item.get("logical_identity"),
                    "authority_status": item.get("authority_status"),
                    "valid_from_chapter": item.get("valid_from_chapter"),
                    "valid_to_chapter": item.get("valid_to_chapter"),
                    "known_by": item.get("known_by"),
                    "not_known_by": item.get("not_known_by"),
                    "provenance": item.get("provenance"),
                    "evidence_pointer": item.get("evidence_pointer"),
                },
            }
            for item in replayed_hits
        ]
        sections = {
            key: _tokens(packet.get(key) or [])
            for key in (
                "task", "active_context", "working_memory",
                "retrieved_memory", "compressed_memory",
            )
        }
        return {
            "context_packet_id": str(row.get("_id") or ""),
            "recorded_token_estimate": int(row.get("token_estimate") or 0),
            "recorded_recomputed_token_estimate": _tokens(recorded_packet),
            "replayed_token_estimate": _tokens(packet),
            "tokens_by_section": sections,
            "packet": _json_safe(packet),
        }

    async def replay(self, db, request: ReplayRequest) -> Dict[str, Any]:
        started = time.perf_counter()
        readiness = None
        source_documents = None
        index_revision = None
        retrieval_diagnostics: Dict[str, Any] = {}
        if request.respect_index_readiness:
            from app.services.memory_incremental_index_service import memory_incremental_index_service
            strict = request.consumer not in {
                "conversation", "story_studio_conversation", "historical_evidence",
            }
            readiness = await memory_incremental_index_service.prepare_for_retrieval(
                db, request.project_id, strict_writing=strict
            )
            if readiness.get("fallback_required"):
                source_documents, fallback = await memory_incremental_index_service.direct_authority_documents(
                    db, request.project_id
                )
                retrieval_diagnostics.update(fallback)
            elif readiness.get("status") == "READY":
                index_revision = int(readiness.get("processed_version") or 0)
        hits = await retrieve_relevant_context(
            db,
            request.project_id,
            request.query,
            top_k=max(1, int(request.top_k)),
            refresh_index=False,
            safe_for_writing=request.consumer not in {
                "conversation", "story_studio_conversation", "historical_evidence",
            },
            consumer=request.consumer,
            as_of_chapter=request.current_chapter,
            as_of_scene=request.current_scene,
            pov_character=request.pov_character,
            branch_id=request.branch_id,
            index_revision=index_revision,
            source_documents=source_documents,
            resolve_legacy_aliases=index_revision is None,
            diagnostics=retrieval_diagnostics,
        )
        attributed: List[Dict[str, Any]] = []
        for rank, hit in enumerate(hits, start=1):
            physical_id = str(hit.get("id") or "")
            embedding = (
                await db.memory_embeddings.find_one({"_id": ObjectId(physical_id)})
                if ObjectId.is_valid(physical_id)
                else None
            ) or dict(hit)
            identity = await self._owner_identity(db, request.project_id, embedding)
            metadata = dict(embedding.get("metadata") or {})
            statuses = _status_values(embedding)
            content = str(hit.get("content") or "")
            chapter = (
                metadata.get("chapter_number")
                or metadata.get("valid_from_chapter")
                or identity.get("owner_chapter")
            )
            known_by = list(metadata.get("known_by") or [])
            not_known_by = list(metadata.get("not_known_by") or [])
            expected = [term.lower() for term in request.expected_terms if term]
            relevant = not expected or any(term in content.lower() for term in expected)
            attributed.append({
                "rank": rank,
                "physical_embedding_id": physical_id,
                "physical_source_id": identity["owner_physical_id"],
                "logical_source_id": identity["logical_source_id"],
                "logical_identity": identity["logical_identity"],
                "source_type": hit.get("source_type"),
                "source_version": int(embedding.get("source_version") or 1),
                "owner_source_version": identity["owner_source_version"],
                "score": float(hit.get("score") or 0),
                "semantic_score": float(hit.get("semantic_score") or 0),
                "estimated_tokens": estimate_tokens(content),
                "authority_status": metadata.get("authority_status") or identity.get("owner_authority_status"),
                "status": metadata.get("status") or identity.get("owner_status"),
                "valid_from_chapter": metadata.get("valid_from_chapter") or chapter,
                "valid_to_chapter": metadata.get("valid_to_chapter"),
                "scene_scope": metadata.get("scene_number") or metadata.get("scene_order"),
                "known_by": known_by,
                "not_known_by": not_known_by,
                "provenance": metadata.get("provenance") or identity.get("owner_provenance"),
                "evidence_pointer": metadata.get("evidence_pointer") or {
                    "source_type": hit.get("source_type"),
                    "source_id": identity["logical_source_id"],
                    "physical_source_id": identity["owner_physical_id"],
                },
                "candidate_or_rejected_or_stale": bool(statuses & STRICT_BAD_STATUSES),
                "future_chapter": bool(
                    request.current_chapter is not None
                    and chapter is not None
                    and int(chapter) > int(request.current_chapter)
                ),
                "pov_knowledge_leak": bool(
                    request.pov_character
                    and (
                        request.pov_character.lower() in {str(v).lower() for v in not_known_by}
                        or (
                            known_by
                            and request.pov_character.lower()
                            not in {str(v).lower() for v in known_by}
                        )
                    )
                ),
                "relevant": relevant,
                "why_selected": {
                    "rank": rank,
                    "score": float(hit.get("score") or 0),
                    "semantic_score": float(hit.get("semantic_score") or 0),
                    "query": request.query,
                    "consumer": request.consumer,
                    "chapter_relevance": chapter,
                },
                "content": content,
            })

        duplicate_groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in attributed:
            duplicate_groups.setdefault(item["logical_identity"], []).append(item)
        duplicates = [
            {
                "logical_identity": key,
                "count": len(items),
                "ranks": [item["rank"] for item in items],
                "physical_embedding_ids": [item["physical_embedding_id"] for item in items],
                "estimated_duplicate_tokens": sum(item["estimated_tokens"] for item in items[1:]),
            }
            for key, items in duplicate_groups.items()
            if len(items) > 1
        ]
        relevant_ranks = [item["rank"] for item in attributed if item["relevant"]]
        relevant_hits = len(relevant_ranks)
        expected_count = max(1, len(request.expected_terms))
        result = {
            "schema_version": 1,
            "mode": "BASELINE_OR_CURRENT_NATIVE",
            "captured_at": datetime.utcnow().isoformat() + "Z",
            "request": asdict(request),
            "retrieval": {
                "hits": attributed,
                "duplicate_groups": duplicates,
                "duplicate_logical_hits": sum(item["count"] - 1 for item in duplicates),
                "duplicate_tokens": sum(item["estimated_duplicate_tokens"] for item in duplicates),
                "candidate_rejected_stale_leakage": sum(item["candidate_or_rejected_or_stale"] for item in attributed),
                "future_knowledge_leakage": sum(item["future_chapter"] for item in attributed),
                "character_knowledge_leakage": sum(item["pov_knowledge_leak"] for item in attributed),
                "total_tokens": sum(item["estimated_tokens"] for item in attributed),
                "relevant_tokens": sum(item["estimated_tokens"] for item in attributed if item["relevant"]),
                "irrelevant_tokens": sum(item["estimated_tokens"] for item in attributed if not item["relevant"]),
                "recall_at_k": min(1.0, relevant_hits / expected_count),
                "mrr": (1.0 / min(relevant_ranks)) if relevant_ranks else 0.0,
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "index_readiness": readiness,
                "diagnostics": retrieval_diagnostics,
            },
            "context": await self._context_packet(db, request, attributed),
        }
        return _json_safe(result)

    def compare(self, baseline: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
        def metric(payload: Dict[str, Any], name: str) -> Any:
            return (payload.get("retrieval") or {}).get(name)

        names = (
            "duplicate_logical_hits", "total_tokens", "duplicate_tokens",
            "candidate_rejected_stale_leakage", "future_knowledge_leakage",
            "character_knowledge_leakage", "recall_at_k", "mrr", "latency_ms",
        )
        rows = []
        for name in names:
            before = metric(baseline, name)
            after = metric(candidate, name)
            rows.append({
                "metric": name,
                "before": before,
                "after": after,
                "delta": round(after - before, 6)
                if isinstance(before, (int, float)) and isinstance(after, (int, float))
                else None,
            })
        return {
            "schema_version": 1,
            "baseline_request": baseline.get("request"),
            "candidate_request": candidate.get("request"),
            "metrics": rows,
        }

    async def develop_story_baseline(
        self,
        db,
        project_id: str,
        *,
        cycle_numbers: Iterable[int] | None = None,
    ) -> Dict[str, Any]:
        query: Dict[str, Any] = {"project_id": ObjectId(project_id)}
        if cycle_numbers:
            query["cycle_number"] = {"$in": [int(value) for value in cycle_numbers]}
        cursor = db.context_packets.find(query).sort([("cycle_number", 1), ("created_at", 1)])
        rows: List[Dict[str, Any]] = []
        async for document in cursor:
            packet = document.get("packet") or {}
            story_bible = packet.get("story_bible") or packet.get("current_story_plan") or {}
            section_tokens = {
                str(key): _tokens(value)
                for key, value in (story_bible.get("sections") or story_bible).items()
            } if isinstance(story_bible, dict) else {}
            source_tokens = {
                key: _tokens(packet.get(key) or [])
                for key in (
                    "canon", "decisions", "confirmed_planning", "rejected_decisions",
                    "retrieved_memory", "agent_memory", "cycle_outputs", "chapter_memory",
                )
            }
            captured_sources = document.get("prompt_tokens_by_source") or document.get("tokens_by_source") or {}
            if captured_sources:
                source_tokens.update({
                    str(key): int(value or 0)
                    for key, value in captured_sources.items()
                })
            rows.append({
                "context_packet_id": str(document.get("_id") or ""),
                "cycle_number": int(document.get("cycle_number") or 0),
                "specialist": document.get("agent_name"),
                "prompt_tokens": int(document.get("token_estimate") or _tokens(packet)),
                "measured_prompt_tokens": document.get("prompt_tokens"),
                "source_tokens": source_tokens,
                "story_bible_section_tokens": section_tokens,
                "repeated_information": document.get("repeated_information") or {},
                "historical_attribution_complete": bool(captured_sources),
            })
        tokens = [row["prompt_tokens"] for row in rows]
        return _json_safe({
            "schema_version": 1,
            "project_id": project_id,
            "cycles": sorted({row["cycle_number"] for row in rows}),
            "specialist_packets": rows,
            "packet_count": len(rows),
            "prompt_tokens_total": sum(tokens),
            "prompt_tokens_median": statistics.median(tokens) if tokens else 0,
        })


memory_replay_service = MemoryReplayService()
