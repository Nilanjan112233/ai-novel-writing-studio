"""Shared, incremental narrative analysis graph for NovelForge Phase 6.

The engine is deliberately deterministic. AI review can add observations, but every
platform surface consumes the same persisted nodes, edges, findings, and scores.
"""
from __future__ import annotations

import hashlib
import json
import re
import asyncio
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any, Dict, Iterable
from uuid import uuid4

from bson import ObjectId
from pymongo import UpdateOne

from app.services.story_quality_service import story_quality_service


SEVERITY_WEIGHT = {"info": 1, "low": 2, "medium": 5, "warning": 5, "high": 10, "critical": 18}
DOMAINS = ("character", "canon", "timeline", "plot", "pacing", "continuity", "balance")
RESPONSIBLE_SUBSYSTEMS = {
    "character": "character_intelligence",
    "canon": "canon_intelligence",
    "timeline": "timeline_intelligence",
    "plot": "plot_thread_intelligence",
    "pacing": "story_health",
    "continuity": "story_health",
    "balance": "developmental_editor",
}
SOURCE_COLLECTIONS = {
    "chapter": "chapter_intelligence",
    "scene": "scene_plans",
    "scene_draft": "scene_drafts",
    "character": "character_bibles",
    "relationship": "relationship_graphs",
    "timeline": "timeline_entries",
    "canon": "canon_registry",
    "canon_conflict": "canon_conflicts",
    "plot_thread": "plot_threads",
    "mystery": "mystery_registry",
    "foreshadow": "foreshadow_registry_v2",
    "artifact": "artifact_registry",
    "location": "world_bibles",
    "organization": "factions",
    "power": "power_progressions",
    "continuity": "continuity_reports",
    "shared_context": "shared_narrative_context",
    "planning_invalidation": "planning_invalidations",
}
IDENTITY_FIELDS = (
    "intelligence_id", "scene_id", "draft_id", "entry_id", "canon_id",
    "conflict_id", "thread_id", "mystery_id", "artifact_id",
    "relationship_id", "character_id", "name", "report_id",
)
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
AUTHOR_LABEL_FIELDS = (
    "title", "name", "question", "subject", "label", "event", "seed",
    "promise", "summary", "description", "payoff_target", "value",
)
AUTHOR_KIND_LABELS = {
    "foreshadow": "Unnamed foreshadowing thread",
    "plot_thread": "Unnamed plot thread",
    "mystery": "Unnamed mystery",
    "timeline": "Unnamed timeline event",
    "canon": "Unnamed canon fact",
}


def _serialize(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {("id" if key == "_id" else key): _serialize(item) for key, item in value.items()}
    return value


def _stable(value: Any) -> str:
    return json.dumps(_serialize(value), sort_keys=True, separators=(",", ":"), default=str)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_stable(value).encode("utf-8")).hexdigest()


def _bounded(value: Any) -> Any:
    """Keep graph records queryable without duplicating entire manuscripts."""
    if isinstance(value, str):
        return value if len(value) <= 2000 else f"{value[:2000]}…"
    if isinstance(value, list):
        return [_bounded(item) for item in value[:200]]
    if isinstance(value, dict):
        return {key: _bounded(item) for key, item in value.items()}
    return value


def _identity(document: Dict[str, Any]) -> str:
    for field in IDENTITY_FIELDS:
        if document.get(field):
            return str(document[field])
    return str(document.get("_id") or "")


def _author_label(document: Dict[str, Any], kind: str) -> str:
    """Choose story language for author surfaces while preserving machine identity separately."""
    for field in AUTHOR_LABEL_FIELDS:
        value = document.get(field)
        if isinstance(value, str):
            candidate = value.strip()
            if candidate and not UUID_PATTERN.fullmatch(candidate):
                return candidate
    return AUTHOR_KIND_LABELS.get(kind, f"Unnamed {kind.replace('_', ' ')}")


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif value is not None:
        text = str(value).strip()
        if text:
            yield text


def _locations(document: Dict[str, Any]) -> tuple[list[int], list[str]]:
    chapter = document.get("chapter_number")
    chapters = [int(chapter)] if isinstance(chapter, (int, float)) else []
    scenes = [str(value) for key in ("scene_id", "source_scene_id") if (value := document.get(key))]
    return chapters, scenes


def _parse_story_date(value: Any) -> datetime | None:
    """Parse structured chronology values without pretending prose dates sort."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%d %B %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value.strip(), pattern)
        except ValueError:
            continue
    return None


class NarrativeAnalysisEngine:
    def __init__(self) -> None:
        self._project_locks: dict[str, asyncio.Lock] = {}

    async def _record_history(
        self,
        db,
        pid: ObjectId,
        snapshot: Dict[str, Any],
        findings: list[Dict[str, Any]],
        *,
        trigger: str,
    ) -> None:
        """Persist a compact, immutable projection for author-facing score history."""
        history = {
            "project_id": pid,
            "analysis_id": snapshot.get("analysis_id") or str(uuid4()),
            "scores": dict(snapshot.get("scores") or {}),
            "finding_counts": dict(snapshot.get("finding_counts") or {}),
            "findings": [
                {
                    "finding_id": item.get("finding_id"),
                    "domain": item.get("domain"),
                    "severity": item.get("severity"),
                    "explanation": item.get("explanation"),
                    "recommended_actions": list(item.get("recommended_actions") or [])[:3],
                    "affected_chapters": list(item.get("affected_chapters") or [])[:100],
                    "affected_scenes": list(item.get("affected_scenes") or [])[:200],
                }
                for item in findings[:2000]
            ],
            "stats": dict(snapshot.get("stats") or {}),
            "trigger": trigger,
            "calculated_at": snapshot.get("calculated_at") or datetime.utcnow(),
        }
        await db.narrative_analysis_history.update_one(
            {"project_id": pid, "analysis_id": history["analysis_id"]},
            {"$setOnInsert": history},
            upsert=True,
        )

    async def _project(self, db, project_id: str) -> ObjectId:
        if not ObjectId.is_valid(project_id):
            raise ValueError("Invalid project ID")
        pid = ObjectId(project_id)
        if not await db.projects.find_one({"_id": pid}):
            raise ValueError("Project not found")
        return pid

    async def _load_sources(self, db, pid: ObjectId) -> Dict[str, list[Dict[str, Any]]]:
        result: Dict[str, list[Dict[str, Any]]] = {}
        for kind, collection in SOURCE_COLLECTIONS.items():
            query: Dict[str, Any] = {"project_id": pid, "authority_status": {"$ne": "stale"}}
            if kind == "planning_invalidation":
                query["status"] = "pending"
            if kind == "chapter":
                query["active"] = True
            if kind == "canon":
                query["active"] = True
            if kind == "scene_draft":
                query["active"] = True
                query["status"] = {"$in": ["approved", "validated"]}
            result[kind] = await db[collection].find(query).to_list(length=20000)
        chapter_rows = await db.chapter_plans.find(
            {"project_id": pid}, {"chapter_plan_id": 1, "chapter_number": 1, "title": 1}
        ).to_list(length=10000)
        chapter_by_id = {str(item.get("chapter_plan_id")): item for item in chapter_rows}
        scene_by_id = {str(item.get("scene_id")): item for item in result.get("scene") or []}
        for draft in result.get("scene_draft") or []:
            scene = scene_by_id.get(str(draft.get("scene_id"))) or {}
            chapter = chapter_by_id.get(str(scene.get("chapter_plan_id") or draft.get("chapter_plan_id"))) or {}
            draft["_chapter_number"] = int(chapter.get("chapter_number") or 0)
            draft["_chapter_title"] = chapter.get("title")
            draft["_scene_order"] = int(scene.get("order") or 0)
            draft["_scene_title"] = scene.get("title")
        return result

    async def _source_manifest(self, db, pid: ObjectId) -> Dict[str, Any]:
        """Read lightweight collection watermarks before loading story payloads."""
        manifest: Dict[str, Any] = {}
        for kind, collection in SOURCE_COLLECTIONS.items():
            query: Dict[str, Any] = {"project_id": pid, "authority_status": {"$ne": "stale"}}
            if kind == "planning_invalidation":
                query["status"] = "pending"
            if kind in {"chapter", "canon"}:
                query["active"] = True
            if kind == "scene_draft":
                query.update({"active": True, "status": {"$in": ["approved", "validated"]}})
            latest = await db[collection].find_one(
                query,
                {"_id": 1, "updated_at": 1, "created_at": 1},
                sort=[("updated_at", -1), ("created_at", -1), ("_id", -1)],
            )
            manifest[kind] = {
                "count": await db[collection].count_documents(query),
                "latest_id": str((latest or {}).get("_id") or ""),
                "latest_at": _serialize(
                    (latest or {}).get("updated_at") or (latest or {}).get("created_at")
                ),
            }
        return manifest

    def _node(self, kind: str, document: Dict[str, Any]) -> Dict[str, Any]:
        node_id = f"{kind}:{_identity(document)}"
        chapters, scenes = _locations(document)
        label = _author_label(document, kind)
        source_payload = _serialize(document)
        source_payload.pop("id", None)
        source_payload.pop("project_id", None)
        payload = _bounded(source_payload)
        return {
            "node_id": node_id,
            "kind": kind,
            "label": label,
            "chapter_numbers": chapters,
            "scene_ids": scenes,
            "source_collection": SOURCE_COLLECTIONS[kind],
            "source_id": _identity(document),
            "source_fingerprint": _fingerprint(source_payload),
            "payload": payload,
        }

    def _edges(self, nodes: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        identities: Dict[str, list[str]] = defaultdict(list)
        for node in nodes:
            identities[node["source_id"].lower()].append(node["node_id"])
            identities[node["label"].lower()].append(node["node_id"])
        edges: Dict[str, Dict[str, Any]] = {}
        for node in nodes:
            source = node["node_id"]
            for text in _strings(node["payload"]):
                normalized = text.lower()
                tokens = re.findall(r"[a-z0-9][a-z0-9_-]*", normalized)
                markers = {normalized, *tokens}
                for width in range(2, min(5, len(tokens)) + 1):
                    markers.update(" ".join(tokens[index:index + width]) for index in range(len(tokens) - width + 1))
                for marker in markers:
                    if len(marker) < 3:
                        continue
                    for target in identities.get(marker, []):
                        if target == source:
                            continue
                        edge_id = _fingerprint((source, target, "references"))[:24]
                        edges[edge_id] = {
                            "edge_id": edge_id, "source": source, "target": target,
                            "relationship": "references", "confidence": 0.8,
                        }
        return list(edges.values())

    def _finding(
        self, domain: str, category: str, severity: str, explanation: str,
        *, evidence: list[Any], chapters: Iterable[int] = (), scenes: Iterable[str] = (),
        actions: Iterable[str] = (), elements: Iterable[str] = (), confidence: float | None = None,
    ) -> Dict[str, Any]:
        location_chapters = sorted({int(value) for value in chapters if value is not None})
        location_scenes = sorted({str(value) for value in scenes if value})
        action_list = list(actions)
        basis = {"domain": domain, "category": category, "explanation": explanation,
                 "chapters": location_chapters, "scenes": location_scenes, "elements": sorted(set(elements))}
        evidence_items = list(evidence)
        calibrated_confidence = confidence
        if calibrated_confidence is None:
            support = len(evidence_items) + len(location_chapters) + len(location_scenes)
            calibrated_confidence = min(.95, .62 + min(5, support) * .06)
        semantic_basis = {
            "domain": domain,
            "category": category,
            "chapters": location_chapters,
            "scenes": location_scenes,
            "elements": sorted(set(elements)),
            "evidence": _serialize(evidence_items[:3]),
        }
        return {
            "finding_id": _fingerprint(basis)[:32], "domain": domain,
            "semantic_issue_id": _fingerprint(semantic_basis)[:32],
            "finding_type": "analysis",
            "category": category, "severity": severity, "explanation": explanation,
            "affected_chapters": location_chapters, "affected_scenes": location_scenes,
            "affected_elements": sorted(set(elements)), "evidence": _serialize(evidence_items),
            "recommended_actions": action_list, "confidence": round(calibrated_confidence, 2),
            "responsible_subsystem": RESPONSIBLE_SUBSYSTEMS.get(domain, "story_health"),
            "suggested_improvement": action_list[0] if action_list else "Review the evidence and choose an author-approved improvement.",
            "source_service": "narrative_analysis_engine",
        }

    @staticmethod
    def _narrative_person(text: str) -> str:
        narrative = re.sub(r'["“][^"”]{0,500}["”]', " ", text or "")
        tokens = re.findall(r"[a-z']+", narrative.lower())
        first = sum(token in {"i", "me", "my", "mine", "we", "us", "our", "ours"} for token in tokens)
        third = sum(token in {"he", "him", "his", "she", "her", "hers", "they", "them", "their", "theirs"} for token in tokens)
        if first >= 4 and first > third * 1.4:
            return "first person"
        if third >= 4 and third > first * 1.4:
            return "third person"
        return "omniscient or indeterminate"

    @staticmethod
    def _planned_person(scene: Dict[str, Any], draft: Dict[str, Any]) -> str:
        values = [
            scene.get("pov"), scene.get("point_of_view"), scene.get("planned_pov"),
            *[item.get("pov") for item in draft.get("paragraph_blueprint") or [] if isinstance(item, dict)],
        ]
        text = " ".join(str(value or "").lower() for value in values)
        if "omniscient" in text or "multiple" in text:
            return "omniscient"
        if "first" in text or "1st" in text:
            return "first person"
        if "third" in text or "3rd" in text:
            return "third person"
        return "unspecified"

    def _prose_findings(
        self,
        scene_plans: list[Dict[str, Any]],
        drafts: list[Dict[str, Any]],
    ) -> list[Dict[str, Any]]:
        findings: list[Dict[str, Any]] = []
        scene_by_id = {str(item.get("scene_id")): item for item in scene_plans}
        ordered = sorted(
            drafts,
            key=lambda item: (
                int(item.get("_chapter_number") or 0),
                int(item.get("_scene_order") or 0),
                int(item.get("version_number") or 0),
            ),
        )
        previous: tuple[Dict[str, Any], str] | None = None
        for draft in ordered:
            scene = scene_by_id.get(str(draft.get("scene_id"))) or {}
            detected = self._narrative_person(str(draft.get("generated_text") or ""))
            planned = self._planned_person(scene, draft)
            chapter = int(draft.get("_chapter_number") or 0)
            scene_id = str(draft.get("scene_id") or "")
            if planned in {"first person", "third person"} and detected not in {planned, "omniscient or indeterminate"}:
                findings.append(self._finding(
                    "continuity", "pov_drift", "high",
                    f"{draft.get('_scene_title') or 'This scene'} appears to shift from the planned {planned} narration to {detected}.",
                    evidence=[{"planned_pov": planned, "detected_pov": detected, "scene": draft.get("_scene_title")}],
                    chapters=(chapter,), scenes=(scene_id,),
                    actions=("Restore the planned viewpoint, or mark the POV change as intentional in the scene plan.",),
                    elements=(scene_id,), confidence=.82,
                ))
            if previous and previous[1] != detected and "indeterminate" not in previous[1] and "indeterminate" not in detected:
                previous_draft, previous_person = previous
                intentional = bool(
                    scene.get("pov_change_planned")
                    or scene.get("intentional_pov_change")
                    or planned == detected
                )
                if not intentional:
                    findings.append(self._finding(
                        "continuity", "unexpected_pov_transition", "high",
                        f"The narration changes from {previous_person} in {previous_draft.get('_scene_title') or 'the previous scene'} to {detected} in {draft.get('_scene_title') or 'this scene'} without a planned POV transition.",
                        evidence=[
                            {"chapter": previous_draft.get("_chapter_number"), "scene": previous_draft.get("_scene_title"), "pov": previous_person},
                            {"chapter": chapter, "scene": draft.get("_scene_title"), "pov": detected},
                        ],
                        chapters=(previous_draft.get("_chapter_number"), chapter),
                        scenes=(previous_draft.get("scene_id"), scene_id),
                        actions=("Confirm and mark the viewpoint break as intentional, or revise the drifting narration.",),
                        elements=(str(previous_draft.get("scene_id") or ""), scene_id), confidence=.78,
                    ))
            previous = (draft, detected)

        if len(ordered) < 4:
            return findings
        pattern_locations: Dict[str, list[Dict[str, Any]]] = defaultdict(list)
        gesture_patterns = {
            "heart reactions": r"\bheart\s+(?:hammer|pound|race|lurch|skip|clench)",
            "breath reactions": r"\b(?:breath|breathing)\s+(?:catch|hitch|stop|shallow|ragged)|\bheld (?:his|her|their) breath",
            "hand or finger gestures": r"\b(?:hand|hands|finger|fingers|knuckle|knuckles)\b.{0,32}\b(?:clench|curl|tighten|tremble|drum|tap|grip)",
            "rain imagery": r"\brain\b|\brain-soaked\b|\brainwater\b",
            "ozone imagery": r"\bozone\b",
        }
        for draft in ordered:
            text = str(draft.get("generated_text") or "")
            for label, pattern in gesture_patterns.items():
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    pattern_locations[label].append({
                        "chapter": draft.get("_chapter_number"),
                        "scene_id": draft.get("scene_id"),
                        "scene": draft.get("_scene_title"),
                        "excerpt": text[max(0, match.start() - 45):match.end() + 65].strip(),
                    })
        threshold = max(4, (len(ordered) + 2) // 3)
        for label, locations in pattern_locations.items():
            distinct_scenes = {item.get("scene_id") for item in locations}
            if len(locations) < threshold or len(distinct_scenes) < 3:
                continue
            findings.append(self._finding(
                "pacing", "repetitive_prose_pattern", "medium",
                f"The manuscript repeatedly uses {label} in {len(distinct_scenes)} scenes, which may make emotional or sensory beats feel predictable.",
                evidence=locations[:6],
                chapters=[item.get("chapter") for item in locations],
                scenes=[str(item.get("scene_id") or "") for item in locations],
                actions=("Review the representative locations and vary only repetitions that are not intentional thematic echoes.",),
                elements=(label,), confidence=.8,
            ))
        return findings

    def _analyze(self, sources: Dict[str, list[Dict[str, Any]]]) -> list[Dict[str, Any]]:
        findings: list[Dict[str, Any]] = []
        chapters = sorted(sources["chapter"], key=lambda item: int(item.get("chapter_number") or 0))
        recent = chapters[-10:]

        for invalidation in sources.get("planning_invalidation") or []:
            count = int(invalidation.get("affected_count") or len(invalidation.get("affected_records") or []))
            findings.append(self._finding(
                "continuity",
                "author_decision_requires_reconsideration",
                "high",
                str(invalidation.get("message") or f"{count} planning record(s) need reconsideration after an author decision changed."),
                evidence=list(invalidation.get("affected_records") or [])[:12],
                actions=("Continue story development so the affected planning can be reconciled.",),
                elements=(str(invalidation.get("decision_id") or invalidation.get("_id") or ""),),
                confidence=.99,
            ))

        # Canon: conflicts already carry authoritative source evidence.
        canon_by_id = {str(item.get("canon_id")): item for item in sources["canon"]}
        for conflict in sources["canon_conflict"]:
            if str(conflict.get("status") or "open") not in {"open", "acknowledged"}:
                continue
            records = [canon_by_id[value] for value in map(str, conflict.get("canon_ids") or []) if value in canon_by_id]
            evidence = [{
                "source": f"{item.get('source_collection')}:{item.get('source_id')}",
                "value": item.get("value"), "canon_id": item.get("canon_id"),
            } for item in records] or list(conflict.get("evidence") or [])
            findings.append(self._finding(
                "canon", str(conflict.get("conflict_type") or "canon_conflict"),
                "high" if conflict.get("severity") == "high" else "medium",
                str(conflict.get("message") or "Active canon sources conflict."),
                evidence=evidence,
                actions=("Review the original and conflicting sources.", "Acknowledge or resolve the authoritative fact."),
                elements=[str(item.get("canon_id")) for item in records],
            ))

        # Timeline: missing dependencies, duplicate positions, gaps, impossible ranges.
        timeline = sources["timeline"]
        timeline_ids = {str(item.get("entry_id") or item.get("_id")) for item in timeline}
        orders: Dict[int, list[Dict[str, Any]]] = defaultdict(list)
        for entry in timeline:
            entry_id = str(entry.get("entry_id") or entry.get("_id"))
            missing = [str(value) for value in entry.get("dependencies") or [] if str(value) not in timeline_ids]
            if missing:
                findings.append(self._finding("timeline", "missing_dependency", "high",
                    f"{entry.get('event') or entry.get('title') or entry_id} depends on missing events.",
                    evidence=missing, actions=("Restore the missing event or remove the dependency.",), elements=(entry_id,)))
            order = entry.get("order")
            if isinstance(order, (int, float)):
                orders[int(order)].append(entry)
            start, end = entry.get("start_date") or entry.get("date"), entry.get("end_date")
            parsed_start, parsed_end = _parse_story_date(start), _parse_story_date(end)
            if parsed_start and parsed_end and parsed_end < parsed_start:
                findings.append(self._finding("timeline", "impossible_date", "critical",
                    f"{entry.get('event') or entry_id} ends before it starts.", evidence=[{"start": start, "end": end}],
                    actions=("Correct the event dates before approving chronology changes.",), elements=(entry_id,)))
        for order, entries in orders.items():
            if len(entries) > 1:
                findings.append(self._finding("timeline", "overlapping_events", "medium",
                    f"{len(entries)} events share chronological position {order}.",
                    evidence=[item.get("event") or item.get("title") or _identity(item) for item in entries],
                    actions=("Confirm simultaneity or assign distinct chronological positions.",),
                    elements=[_identity(item) for item in entries]))
        if orders:
            expected = set(range(min(orders), max(orders) + 1))
            for order in sorted(expected - set(orders))[:20]:
                previous_event = next((
                    item.get("event") or item.get("title")
                    for item in orders.get(order - 1, [])
                ), "the preceding event")
                next_event = next((
                    item.get("event") or item.get("title")
                    for item in orders.get(order + 1, [])
                ), "the following event")
                findings.append(self._finding("timeline", "chronology_gap", "low",
                    f"A transition may be missing between {previous_event} and {next_event}.",
                    evidence=[{"before": previous_event, "after": next_event}],
                    actions=("Add a transition or document the intentional time jump.",)))

        # Plot threads, mysteries, promises, callbacks, and abandonment.
        recent_text = " ".join(_strings(recent)).lower()
        for kind in ("plot_thread", "mystery", "foreshadow"):
            for item in sources[kind]:
                status = str(item.get("status") or "open").lower()
                if status in {"resolved", "closed", "paid_off", "complete", "completed", "archived"}:
                    continue
                title = _author_label(item, kind)
                introduced = item.get("introduced_chapter") or item.get("chapter_number")
                references = list(item.get("references") or [])
                reference_chapters = [
                    int(value)
                    for reference in references
                    if (value := (
                        reference.get("chapter_number")
                        if isinstance(reference, dict)
                        else reference if isinstance(reference, (int, float)) else None
                    )) is not None
                ]
                last_structured_reference = max(
                    reference_chapters
                    + ([int(introduced)] if isinstance(introduced, (int, float)) else [])
                    + [0]
                )
                abandoned = (
                    len(chapters) >= 10
                    and last_structured_reference > 0
                    and int(chapters[-1].get("chapter_number") or len(chapters)) - last_structured_reference >= 10
                )
                severity = "high" if abandoned else "medium"
                category = "abandoned_storyline" if abandoned else "unresolved_thread"
                findings.append(self._finding("plot", category, severity,
                    f"{title} is unresolved" + (" and has no recent development." if abandoned else "."),
                    evidence=[{"status": status, "introduction": introduced, "references": references}],
                    chapters=([introduced] if isinstance(introduced, (int, float)) else []),
                    actions=("Add a development beat or mark the thread intentionally deferred.", "Plan and link a resolution."),
                    elements=(_identity(item),), confidence=.86 if abandoned else (.72 if references else .58)))
        resolved_text = " ".join(str(v).lower() for c in chapters for key in ("important_events", "mysteries_resolved", "foreshadowing_resolved") for v in c.get(key, []))
        for chapter in chapters:
            for promise in chapter.get("future_obligations") or []:
                if str(promise).lower() not in resolved_text:
                    findings.append(self._finding("plot", "unresolved_promise", "medium",
                        f"Promise introduced in Chapter {chapter.get('chapter_number')} has no detected resolution: {promise}",
                        evidence=[promise], chapters=(chapter.get("chapter_number"),),
                        scenes=chapter.get("scene_ids") or [], actions=("Link the promise to a later payoff or explicitly defer it.",)))

        # Character presence and consistency evidence.
        recent_characters = {str(value).lower() for chapter in recent for value in chapter.get("characters_present") or []}
        for character in sources["character"]:
            name = str(character.get("name") or "").strip()
            if not name or str(character.get("current_status") or "active").lower() in {"dead", "departed", "archived"}:
                continue
            present = [int(c.get("chapter_number")) for c in chapters if name.lower() in {str(v).lower() for v in c.get("characters_present") or []}]
            if len(chapters) >= 10 and name.lower() not in recent_characters:
                findings.append(self._finding("character", "character_presence_gap", "medium",
                    f"{name} is active but absent from the latest ten chapters.", evidence=[{"last_presence": max(present) if present else None}],
                    chapters=([max(present)] if present else []), actions=("Confirm the absence is intentional or restore the character's active thread.",), elements=(name,)))
            traits = {str(v).lower() for v in character.get("personality") or []}
            for chapter in chapters:
                for change in chapter.get("character_changes") or []:
                    if str(change.get("character") or "").lower() != name.lower():
                        continue
                    text = str(change.get("change") or change.get("description") or "")
                    contradictions = [trait for trait in traits if re.search(rf"\bnot\s+{re.escape(trait)}\b", text.lower())]
                    if contradictions:
                        findings.append(self._finding("character", "personality_drift", "high",
                            f"{name}'s behavior may contradict established traits.", evidence=[{"traits": sorted(traits), "change": text}],
                            chapters=(chapter.get("chapter_number"),), actions=("Explain the motivation for the shift or revise the behavior.",), elements=(name,), confidence=.58))

        # Approved active prose only: POV continuity and repeated manuscript habits.
        findings.extend(self._prose_findings(sources["scene"], sources["scene_draft"]))

        # Pacing, continuity, and narrative balance.
        word_counts = [int(item.get("word_count") or 0) for item in chapters if int(item.get("word_count") or 0) > 0]
        if len(word_counts) >= 4:
            mean = sum(word_counts) / len(word_counts)
            for chapter in chapters:
                count = int(chapter.get("word_count") or 0)
                if count and (count < mean * .45 or count > mean * 1.8):
                    findings.append(self._finding("pacing", "chapter_length_outlier", "medium",
                        f"Chapter {chapter.get('chapter_number')} is a pacing outlier at {count} words.",
                        evidence=[{"words": count, "project_mean": round(mean)}], chapters=(chapter.get("chapter_number"),),
                        actions=("Review whether the chapter's narrative work justifies its relative length.",)))
        for quality in story_quality_service.compare_chapters(chapters):
            findings.append(self._finding(
                "pacing",
                str(quality.get("category") or "structural_weakness"),
                str(quality.get("severity") or "medium").replace("warning", "medium"),
                str(quality.get("message") or "Narrative structure needs review."),
                evidence=list(quality.get("evidence") or ["chapter-shape analysis"]),
                actions=("Review the cited chapter pattern and vary rhythm, escalation, or structural work where appropriate.",),
            ))
        for report in sources["continuity"]:
            if str(report.get("result") or "PASS").upper() not in {"WARNING", "FAIL"}:
                continue
            chapters_, scenes_ = _locations(report)
            findings.append(self._finding("continuity", "continuity_warning",
                "high" if str(report.get("result")).upper() == "FAIL" else "medium",
                str(report.get("message") or report.get("summary") or "Continuity validation reported an issue."),
                evidence=list(report.get("evidence") or [report.get("findings") or []]), chapters=chapters_, scenes=scenes_,
                actions=("Inspect the cited locations and reconcile the continuity break.",)))
        presence = Counter(str(value) for chapter in chapters for value in chapter.get("characters_present") or [])
        if sum(presence.values()) >= 10 and presence:
            name, count = presence.most_common(1)[0]
            ratio = count / max(1, sum(presence.values()))
            if ratio > .7:
                findings.append(self._finding("balance", "character_presence_imbalance", "medium",
                    f"{name} accounts for {round(ratio * 100)}% of recorded character presence.",
                    evidence=[dict(presence)], actions=("Review whether supporting viewpoints and arcs receive enough narrative space.",), elements=(name,)))
        return findings

    def _deduplicate_findings(self, findings: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        id_to_semantic = {
            str(item.get("finding_id")): str(item.get("semantic_issue_id"))
            for item in findings
            if item.get("finding_id") and item.get("semantic_issue_id")
        }
        representatives: Dict[str, Dict[str, Any]] = {}
        merged_identities: set[str] = set()
        for item in findings:
            source_id = str(item.get("source_finding_id") or "")
            identity = (
                id_to_semantic.get(source_id)
                or str(item.get("semantic_issue_id") or "")
                or source_id
            )
            if not identity:
                normalized_message = " ".join(
                    token for token in re.findall(r"[a-z0-9]+", str(item.get("explanation") or item.get("message") or "").lower())
                    if token not in {"the", "a", "an", "is", "in", "and", "has", "detected", "chapter", "scene"}
                )
                identity = _fingerprint({
                    "domain": item.get("domain"),
                    "category": item.get("category"),
                    "message": normalized_message,
                    "chapters": item.get("affected_chapters") or [],
                    "scenes": item.get("affected_scenes") or [],
                    "elements": item.get("affected_elements") or [],
                })[:32]
            candidate = dict(item)
            candidate["semantic_issue_id"] = identity
            current = representatives.get(identity)
            if current is None:
                representatives[identity] = candidate
                continue
            if SEVERITY_WEIGHT.get(str(candidate.get("severity")), 5) > SEVERITY_WEIGHT.get(str(current.get("severity")), 5):
                candidate, current = current, candidate
                representatives[identity] = current
            current["evidence"] = list(dict.fromkeys(
                _stable(value) for value in [*(current.get("evidence") or []), *(candidate.get("evidence") or [])]
            ))[:12]
            current["recommended_actions"] = list(dict.fromkeys([
                *(current.get("recommended_actions") or []),
                *(candidate.get("recommended_actions") or []),
            ]))[:6]
            current["duplicate_finding_ids"] = list(dict.fromkeys([
                *(current.get("duplicate_finding_ids") or []),
                str(candidate.get("finding_id") or ""),
            ]))
            merged_identities.add(identity)
        # Convert stable evidence markers back to author-readable values only when
        # a merge occurred; unchanged findings retain their original structures.
        for identity, item in representatives.items():
            if identity in merged_identities:
                restored = []
                for value in item.get("evidence") or []:
                    if not isinstance(value, str):
                        restored.append(value)
                        continue
                    try:
                        restored.append(json.loads(value))
                    except json.JSONDecodeError:
                        restored.append(value)
                item["evidence"] = restored
        return list(representatives.values())

    def _scored_findings(self, findings: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """Return one scoring representative for each semantic issue.

        Critique findings can be projections of an existing analysis or audit
        finding. They remain visible because they add improvement guidance, but
        they must not deduct Story Health a second time.
        """
        return self._deduplicate_findings(findings)

    def _scores(self, findings: list[Dict[str, Any]]) -> Dict[str, int]:
        scored_findings = self._scored_findings(findings)
        scores = {}
        for domain in DOMAINS:
            deduction = sum(
                SEVERITY_WEIGHT.get(str(item["severity"]), 5)
                for item in scored_findings
                if item["domain"] == domain
            )
            scores[domain] = max(0, 100 - min(70, deduction))
        scores["overall"] = round(sum(scores.values()) / len(DOMAINS)) if scores else 100
        return scores

    async def analyze(self, db, project_id: str, *, force: bool = False, changed_sources: list[str] | None = None) -> Dict[str, Any]:
        """Coalesce concurrent analysis requests for the same project."""
        lock = self._project_locks.setdefault(project_id, asyncio.Lock())
        async with lock:
            return await self._analyze_locked(
                db,
                project_id,
                force=force,
                changed_sources=changed_sources,
            )

    async def _analyze_locked(self, db, project_id: str, *, force: bool = False, changed_sources: list[str] | None = None) -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        started = datetime.utcnow()
        source_manifest = await self._source_manifest(db, pid)
        latest_event = await db.project_events.find_one(
            {
                "project_id": pid,
                "event_type": {
                    "$nin": [
                        "narrative_analysis_started",
                        "narrative_analysis_completed",
                        "narrative_analysis_failed",
                    ]
                },
            },
            sort=[("_id", -1)],
        )
        event_cursor = str(latest_event["_id"]) if latest_event else None
        if not force and not changed_sources:
            cached = await db.narrative_analysis_snapshots.find_one(
                {"project_id": pid, "snapshot_type": "current"}
            )
            if (
                cached
                and "source_event_cursor" in cached
                and cached.get("source_event_cursor") == event_cursor
                and cached.get("source_manifest") == source_manifest
            ):
                cached = {
                    **cached,
                    "stats": {
                        **dict(cached.get("stats") or {}),
                        "recomputed_nodes": 0,
                        "reused_nodes": int((cached.get("stats") or {}).get("nodes") or 0),
                        "cache_hit": True,
                        "incremental": True,
                        "duration_ms": max(
                            0,
                            round((datetime.utcnow() - started).total_seconds() * 1000, 2),
                        ),
                    },
                }
                return await self.platform(db, project_id, snapshot=cached)
        sources = await self._load_sources(db, pid)
        nodes = [self._node(kind, document) for kind, documents in sources.items() for document in documents]
        previous = {item["node_id"]: item async for item in db.narrative_nodes.find({"project_id": pid})}
        now = datetime.utcnow()
        changed = [node for node in nodes if force or node["node_id"] not in previous or previous[node["node_id"]].get("source_fingerprint") != node["source_fingerprint"]]
        if changed_sources:
            selected = set(changed_sources)
            changed_by_id = {node["node_id"]: node for node in changed}
            for node in nodes:
                if node["source_id"] in selected or node["node_id"] in selected:
                    changed_by_id[node["node_id"]] = node
            changed = list(changed_by_id.values())
        current_ids = {node["node_id"] for node in nodes}
        deleted_ids = set(previous) - current_ids
        if not force and not changed and not deleted_ids:
            cached_snapshot = await db.narrative_analysis_snapshots.find_one(
                {"project_id": pid, "snapshot_type": "current"}
            )
            if cached_snapshot:
                cached_snapshot = {
                    **cached_snapshot,
                    "stats": {
                        **dict(cached_snapshot.get("stats") or {}),
                        "source_documents": len(nodes),
                        "nodes": len(nodes),
                        "recomputed_nodes": 0,
                        "reused_nodes": len(nodes),
                        "duration_ms": max(0, round((datetime.utcnow() - started).total_seconds() * 1000, 2)),
                        "incremental": True,
                        "cache_hit": True,
                    },
                }
                return await self.platform(db, project_id, snapshot=cached_snapshot)
        if current_ids:
            await db.narrative_nodes.delete_many({"project_id": pid, "node_id": {"$nin": list(current_ids)}})
        else:
            await db.narrative_nodes.delete_many({"project_id": pid})
        for node in changed:
            await db.narrative_nodes.update_one({"project_id": pid, "node_id": node["node_id"]},
                {"$set": {**node, "project_id": pid, "analyzed_at": now}}, upsert=True)
        edges = self._edges(nodes)
        if edges:
            await db.narrative_edges.bulk_write(
                [
                    UpdateOne(
                        {"project_id": pid, "edge_id": item["edge_id"]},
                        {"$set": {**item, "project_id": pid, "analyzed_at": now}},
                        upsert=True,
                    )
                    for item in edges
                ],
                ordered=False,
            )
            await db.narrative_edges.delete_many({
                "project_id": pid,
                "edge_id": {"$nin": [item["edge_id"] for item in edges]},
            })
        else:
            await db.narrative_edges.delete_many({"project_id": pid})
        findings = self._analyze(sources)
        current_findings = {item["finding_id"] for item in findings}
        await db.narrative_findings.update_many({
            "project_id": pid,
            "status": {"$in": ["open", "acknowledged"]},
            "finding_id": {"$nin": list(current_findings)},
            "$or": [
                {"finding_type": "analysis"},
                {"finding_type": {"$exists": False}},
            ],
        }, {"$set": {"status": "resolved", "resolved_at": now}})
        for finding in findings:
            await db.narrative_findings.update_one({"project_id": pid, "finding_id": finding["finding_id"]},
                {"$set": {**finding, "project_id": pid, "last_seen_at": now},
                 "$setOnInsert": {"first_seen_at": now, "status": "open"}}, upsert=True)
        active_findings = await db.narrative_findings.find({
            "project_id": pid, "status": {"$in": ["open", "acknowledged"]},
        }).to_list(length=20000)
        active_findings = self._deduplicate_findings(active_findings)
        scored_findings = self._scored_findings(active_findings)
        scores = self._scores(active_findings)
        duration_ms = max(0, round((datetime.utcnow() - started).total_seconds() * 1000, 2))
        snapshot = {
            "project_id": pid, "analysis_id": str(uuid4()), "graph_version": 1,
            "status": "complete", "scores": scores,
            "finding_counts": dict(Counter(item["domain"] for item in active_findings)),
            "scored_finding_counts": dict(Counter(item["domain"] for item in scored_findings)),
            "stats": {"source_documents": len(nodes), "nodes": len(nodes), "edges": len(edges),
                      "findings": len(findings), "active_findings": len(active_findings),
                      "scored_findings": len(scored_findings), "recomputed_nodes": len(changed),
                      "reused_nodes": len(nodes) - len(changed), "duration_ms": duration_ms,
                      "incremental": not force},
            "calculated_at": now,
            "source_event_cursor": event_cursor,
            "source_manifest": source_manifest,
        }
        await db.narrative_analysis_snapshots.update_one({"project_id": pid, "snapshot_type": "current"},
            {"$set": {**snapshot, "snapshot_type": "current"}, "$setOnInsert": {"created_at": now}}, upsert=True)
        await self._record_history(db, pid, snapshot, active_findings, trigger="narrative_analysis")
        return await self.platform(db, project_id, snapshot=snapshot)

    async def refresh_scores(self, db, project_id: str) -> Dict[str, Any]:
        """Re-score the current snapshot after an external shared-finding projection changes."""
        pid = await self._project(db, project_id)
        active = await db.narrative_findings.find({
            "project_id": pid, "status": {"$in": ["open", "acknowledged"]},
        }).to_list(length=20000)
        active = self._deduplicate_findings(active)
        scored = self._scored_findings(active)
        scores = self._scores(active)
        finding_counts = dict(Counter(item.get("domain") for item in active))
        scored_finding_counts = dict(Counter(item.get("domain") for item in scored))
        now = datetime.utcnow()
        await db.narrative_analysis_snapshots.update_one(
            {"project_id": pid, "snapshot_type": "current"},
            {"$set": {
                "scores": scores,
                "finding_counts": finding_counts,
                "scored_finding_counts": scored_finding_counts,
                "stats.active_findings": len(active),
                "stats.scored_findings": len(scored),
                "rescored_at": now,
            }},
        )
        snapshot = await db.narrative_analysis_snapshots.find_one(
            {"project_id": pid, "snapshot_type": "current"}
        ) or {}
        history_snapshot = {
            **snapshot,
            "analysis_id": str(uuid4()),
            "scores": scores,
            "finding_counts": finding_counts,
            "calculated_at": now,
            "stats": {**dict(snapshot.get("stats") or {}), "score_refresh": True},
        }
        await self._record_history(db, pid, history_snapshot, active, trigger="finding_status_change")
        return {"scores": scores, "finding_counts": finding_counts, "rescored_at": now.isoformat()}

    async def platform(self, db, project_id: str, *, snapshot: Dict[str, Any] | None = None) -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        if snapshot is None:
            snapshot = await db.narrative_analysis_snapshots.find_one({"project_id": pid, "snapshot_type": "current"})
        if not snapshot:
            return await self.analyze(db, project_id)
        findings = await db.narrative_findings.find({"project_id": pid, "status": {"$in": ["open", "acknowledged"]}}).sort([("severity", 1), ("first_seen_at", 1)]).to_list(length=10000)
        findings = self._deduplicate_findings(findings)
        domains = {domain: [item for item in findings if item.get("domain") == domain] for domain in DOMAINS}
        return _serialize({"snapshot": snapshot, "findings": findings, "domains": domains})

    async def set_finding_status(self, db, project_id: str, finding_id: str, status: str) -> Dict[str, Any]:
        pid = await self._project(db, project_id)
        if status not in {"open", "acknowledged", "deferred", "resolved"}:
            raise ValueError("Unsupported finding status")
        result = await db.narrative_findings.find_one_and_update(
            {"project_id": pid, "finding_id": finding_id},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}, return_document=True)
        if not result:
            raise ValueError("Narrative finding not found")
        await self.refresh_scores(db, project_id)
        return _serialize(result)


narrative_analysis_engine = NarrativeAnalysisEngine()
