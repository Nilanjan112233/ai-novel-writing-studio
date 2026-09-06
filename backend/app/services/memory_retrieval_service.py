"""Project-scoped narrative memory indexing and retrieval.

The service prefers Chroma when it is installed, but keeps a Mongo-backed
deterministic vector store as the default test/dev path. That gives the app the
same retrieval contract without making local validation depend on a heavy
embedding runtime.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any, Dict, Iterable, List
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.services.memory_retrieval_policy import (
    RetrievalEligibilityContext,
    canonical_source_id,
    logical_identity,
    metadata_for_source,
    owner_source_version,
    retrieval_eligibility_policy,
)
from app.services.memory_index_cache import memory_index_cache
from app.services.memory_phase_c_ranker import (
    PHASE_C_RANKER_VERSION,
    bm25_scores,
    hash_scores,
    lexical_document_fields,
    story_metadata_score,
)

VECTOR_SIZE = 64


SOURCE_SPECS: Dict[str, tuple[str, tuple[str, ...]]] = {
    "timeline": ("timeline_messages", ("content", "agent_name", "message_type")),
    "output": ("agent_outputs", ("agent_name", "content")),
    "character": ("character_bibles", ("name", "role", "description", "goals", "fears", "current_arc_state", "notes")),
    "relationship": ("relationship_graphs", ("character_a", "character_b", "type", "relationship", "history", "status")),
    "world": ("world_bibles", ("locations", "races", "history", "religion", "politics", "technology", "economy", "academies", "world_rules", "current_conflicts")),
    "plot_thread": ("plot_threads", ("title", "description", "status", "related_characters")),
    "theme": ("theme_registry", ("themes", "motifs", "symbols", "reinforcement_opportunities")),
    "foreshadow": ("foreshadow_registry", ("setup", "expected_payoff", "resolved")),
    "continuity": ("continuity_reports", ("issues", "contradictions", "timeline_violations", "character_violations", "severity", "recommendations")),
    "scene": ("scene_registry", ("title", "summary", "characters_present", "purpose")),
    "story_timeline": ("story_timelines", ("event", "date", "age", "participants", "consequences", "dependencies", "event_type")),
    "question": ("questions", ("text", "choices", "answer")),
    "canon": ("canon_registry", ("fact", "status", "source")),
    "decision": ("decision_registry", ("decision", "answer", "status", "question_text")),
    "story_vision": ("story_visions", ("premise", "genre", "themes", "target_length", "audience", "narrative_goals", "director_notes")),
    "story_arc": ("story_arcs", ("title", "goal", "major_events", "conflicts", "payoffs", "mysteries", "character_changes")),
    "readiness": ("story_readiness", ("category", "title", "description", "priority", "status", "evidence")),
    "timeline_v2": ("timeline_entries", ("title", "summary", "importance", "status", "certainty", "dependencies")),
    "character_progression": ("character_progressions", ("character", "current_state", "desired_state", "skills", "powers", "beliefs", "relationships", "maturity", "trauma", "goals")),
    "knowledge": ("knowledge_entries", ("title", "content", "knowledge_type", "known_by", "not_known_by", "learned_how", "source", "reveal_target")),
    "foreshadow_v2": ("foreshadow_registry_v2", ("seed", "payoff_target", "status")),
    "artifact": ("artifact_registry", ("item", "owner", "power", "hidden_power", "cost", "limitations", "history", "future_relevance", "status")),
    "power_system": ("power_systems", ("ranks", "levels", "cultivation", "skills", "classes", "evolution_paths", "limitations", "resources", "costs", "progression_curve")),
    "character_journey": ("character_journeys", ("character_name", "goals", "fears", "beliefs", "growth", "relationships", "status", "future_plans")),
    "mystery": ("mystery_registry", ("question", "truth", "known_clues", "hidden_clues", "red_herrings", "reveal_target", "status")),
    "ai_insight": ("ai_insights", ("agent_concerns", "missing_story_areas", "weak_characters", "weak_pacing", "potential_contradictions", "suggested_improvements")),
    "faction": ("factions", ("name", "agenda", "pressure", "leader", "goals", "enemies", "allies", "secrets", "territory")),
    "arc_checklist": ("arc_checklists", ("category", "title", "description", "priority", "status", "dimension", "evidence")),
    "arc_dependency": ("arc_dependencies", ("dependency_type", "target_id", "required_state", "status", "validation_reason", "evidence")),
    "chapter_plan": ("chapter_plans", ("title", "chapter_number", "purpose", "conflict", "character_focus", "knowledge_changes", "status")),
    "scene_plan_v2": ("scene_plans", ("title", "purpose", "conflict", "outcome", "character_focus", "character_change", "status")),
    "power_progression": ("power_progressions", ("character", "starting_power", "ending_power", "new_abilities", "mastered_abilities", "limitations", "costs", "future_evolution")),
    "foreshadow_chain": ("foreshadow_chains", ("event_type", "summary", "from_state", "to_state", "evidence")),
    "artifact_evolution": ("artifact_evolutions", ("event_type", "summary", "from_state", "to_state", "evidence")),
    "knowledge_evolution": ("knowledge_evolutions", ("event_type", "summary", "from_state", "to_state", "evidence")),
    "chapter_intelligence": ("chapter_intelligence", ("chapter_number", "chapter_summary", "important_events", "characters_present", "character_changes", "knowledge_revealed", "mysteries_introduced", "mysteries_advanced", "mysteries_resolved", "relationship_changes", "artifact_usage", "timeline_impact", "canon_impact", "world_facts", "unresolved_questions", "future_obligations")),
    "atomic_memory": ("atomic_memories", ("content", "subject", "predicate", "compact_value")),
}

COLLECTION_TO_SOURCE_TYPE = {
    collection: source_type
    for source_type, (collection, _fields) in SOURCE_SPECS.items()
}


def _tokens(text: str) -> List[str]:
    return [
        token.strip(".,!?;:()[]{}\"'").lower()
        for token in (text or "").split()
        if token.strip(".,!?;:()[]{}\"'")
    ]


def embed_text(text: str) -> List[float]:
    vector = [0.0] * VECTOR_SIZE
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = digest[0] % VECTOR_SIZE
        weight = 1.0 + (digest[1] % 5) / 10
        vector[index] += weight
    magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / magnitude for value in vector]


def _cosine(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


EMOTIONAL_TERMS = {
    "tragic", "grief", "guilt", "fear", "love", "betrayal", "trust",
    "mercy", "wound", "sacrifice", "shame", "hope", "rage",
}
THEME_TERMS = {"theme", "motif", "symbol", "meaning", "inheritance", "power", "truth", "cost"}
CONTINUITY_TERMS = {"contradiction", "timeline", "continuity", "rule", "promise", "payoff"}


def _chapter_memory_quality(doc: Dict[str, Any]) -> float:
    """Score the usefulness of chapter intelligence without changing authority."""
    fields = (
        "important_events", "characters_present", "knowledge_revealed",
        "mysteries_introduced", "relationship_changes", "future_obligations",
        "artifacts", "world_facts", "unresolved_questions",
    )
    populated = sum(bool(doc.get(field)) for field in fields)
    characters = [str(item).strip().lower() for item in doc.get("characters_present") or []]
    polluted = sum(item in {"the", "her", "his", "did", "you", "found", "because", "one", "about"} for item in characters)
    prompt_shape = str(doc.get("chapter_summary") or "").lower().startswith("chapter ") and not doc.get("important_events")
    quality = min(1.0, 0.25 + populated * 0.08)
    quality -= min(0.35, polluted * 0.04)
    if prompt_shape:
        quality -= 0.2
    return max(0.05, round(quality, 3))


def narrative_relevance_score(query: str, doc: Dict[str, Any], base_score: float) -> float:
    """Blend semantic similarity with narrative-specific priority signals."""
    query_tokens = set(_tokens(query))
    content = (doc.get("content") or "").lower()
    content_tokens = set(_tokens(content))
    source_type = doc.get("source_type", "")
    score = base_score

    shared = query_tokens & content_tokens
    score += min(len(shared) * 0.035, 0.25)
    if source_type in {"character", "scene"} and shared:
        score += 0.22
    if source_type in {"character", "plot_thread", "theme"} and shared:
        score += 0.16
    if source_type == "plot_thread" and ("open" in content or "unresolved" in content):
        score += 0.18
    if query_tokens & EMOTIONAL_TERMS and content_tokens & EMOTIONAL_TERMS:
        score += 0.14
    if query_tokens & THEME_TERMS and (source_type in {"theme", "output"} or content_tokens & THEME_TERMS):
        score += 0.12
    if query_tokens & EMOTIONAL_TERMS and source_type in {"character", "plot_thread", "theme"}:
        score += 0.18
    if query_tokens & CONTINUITY_TERMS and source_type in {"continuity", "plot_thread", "world"}:
        score += 0.16
    if source_type == "atomic_memory" and shared:
        # Phase B keeps compact facts competitive with their verbose owners;
        # this is a type-aware relevance signal, not a new retrieval/fusion
        # architecture.
        score += 0.18
        predicate = str((doc.get("metadata") or {}).get("predicate") or "")
        if predicate == "owner" and query_tokens & {"who", "owner", "owns", "has", "holds"}:
            score += 0.22
        if predicate in {"plot_thread_state", "open_obligation"} and query_tokens & {"open", "thread", "dormant", "callback", "marker", "bell"}:
            score += 0.16
        if predicate in {"event", "character_change"} and query_tokens & {"injury", "injured", "hand", "palm", "healed", "scar"}:
            score += 0.16

    updated_at = doc.get("updated_at") or doc.get("created_at")
    if isinstance(updated_at, datetime):
        age_days = max((datetime.utcnow() - updated_at).days, 0)
        score += max(0.0, 0.1 - (age_days * 0.01))
    return score


def _doc_text(doc: Dict[str, Any], fields: Iterable[str]) -> str:
    parts = []
    for field in fields:
        value = doc.get(field)
        if isinstance(value, (list, dict)):
            parts.append(str(value))
        elif value:
            parts.append(str(value))
    return "\n".join(parts)


def materialize_owner_memory(
    source_type: str,
    document: Dict[str, Any],
) -> Dict[str, Any] | None:
    """Create one deterministic derived representation from an owner record."""
    if source_type == "project":
        fields = (
            "story_title", "project_name", "title", "premise", "idea_dump",
            "genre", "tone", "themes", "notes",
        )
        owner = {**document, "source_id": str(document.get("_id") or "")}
    else:
        spec = SOURCE_SPECS.get(source_type)
        if not spec:
            return None
        _collection_name, fields = spec
        owner = document
    if source_type == "chapter_intelligence":
        from app.services.memory_phase_b_service import episode_text
        content = episode_text(owner).strip()
    else:
        content = _doc_text(owner, fields).strip()
    if not content:
        return None
    metadata = metadata_for_source(source_type, owner)
    if source_type == "chapter_intelligence":
        metadata.update({
            "quality_score": _chapter_memory_quality(owner),
            "provenance": owner.get("provenance") or "chapter_intelligence",
        })
    elif source_type == "atomic_memory":
        metadata.update({
            "authority_level": owner.get("authority_class") or "derived",
            "provenance": owner.get("provenance") or "phase_b_atomic_memory",
            "evidence_pointers": owner.get("evidence_pointers") or [],
            "quality_score": float(owner.get("confidence") or 0.8),
            "conflict_status": owner.get("conflict_status"),
            "subject": owner.get("subject"),
            "predicate": owner.get("predicate"),
            "compact_value": owner.get("compact_value"),
            "entity_refs": owner.get("entity_refs") or [],
        })
    return {
        "source_type": source_type,
        "logical_source_id": str(metadata["logical_source_id"]),
        "source_version": int(metadata["owner_source_version"]),
        "physical_source_id": str(owner.get("_id") or ""),
        "content": content,
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "metadata": metadata,
    }


async def index_memory(
    db,
    *,
    project_id: str,
    source_type: str,
    source_id: str,
    content: str,
    metadata: Dict[str, Any] | None = None,
    source_version: int | None = None,
    physical_source_id: str | None = None,
) -> Dict[str, Any]:
    content = (content or "").strip()
    if not content:
        return {"writes": 0, "invalidated": 0, "unchanged": True, "empty": True}

    now = datetime.utcnow()
    project_oid = ObjectId(project_id)
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    normalized_metadata = dict(metadata or {})
    logical_source_id = str(
        normalized_metadata.get("logical_source_id") or source_id
    )
    explicit_source_version = int(
        source_version
        or normalized_metadata.get("owner_source_version")
        or 0
    ) or None
    normalized_metadata.update({
        "logical_source_id": logical_source_id,
        "physical_source_id": str(
            physical_source_id
            or normalized_metadata.get("physical_source_id")
            or source_id
        ),
    })
    if explicit_source_version is not None:
        normalized_metadata["owner_source_version"] = explicit_source_version
    normalized_metadata["logical_identity"] = logical_identity(
        source_type,
        logical_source_id,
        explicit_source_version or 1,
    )
    metadata_hash = hashlib.sha256(
        json.dumps(
            normalized_metadata,
            default=str,
            sort_keys=True,
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    lexical_fields = lexical_document_fields(content)
    identity = {
        "project_id": project_oid,
        "source_type": source_type,
        "source_id": logical_source_id,
    }

    # Owner-versioned sources have one deterministic materialization per
    # logical source/version. Replaying unchanged indexing updates in place.
    if explicit_source_version is not None:
        version_identity = {**identity, "source_version": explicit_source_version}
        existing_version = await db.memory_embeddings.find_one(
            version_identity,
            {"_id": 1, "active": 1, "content_hash": 1, "metadata_hash": 1, "phase_c_ranker_version": 1},
        )
        if (
            existing_version
            and existing_version.get("active") is not False
            and existing_version.get("content_hash") == content_hash
            and existing_version.get("metadata_hash") == metadata_hash
            and int(existing_version.get("phase_c_ranker_version") or 0) == PHASE_C_RANKER_VERSION
        ):
            return {"writes": 0, "invalidated": 0, "unchanged": True}
        update_result = await db.memory_embeddings.update_one(
            version_identity,
            {
                "$set": {
                    "active": True,
                    "content_hash": content_hash,
                    "metadata_hash": metadata_hash,
                    "content": content,
                    "embedding": embed_text(content),
                    **lexical_fields,
                    "metadata": normalized_metadata,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        invalidation_result = await db.memory_embeddings.update_many(
            {
                **identity,
                "source_version": {"$ne": explicit_source_version},
                "active": {"$ne": False},
                # A bounded historical state is still a valid as-of retrieval
                # source. Keep it materialized; the central policy selects it
                # only inside its chapter/scene interval.
                "$and": [
                    {"$or": [
                        {"metadata.valid_to_chapter": {"$exists": False}},
                        {"metadata.valid_to_chapter": None},
                    ]},
                    {"$or": [
                        {"metadata.valid_to_scene": {"$exists": False}},
                        {"metadata.valid_to_scene": None},
                    ]},
                ],
            },
            {"$set": {"active": False, "updated_at": now}},
        )
        memory_index_cache.invalidate(project_id)
        return {
            "writes": 1,
            "inserted": bool(update_result.upserted_id),
            "invalidated": int(invalidation_result.modified_count),
            "unchanged": False,
        }

    existing = await db.memory_embeddings.find_one(
        {
            **identity,
            "content_hash": content_hash,
            "active": {"$ne": False},
        },
        sort=[("source_version", -1), ("updated_at", -1)],
    )
    if existing:
        duplicate_result = await db.memory_embeddings.update_many(
            {**identity, "_id": {"$ne": existing["_id"]}},
            {"$set": {"active": False}},
        )
        if (
            existing.get("content_hash") == content_hash
            and existing.get("metadata_hash") == metadata_hash
            and int(existing.get("phase_c_ranker_version") or 0) == PHASE_C_RANKER_VERSION
        ):
            if duplicate_result.modified_count:
                memory_index_cache.invalidate(project_id)
            return {
                "writes": int(bool(duplicate_result.modified_count)),
                "invalidated": int(duplicate_result.modified_count),
                "unchanged": not bool(duplicate_result.modified_count),
            }
        await db.memory_embeddings.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "content": content,
                    "embedding": embed_text(content),
                    **lexical_fields,
                    "metadata": normalized_metadata,
                    "content_hash": content_hash,
                    "metadata_hash": metadata_hash,
                    "active": True,
                    "source_version": int(existing.get("source_version") or 1),
                    "updated_at": now,
                }
            },
        )
        memory_index_cache.invalidate(project_id)
        return {"writes": 1, "invalidated": int(duplicate_result.modified_count), "unchanged": False}

    # Another analysis task may index the same source at the same time. Retry the
    # source-version allocation and reuse an identical winner instead of leaking a
    # Mongo DuplicateKeyError into the author operation.
    for attempt in range(5):
        latest = await db.memory_embeddings.find_one(
            identity,
            {"source_version": 1},
            sort=[("source_version", -1), ("updated_at", -1)],
        )
        next_version = int((latest or {}).get("source_version") or 0) + 1
        try:
            await db.memory_embeddings.insert_one(
                {
                    **identity,
                    "source_version": next_version,
                    "active": True,
                    "content_hash": content_hash,
                    "metadata_hash": metadata_hash,
                    "content": content,
                    "embedding": embed_text(content),
                    **lexical_fields,
                    "metadata": normalized_metadata,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            break
        except DuplicateKeyError:
            winner = await db.memory_embeddings.find_one(
                {**identity, "content_hash": content_hash}
            )
            if winner:
                await db.memory_embeddings.update_many(
                    {**identity, "_id": {"$ne": winner["_id"]}},
                    {"$set": {"active": False}},
                )
                await db.memory_embeddings.update_one(
                    {"_id": winner["_id"]},
                    {"$set": {"active": True, "updated_at": now}},
                )
                memory_index_cache.invalidate(project_id)
                return {"writes": 1, "invalidated": 0, "unchanged": False}
            if attempt == 4:
                raise
    invalidation_result = await db.memory_embeddings.update_many(
        {**identity, "content_hash": {"$ne": content_hash}},
        {"$set": {"active": False}},
    )
    stale = (
        await db.memory_embeddings.find({**identity, "active": False}, {"_id": 1})
        .sort([("source_version", -1), ("updated_at", -1)])
        .skip(1)
        .to_list(length=1000)
    )
    if stale:
        await db.memory_embeddings.delete_many(
            {"_id": {"$in": [document["_id"] for document in stale]}}
        )
    memory_index_cache.invalidate(project_id)
    return {
        "writes": 1,
        "invalidated": int(invalidation_result.modified_count),
        "unchanged": False,
    }


async def cleanup_stale_memory(db, project_id: str | None = None) -> int:
    """Keep one inactive predecessor per source and remove older duplicates."""
    query: Dict[str, Any] = {"active": False}
    if project_id:
        query["project_id"] = ObjectId(project_id)
    stale = await db.memory_embeddings.find(
        query,
        {
            "_id": 1,
            "project_id": 1,
            "source_type": 1,
            "source_id": 1,
            "source_version": 1,
            "updated_at": 1,
        },
    ).to_list(length=100000)
    grouped: Dict[tuple[str, str, str], List[Dict[str, Any]]] = {}
    for document in stale:
        key = (
            str(document.get("project_id") or ""),
            str(document.get("source_type") or ""),
            str(document.get("source_id") or ""),
        )
        grouped.setdefault(key, []).append(document)
    delete_ids = []
    for documents in grouped.values():
        documents.sort(
            key=lambda item: (
                int(item.get("source_version") or 0),
                item.get("updated_at") or datetime.min,
            ),
            reverse=True,
        )
        delete_ids.extend(document["_id"] for document in documents[1:])
    if not delete_ids:
        return 0
    result = await db.memory_embeddings.delete_many({"_id": {"$in": delete_ids}})
    return result.deleted_count


async def index_project_memory(db, project_id: str) -> Dict[str, int]:
    """Refresh all Native sources without silently truncating a collection."""
    pid = ObjectId(project_id)
    indexed = 0
    aliases_deactivated = 0
    project = await db.projects.find_one({"_id": pid})
    if project:
        materialized = materialize_owner_memory("project", project)
        if materialized:
            await index_memory(
                db,
                project_id=project_id,
                source_type="project",
                source_id=str(materialized["logical_source_id"]),
                content=str(materialized["content"]),
                metadata=materialized["metadata"],
                source_version=int(materialized["source_version"]),
                physical_source_id=str(materialized["physical_source_id"]),
            )
            indexed += 1

    # Queries are intentionally project-only. Consumer safety is centralized
    # in memory_retrieval_policy rather than scattered through source cursors.
    for source_type, (collection_name, fields) in SOURCE_SPECS.items():
        collection = db[collection_name]
        async for doc in collection.find({"project_id": pid}):
            materialized = materialize_owner_memory(source_type, doc)
            if not materialized:
                continue
            metadata = materialized["metadata"]
            logical_source = str(materialized["logical_source_id"])
            physical_source = str(materialized["physical_source_id"])
            await index_memory(
                db,
                project_id=project_id,
                source_type=source_type,
                source_id=logical_source,
                content=str(materialized["content"]),
                metadata=metadata,
                source_version=int(metadata["owner_source_version"]),
                physical_source_id=physical_source,
            )
            indexed += 1
            # Keep legacy physical-ID rows as reversible inactive history.  Do
            # not delete any owner or embedding during normal repair/indexing.
            if physical_source and physical_source != logical_source:
                result = await db.memory_embeddings.update_many(
                    {
                        "project_id": pid,
                        "source_type": source_type,
                        "source_id": physical_source,
                        "active": {"$ne": False},
                    },
                    {"$set": {
                        "active": False,
                        "metadata.logical_source_id": logical_source,
                        "metadata.logical_identity": metadata["logical_identity"],
                        "metadata.owner_source_version": metadata["owner_source_version"],
                        "superseded_by_logical_identity": metadata["logical_identity"],
                        "updated_at": datetime.utcnow(),
                    }},
                )
                aliases_deactivated += int(result.modified_count)
    return {"indexed": indexed, "legacy_aliases_deactivated": aliases_deactivated}


async def _chapter_intelligence_aliases(db, pid: ObjectId) -> Dict[str, tuple[str, int]]:
    aliases: Dict[str, tuple[str, int]] = {}
    async for document in db.chapter_intelligence.find(
        {"project_id": pid},
        {"_id": 1, "intelligence_id": 1, "version_number": 1, "source_version": 1},
    ):
        logical_source = str(document.get("intelligence_id") or document.get("_id") or "")
        version = owner_source_version(document)
        aliases[str(document.get("_id") or "")] = (logical_source, version)
        aliases[logical_source] = (logical_source, version)
    return aliases


async def find_logical_memory_duplicates(db, project_id: str) -> List[Dict[str, Any]]:
    """Identify active duplicate logical records without modifying persistence."""
    if not ObjectId.is_valid(project_id):
        return []
    pid = ObjectId(project_id)
    aliases = await _chapter_intelligence_aliases(db, pid)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    async for document in db.memory_embeddings.find({"project_id": pid, "active": {"$ne": False}}):
        metadata = document.get("metadata") or {}
        source_type = str(document.get("source_type") or "memory")
        source_id = str(metadata.get("logical_source_id") or document.get("source_id") or "")
        version = int(metadata.get("owner_source_version") or document.get("source_version") or 1)
        if source_type == "chapter_intelligence" and source_id in aliases:
            source_id, version = aliases[source_id]
        key = logical_identity(source_type, source_id, version)
        grouped.setdefault(key, []).append(document)
    return [
        {
            "logical_identity": key,
            "count": len(documents),
            "physical_embedding_ids": [str(item.get("_id")) for item in documents],
            "source_ids": [str(item.get("source_id") or "") for item in documents],
            "rebuildable": True,
        }
        for key, documents in grouped.items()
        if len(documents) > 1
    ]


async def repair_logical_memory_duplicates(
    db,
    project_id: str,
    *,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Rebuild canonical rows and deactivate aliases; never delete authority."""
    duplicates = await find_logical_memory_duplicates(db, project_id)
    if dry_run:
        return {"dry_run": True, "duplicate_groups": duplicates, "changed": 0}
    stats = await index_project_memory(db, project_id)
    remaining = await find_logical_memory_duplicates(db, project_id)
    return {
        "dry_run": False,
        "duplicate_groups_before": duplicates,
        "duplicate_groups_after": remaining,
        "changed": int(stats.get("legacy_aliases_deactivated") or 0),
        "rebuildable": True,
        "authority_records_deleted": 0,
    }


async def retrieve_relevant_context(
    db,
    project_id: str,
    query: str,
    top_k: int = 10,
    refresh_index: bool = False,
    *,
    safe_for_writing: bool = False,
    consumer: str = "conversation",
    as_of_chapter: int | None = None,
    as_of_scene: int | None = None,
    pov_character: str | None = None,
    branch_id: str | None = None,
    index_revision: int | None = None,
    source_documents: List[Dict[str, Any]] | None = None,
    resolve_legacy_aliases: bool = True,
    diagnostics: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    if not ObjectId.is_valid(project_id):
        return []

    if refresh_index:
        await index_project_memory(db, project_id)
        if diagnostics is not None:
            diagnostics["index_writes_query"] = "legacy_full_refresh"
    pid = ObjectId(project_id)
    query_vector = embed_text(query)
    eligibility_context = RetrievalEligibilityContext(
        safe_for_writing=safe_for_writing,
        consumer=consumer,
        project_id=project_id,
        branch_id=branch_id,
        as_of_chapter=as_of_chapter,
        as_of_scene=as_of_scene,
        pov_character=pov_character,
    )
    logical_groups: Dict[str, List[Dict[str, Any]]] = {}
    cache_hit = False
    phase_c_active = False
    phase_c_diagnostics: Dict[str, Any] = {}
    if source_documents is not None:
        sources = list(source_documents)
    elif index_revision is not None:
        from app.services.memory_phase_c_service import memory_phase_c_service
        candidates, phase_c_diagnostics = await memory_phase_c_service.prepare_candidates(db, project_id, query)
        if candidates is not None:
            sources = candidates
            phase_c_active = True
        else:
            sources, cache_hit = await memory_index_cache.load(db, project_id, index_revision)
    else:
        sources = []
        async for source in db.memory_embeddings.find(
            {"project_id": pid, "active": {"$ne": False}}
        ):
            sources.append(dict(source))
    aliases = await _chapter_intelligence_aliases(db, pid) if resolve_legacy_aliases and not phase_c_active else {}
    prepared_sources: List[Dict[str, Any]] = []
    for source in sources:
        prepared = dict(source)
        prepared_metadata = dict(prepared.get("metadata") or {})
        prepared_type = str(prepared.get("source_type") or "memory")
        prepared_source = str(prepared_metadata.get("logical_source_id") or prepared.get("source_id") or "")
        prepared_version = int(prepared_metadata.get("owner_source_version") or prepared.get("source_version") or 1)
        if prepared_type == "chapter_intelligence" and prepared_source in aliases:
            prepared_source, prepared_version = aliases[prepared_source]
        prepared_identity = logical_identity(prepared_type, prepared_source, prepared_version)
        prepared_metadata.update({
            "logical_source_id": prepared_source,
            "logical_identity": prepared_identity,
            "owner_source_version": prepared_version,
        })
        prepared["metadata"] = prepared_metadata
        prepared["logical_identity"] = prepared_identity
        decision = retrieval_eligibility_policy.evaluate(prepared, eligibility_context)
        if not decision.eligible:
            continue
        prepared["_eligibility_decision"] = decision
        prepared_sources.append(prepared)
    sources = prepared_sources
    lexical_scores: Dict[str, float] = {}
    hash_rank_scores: Dict[str, float] = {}
    metadata_scores: Dict[str, float] = {}
    if phase_c_active and sources:
        lexical_scores = bm25_scores(query, sources)
        hash_rank_scores = hash_scores(query, sources)
        metadata_scores = {
            str(source["logical_identity"]): story_metadata_score(query, source, as_of_chapter=as_of_chapter)
            for source in sources
        }

        def _normalized(values: Dict[str, float]) -> Dict[str, float]:
            if not values:
                return {}
            low, high = min(values.values()), max(values.values())
            if high <= low:
                return {key: 0.0 for key in values}
            return {key: (value - low) / (high - low) for key, value in values.items()}

        lexical_scores, hash_rank_scores, metadata_scores = (
            _normalized(lexical_scores), _normalized(hash_rank_scores), _normalized(metadata_scores)
        )
    if diagnostics is not None:
        diagnostics.setdefault("full_source_scans_query", 0)
        diagnostics.setdefault("owner_records_inspected_query", 0)
        diagnostics.setdefault("index_writes_query", 0)
        diagnostics.update({
            "embedding_records_scored": len(sources),
            "index_cache_hit": bool(cache_hit or phase_c_diagnostics.get("phase_c_candidate_cache_hit")),
            "ranking_strategy": "metadata_lexical_hash_weighted" if phase_c_active else "phase_b_complete_scan_fallback",
            **phase_c_diagnostics,
            "records_scored": len(sources),
        })
    for source in sources:
        doc = dict(source)
        metadata = dict(doc.get("metadata") or {})
        source_type = str(doc.get("source_type") or "memory")
        logical_source = str(metadata.get("logical_source_id") or doc.get("source_id") or "")
        version = int(metadata.get("owner_source_version") or doc.get("source_version") or 1)
        if source_type == "chapter_intelligence" and logical_source in aliases:
            logical_source, version = aliases[logical_source]
        logical_key = logical_identity(source_type, logical_source, version)
        metadata.update({
            "logical_source_id": logical_source,
            "logical_identity": logical_key,
            "owner_source_version": version,
        })
        doc["metadata"] = metadata
        decision = doc["_eligibility_decision"]
        base_score = _cosine(query_vector, doc.get("embedding") or [])
        if phase_c_active:
            score = (
                0.48 * lexical_scores.get(logical_key, 0.0)
                + 0.30 * hash_rank_scores.get(logical_key, 0.0)
                + 0.22 * metadata_scores.get(logical_key, 0.0)
            )
        else:
            score = narrative_relevance_score(query, doc, base_score)
        if source_type == "chapter_intelligence":
            quality = float(metadata.get("quality_score") or 0.5)
            score += (quality - 0.5) * 0.35
        content = str(doc.get("content") or "")
        logical_groups.setdefault(logical_key, []).append({
            "document": doc,
            "content": content,
            "estimated_tokens": max(1, len(content) // 4),
            "score": score,
            "semantic_score": base_score,
            "decision": decision,
        })

    deduplicated: List[Dict[str, Any]] = []
    for logical_key, candidates in logical_groups.items():
        # Within the same logical source/version, authority is identical in the
        # normal case. Prefer the compact representation before score so a
        # verbose duplicate cannot occupy context merely by repeating terms.
        candidates.sort(
            key=lambda item: (
                item["decision"].authority_priority,
                -item["estimated_tokens"],
                item["score"],
            ),
            reverse=True,
        )
        selected = candidates[0]
        doc = selected["document"]
        metadata = dict(doc.get("metadata") or {})
        evidence_pointers = []
        for item in candidates:
            candidate_doc = item["document"]
            candidate_metadata = candidate_doc.get("metadata") or {}
            evidence_pointers.append(
                candidate_metadata.get("evidence_pointer")
                or {
                    "source_type": candidate_doc.get("source_type"),
                    "source_id": candidate_metadata.get("logical_source_id") or candidate_doc.get("source_id"),
                    "physical_embedding_id": str(candidate_doc.get("_id") or ""),
                    "physical_source_id": candidate_metadata.get("physical_source_id"),
                }
            )
        selection_score = selected["score"] + selected["decision"].authority_priority / 1000.0
        metadata.update({
            "authority_level": selected["decision"].authority_level,
            "validity": selected["decision"].validity,
            "eligibility_reasons": list(selected["decision"].reasons),
            "evidence_pointers": evidence_pointers,
            "duplicate_representations_collapsed": max(0, len(candidates) - 1),
        })
        deduplicated.append({
            "id": str(doc.get("_id")),
            "source_type": doc.get("source_type", "memory"),
            "source_id": metadata.get("logical_source_id") or doc.get("source_id", ""),
            "logical_identity": logical_key,
            "source_version": int(metadata.get("owner_source_version") or doc.get("source_version") or 1),
            "content": selected["content"],
            "score": selected["score"],
            "selection_score": selection_score,
            "semantic_score": selected["semantic_score"],
            "estimated_tokens": selected["estimated_tokens"],
            "authority_level": selected["decision"].authority_level,
            "validity": selected["decision"].validity,
            "why_selected": {
                "query_relevance": selected["score"],
                "semantic_score": selected["semantic_score"],
                "ranking_strategy": "metadata_lexical_hash_weighted" if phase_c_active else "phase_b_complete_scan_fallback",
                "lexical_score": lexical_scores.get(logical_key, 0.0) if phase_c_active else None,
                "metadata_score": metadata_scores.get(logical_key, 0.0) if phase_c_active else None,
                "hash_score": hash_rank_scores.get(logical_key, selected["semantic_score"]) if phase_c_active else selected["semantic_score"],
                "authority_priority": selected["decision"].authority_priority,
                "consumer": consumer,
                "as_of_chapter": as_of_chapter,
                "as_of_scene": as_of_scene,
                "pov_character": pov_character,
                "logical_deduplication": max(0, len(candidates) - 1),
            },
            "metadata": metadata,
        })

    # An old indexing path could leave several owner versions active.  Keep
    # one current representation per logical owner after chronology filtering.
    # Historical versions remain stored and can still be selected when their
    # explicit validity interval makes them the eligible version for an as-of
    # replay.
    current_by_source: Dict[str, Dict[str, Any]] = {}
    for item in deduplicated:
        source_key = f"{item.get('source_type')}:{item.get('source_id')}"
        existing = current_by_source.get(source_key)
        if existing is None or (
            int(item.get("source_version") or 1),
            float(item.get("selection_score") or 0),
        ) > (
            int(existing.get("source_version") or 1),
            float(existing.get("selection_score") or 0),
        ):
            if existing:
                item["metadata"].setdefault("evidence_pointers", []).extend(
                    existing.get("metadata", {}).get("evidence_pointers") or []
                )
                item["metadata"]["superseded_versions_collapsed"] = int(
                    existing.get("metadata", {}).get("superseded_versions_collapsed") or 0
                ) + 1
            current_by_source[source_key] = item
        elif existing:
            existing["metadata"].setdefault("evidence_pointers", []).extend(
                item.get("metadata", {}).get("evidence_pointers") or []
            )
            existing["metadata"]["superseded_versions_collapsed"] = int(
                existing.get("metadata", {}).get("superseded_versions_collapsed") or 0
            ) + 1
    deduplicated = list(current_by_source.values())

    # Preserve exact-content deduplication across different logical sources,
    # preferring the most authoritative valid source and retaining evidence.
    by_content: Dict[str, Dict[str, Any]] = {}
    for item in deduplicated:
        content_hash = hashlib.sha256(item["content"].strip().lower().encode("utf-8")).hexdigest()
        existing = by_content.get(content_hash)
        if not existing or (
            item["selection_score"], -item["estimated_tokens"]
        ) > (
            existing["selection_score"], -existing["estimated_tokens"]
        ):
            if existing:
                item["metadata"].setdefault("evidence_pointers", []).extend(
                    existing.get("metadata", {}).get("evidence_pointers") or []
                )
            by_content[content_hash] = item
        elif existing:
            existing["metadata"].setdefault("evidence_pointers", []).extend(
                item.get("metadata", {}).get("evidence_pointers") or []
            )
    ranked = list(by_content.values())
    ranked.sort(key=lambda item: item["selection_score"], reverse=True)
    for rank, item in enumerate(ranked[:top_k], start=1):
        item["rank"] = rank
        item["why_selected"]["rank"] = rank
    return ranked[:top_k]
