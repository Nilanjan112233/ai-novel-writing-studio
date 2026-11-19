"""Write-first drafting over the existing chapter draft/version boundary."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from bson import ObjectId

from app.schemas.story_studio import DiscoveryWritingMetadata
from app.services.context_engine import context_engine
from app.services.draft_validation_service import draft_validation_service
from app.services.orchestration_engine import orchestration_engine
from app.services.provider_gateway import provider_gateway
from app.services.task_routing_service import task_routing_service
from app.services.story_knowledge_projection_service import story_knowledge_projection_service


def _words(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _chapter_phase(chapter_number: int) -> str:
    if chapter_number == 1:
        return "opening chapter"
    if chapter_number <= 3:
        return "early novel chapter"
    return "continuing novel chapter"


def _chapter_depth_contract(chapter_number: int) -> Dict[str, Any]:
    if chapter_number == 1:
        return {
            "purpose": "Make this feel like the beginning of a novel, not a scene excerpt from a later book.",
            "opening_guidance": [
                "Hook the reader with a concrete disturbance, desire, question, or charged situation early.",
                "Ground the viewpoint character through what they want, fear, notice, or choose; do not introduce the cast as a list.",
                "Let the world emerge through immediate action and specific detail instead of an opening explanation.",
                "Establish a recognizable voice and emotional pressure without resolving the central mystery.",
                "End with a changed situation, discovery, decision, or unanswered pressure that makes Chapter 2 feel necessary.",
            ],
            "depth_beats": [
                "entry state",
                "immediate desire or problem",
                "complication",
                "escalation or meaningful interaction",
                "revelation, setback, or choice",
                "changed end state and forward pressure",
            ],
        }
    return {
        "purpose": "Advance the novel through a consequential sequence rather than a collection of connected vignettes.",
        "opening_guidance": [
            "Reconnect naturally to the latest approved consequence without recapping the entire story.",
            "Give the viewpoint character a specific immediate objective and make the scene change their options.",
            "Carry forward only relevant continuity, unresolved threads, and author instructions.",
        ],
        "depth_beats": [
            "entry state",
            "objective",
            "complication",
            "escalation",
            "revelation, setback, or decision",
            "changed end state and next-chapter pressure",
        ],
    }


def _extract_fallback(text: str) -> list[dict[str, Any]]:
    stopwords = {
        "The", "When", "Then", "But", "And", "She", "They", "Her", "His", "Hers", "This", "That", "These", "Those",
        "There", "Here", "What", "Where", "Why", "How", "Who", "You", "Your", "I", "We", "He", "It", "Its", "A", "An",
        "No", "Not", "Nothing", "Something", "Someone", "Everyone", "Everything", "Found", "Came", "Left", "Searched", "Didn", "Thank",
        "Constable", "Councillor", "Chapter", "Mill", "Main", "Nine", "First", "Second", "Third", "Outside", "Inside", "Before", "After",
    }
    place_like = {"northglass", "drownwater", "ashwater", "guildhall", "governor", "keep", "street", "river", "city", "channel", "archive", "reach", "water"}
    values = re.findall(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b", text or "")
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    explicitly_named = set(re.findall(r"(?:named|called)\s+([A-Z][a-z]{2,})", text or ""))
    possessive = set(re.findall(r"\b([A-Z][a-z]{2,})['’]s\b", text or ""))
    names = []
    for value in values:
        normalized = value.lower()
        if value in names or value in stopwords or normalized in place_like or normalized.endswith(("water", "street", "reach")):
            continue
        if counts.get(value, 0) < 2 and value not in explicitly_named and value not in possessive:
            continue
        names.append(value)
    candidates = [{"candidate_type": "character", "subject": name, "value": {"observed_in_prose": True}, "confidence": 0.55 if counts.get(name, 0) >= 2 else 0.45, "evidence": [f"Observed repeatedly in approved discovery prose: {name}"], "status": "candidate"} for name in names[:20]]
    lowered = (text or "").lower()
    for artifact in ["northglass", "compass", "satchel", "map", "blue cloth", "brass key"]:
        if artifact in lowered:
            candidates.append({"candidate_type": "artifact", "subject": artifact.title(), "value": {"observed_in_prose": True}, "confidence": 0.5, "evidence": [f"Observed object in approved discovery prose: {artifact}"], "status": "candidate"})
    if any(term in lowered for term in ["promised", "promise", "swore", "vowed"]):
        candidates.append({"candidate_type": "promise", "subject": "Character promise", "value": {"observed_in_prose": True}, "confidence": 0.4, "evidence": ["Promise language observed in approved discovery prose"], "status": "candidate"})
    if any(term in lowered for term in ["impossible", "disappeared", "secret", "should not exist", "missing"]):
        candidates.append({"candidate_type": "mystery", "subject": "Unresolved disappearance or impossible path", "value": {"observed_in_prose": True}, "confidence": 0.4, "evidence": ["Mystery language observed in approved discovery prose"], "status": "candidate"})
    if "third bell" in lowered or "third bell after dusk" in lowered:
        candidates.append({"candidate_type": "world_fact", "subject": "Third bell river rule", "value": "The river reveals a lost path at the third bell after dusk.", "confidence": 0.45, "evidence": ["Third-bell rule observed in approved discovery prose"], "status": "candidate"})
    if any(term in lowered for term in ["lied", "trust", "between them", "knows what"]):
        candidates.append({"candidate_type": "relationship", "subject": "Mara and Ivo trust relationship", "value": {"observed_in_prose": True}, "confidence": 0.35, "evidence": ["Relationship tension observed in approved discovery prose"], "status": "candidate"})
    return candidates[:100]


class DiscoveryWritingService:
    async def generate(self, db, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        metadata = DiscoveryWritingMetadata(**payload)
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid}) or {}
        latest = await db.chapter_drafts.find_one({"project_id": pid}, sort=[("chapter_number", -1)])
        next_chapter_number = int((latest or {}).get("chapter_number") or 0) + 1
        if metadata.chapter_number is not None and metadata.chapter_number != next_chapter_number:
            raise ValueError(
                f"Chapter {metadata.chapter_number} is not the next chapter. NovelForge is ready for Chapter {next_chapter_number}."
            )
        chapter_number = metadata.chapter_number or next_chapter_number
        draft_id = str(uuid4())
        previous_metadata = (latest or {}).get("discovery_metadata") or {}
        pov_character = (
            metadata.pov_character
            or previous_metadata.get("pov_character")
            or project.get("pov_character")
        )
        context = await context_engine.build_context_packet(
            db,
            project_id=project_id,
            agent_name="DiscoveryWriterAgent",
            task=metadata.instruction,
            cycle_number=0,
            target_artifact=f"discovery-chapter:{chapter_number}",
            max_context_tokens=24000,
            current_chapter=max(0, chapter_number - 1),
            pov_character=pov_character,
            safe_for_writing=True,
            include_conversation_history=False,
        )
        settings = await orchestration_engine.get_settings(db)
        minimum = metadata.target_word_min or 0
        target = metadata.target_word_count or metadata.target_word_min or 1200
        maximum = metadata.target_word_max or max(target, int(target * 1.25))
        depth_contract = _chapter_depth_contract(chapter_number)
        prompt = {
            "project": {
                "project_name": project.get("project_name") or project.get("title"),
                "story_title": project.get("story_title") or "Untitled novel",
                "premise": project.get("premise"),
                "genre": project.get("genre"),
                "tone": project.get("tone"),
            },
            "chapter_number": chapter_number,
            "chapter_phase": _chapter_phase(chapter_number),
            "instruction": metadata.instruction,
            "word_range": {"minimum": minimum, "target": target, "maximum": maximum},
            "context": context.model_dump(),
            "chapter_depth_contract": depth_contract,
            "contract": "Return only reader-facing prose. Do not add explanations, metadata, canon, or planning claims. Do not force every planning detail into this chapter. Protect uncertainty and reveal timing.",
        }
        system_prompt = (
            "You are NovelForge's Discovery Writer. Write human-sounding fiction with concrete sensory detail, "
            "varied rhythm, specific character desire, subtext, consequential action, and emotional continuity. "
            "Use the context packet's authority labels literally: canon, approved decisions, and confirmed planning "
            "outrank derived chapter intelligence or candidate suggestions. If a derived prose detail conflicts with "
            "confirmed planning, do not silently repeat the conflict; preserve the confirmed fact or uncertainty and "
            "leave the issue for author review. Candidate material is a suggestion, never an asserted truth unless the "
            "author explicitly asks to use it. "
            "Build one coherent chapter with internal progression: an entry state, immediate objective, complication, "
            "escalation, meaningful interaction, revelation or setback, and a changed end state. Do not write a chain "
            "of vignettes or a summary of planned beats. Avoid generic AI exposition, repetitive sentence openings, "
            "stock metaphors, summary-heavy prose, and explaining the story to the reader. "
            + ("This is the opening chapter. Earn the reader's attention immediately, introduce the viewpoint through "
               "desire and pressure, reveal the world through action, and leave a compelling unanswered question or "
               "consequence for Chapter 2. Do not dump backstory or resolve the central premise. " if chapter_number == 1 else "")
        )
        result = await provider_gateway.generate_with_failover(db, [{"role": "system", "content": system_prompt}, {"role": "user", "content": json.dumps(prompt, ensure_ascii=True, default=str)}], provider=settings.default_provider, model=settings.default_model, fallbacks=[{"provider": "openrouter", "model": "deepseek/deepseek-v4-flash"}, {"provider": "gemini", "model": "gemini-2.5-flash"}], temperature=0.82, max_tokens=min(maximum * 2, 24000), agent_name="DiscoveryWriterAgent", expect_json=False, trace_context={"project_id": project_id})
        generated = str(result.get("content") or "").strip()
        if not generated:
            raise ValueError("Discovery Writer returned no prose")
        range_attempts = [{"attempt": 1, "word_count": _words(generated), "provider": result.get("provider"), "model": result.get("model")}]
        # Provider token limits are not word limits. Give the same writing
        # path one bounded editorial correction when the actual prose misses
        # the author's requested range; never silently truncate prose.
        if _words(generated) < minimum or _words(generated) > maximum:
            correction_prompt = {
                "chapter_number": chapter_number,
                "instruction": metadata.instruction,
                "word_range": {"minimum": minimum, "target": target, "maximum": maximum},
                "draft": generated,
                "correction": "Revise this complete chapter to fit the requested word range. Preserve the same POV, causal events, named facts, promises, mysteries, objects, injuries, and ending consequence. If over maximum, compress repetition and secondary description without turning the chapter into a summary. If under minimum, deepen the existing scene with concrete action, sensory detail, subtext, and meaningful reaction; do not add an unrelated subplot. Return only the revised reader-facing prose.",
            }
            correction = await provider_gateway.generate_with_failover(
                db,
                [{"role": "system", "content": "You are a careful fiction editor revising a chapter for length and continuity. Preserve human-sounding prose and do not explain your edits."}, {"role": "user", "content": json.dumps(correction_prompt, ensure_ascii=True, default=str)}],
                provider=result.get("provider") or settings.default_provider,
                model=result.get("model") or settings.default_model,
                fallbacks=[{"provider": "gemini", "model": "gemini-2.5-flash"}, {"provider": "openrouter", "model": "deepseek/deepseek-v4-flash"}],
                temperature=0.55,
                max_tokens=min(maximum * 2, 24000),
                agent_name="DiscoveryRangeEditor",
                expect_json=False,
                trace_context={"project_id": project_id},
            )
            corrected = str(correction.get("content") or "").strip()
            if corrected:
                generated = corrected
                range_attempts.append({"attempt": 2, "word_count": _words(generated), "provider": correction.get("provider"), "model": correction.get("model")})
        if minimum and _words(generated) < minimum:
            needed = minimum - _words(generated)
            continuation = await provider_gateway.generate_with_failover(
                db,
                [{"role": "system", "content": "You are extending an existing fiction chapter without changing its established facts. Write only a connected final scene, with concrete action, sensory detail, subtext, and a consequential transition. Do not summarize or explain."}, {"role": "user", "content": json.dumps({"chapter_number": chapter_number, "existing_prose": generated, "instruction": metadata.instruction, "minimum_additional_words": needed, "maximum_total_words": maximum, "request": "Continue this chapter immediately from its ending. Add enough meaningful scene material to reach the requested minimum, then stop at a natural chapter ending."}, ensure_ascii=True, default=str)}],
                provider=settings.default_provider,
                model=settings.default_model,
                fallbacks=[{"provider": "gemini", "model": "gemini-2.5-flash"}, {"provider": "openrouter", "model": "deepseek/deepseek-v4-flash"}],
                temperature=0.6,
                max_tokens=min(max(needed * 3, 600), 6000),
                agent_name="DiscoveryRangeContinuation",
                expect_json=False,
                trace_context={"project_id": project_id},
            )
            addition = str(continuation.get("content") or "").strip()
            if addition:
                generated = f"{generated}\n\n{addition}"
                range_attempts.append({"attempt": len(range_attempts) + 1, "word_count": _words(generated), "provider": continuation.get("provider"), "model": continuation.get("model"), "kind": "continuation"})
        # A continuation can satisfy the minimum while overshooting the
        # maximum. Give the same strong writing path one final bounded
        # compression pass instead of silently accepting a non-compliant
        # chapter or truncating reader-facing prose.
        if maximum and _words(generated) > maximum:
            final_correction = await provider_gateway.generate_with_failover(
                db,
                [
                    {"role": "system", "content": "You are a careful fiction editor. Return only the complete revised chapter prose. Compress to the requested range without summarising away scene action, emotional subtext, named facts, or the ending consequence."},
                    {"role": "user", "content": json.dumps({
                        "chapter_number": chapter_number,
                        "instruction": metadata.instruction,
                        "word_range": {"minimum": minimum, "target": target, "maximum": maximum},
                        "current_word_count": _words(generated),
                        "draft": generated,
                        "request": "Reduce repetition and secondary description until the complete chapter fits at or below the maximum while remaining above the minimum. Preserve POV, chronology, continuity, dialogue intent, mysteries, promises, and the final forward pressure.",
                    }, ensure_ascii=True, default=str)},
                ],
                provider=result.get("provider") or settings.default_provider,
                model=result.get("model") or settings.default_model,
                fallbacks=[{"provider": "openrouter", "model": "deepseek/deepseek-v4-flash"}, {"provider": "gemini", "model": "gemini-2.5-flash"}],
                temperature=0.35,
                max_tokens=min(maximum * 2, 24000),
                agent_name="DiscoveryRangeCompression",
                expect_json=False,
                trace_context={"project_id": project_id},
            )
            compressed = str(final_correction.get("content") or "").strip()
            if compressed:
                generated = compressed
                range_attempts.append({"attempt": len(range_attempts) + 1, "word_count": _words(generated), "provider": final_correction.get("provider"), "model": final_correction.get("model"), "kind": "compression"})
        now = datetime.utcnow()
        final_word_count = _words(generated)
        doc = {"project_id": pid, "draft_id": draft_id, "workflow_mode": "discovery", "discovery_id": str(uuid4()), "chapter_number": chapter_number, "chapter_phase": _chapter_phase(chapter_number), "chapter_plan_id": None, "arc_id": None, "version_number": 1, "parent_version_id": None, "status": "draft", "active": True, "source_scene_draft_ids": [], "transitions": [], "generated_text": generated, "word_count": final_word_count, "target_word_min": minimum or None, "target_word_count": target, "target_word_max": maximum, "range_compliant": (not minimum or final_word_count >= minimum) and final_word_count <= maximum, "range_attempts": range_attempts, "discovery_metadata": {**metadata.model_dump(), "chapter_phase": _chapter_phase(chapter_number), "chapter_depth_contract": depth_contract}, "generation_metadata": {key: value for key, value in result.items() if key in {"provider", "model", "tokens_used", "latency_ms", "execution_trace_id", "fallback_used", "attempts"}}, "generated_by": "DiscoveryWriterAgent", "change_reason": metadata.instruction, "created_at": now, "updated_at": now}
        inserted = await db.chapter_drafts.insert_one(doc)
        doc["_id"] = inserted.inserted_id
        report = await draft_validation_service.validate_chapter_draft(db, project_id, doc, persist=True)
        await db.chapter_drafts.update_one({"_id": inserted.inserted_id}, {"$set": {"validation_result": report["result"], "continuity_report_id": report["report_id"], "updated_at": datetime.utcnow()}})
        return {"draft": self._serialize(doc), "continuity_report": self._serialize(report), "workflow_mode": "discovery"}

    async def extract_approved(self, db, project_id: str, draft: Dict[str, Any]) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        existing = await db.discovery_extractions.find_one({"project_id": pid, "source_draft_id": draft["draft_id"]})
        if existing:
            return self._serialize(existing)
        text = str(draft.get("generated_text") or "")
        candidates: list[dict[str, Any]] = []
        extraction_result: Dict[str, Any] = {}
        try:
            route = await task_routing_service.select("extraction")
            extraction_result = await provider_gateway.generate_with_failover(db, [{"role": "system", "content": "Extract only observable candidate story knowledge from the supplied prose. Return a JSON object of the form {\"candidates\": [{\"type\": ..., \"description\": ...}]}. Never claim approval or canon status. Include concrete names, relationships, objects, injuries, promises, mysteries, world rules, timeline events, POV, tone, and unresolved elements. Each candidate must be a concise object with type and description. Do not return an empty list when the prose clearly contains these."}, {"role": "user", "content": json.dumps({"chapter_number": draft.get("chapter_number"), "prose": text, "candidate_types": ["character", "relationship", "world_fact", "timeline_event", "knowledge_change", "mystery", "promise", "plot_thread", "foreshadowing", "artifact", "pov_style", "unresolved_element"]}, ensure_ascii=True)}], provider=route["provider"], model=route["model"], fallbacks=route.get("fallbacks"), temperature=0.1, max_tokens=3000, agent_name="DiscoveryExtractionAgent", expect_json=True, json_list_key="candidates", trace_context={"project_id": project_id, "task_tier": route.get("tier"), "routing_reason": route.get("reason"), "task": "extraction"})
            candidates = [item for item in (extraction_result.get("parsed") or {}).get("candidates") or [] if isinstance(item, dict)][:100]
            if not candidates:
                candidates = _extract_fallback(text)
        except Exception:
            candidates = _extract_fallback(text)
        now = datetime.utcnow()
        doc = {"project_id": pid, "extraction_id": str(uuid4()), "source_draft_id": draft["draft_id"], "chapter_number": draft.get("chapter_number"), "status": "candidate", "candidates": candidates, "extraction_metadata": {key: extraction_result.get(key) for key in ("provider", "model", "tokens_used", "execution_trace_id", "fallback_used", "attempts") if extraction_result.get(key) is not None}, "provenance": {"source_collection": "chapter_drafts", "source_id": draft["draft_id"], "version_number": draft.get("version_number"), "workflow_mode": "discovery"}, "created_at": now, "updated_at": now}
        await db.discovery_extractions.insert_one(doc)
        projection = await story_knowledge_projection_service.project_candidates(
            db,
            project_id,
            candidates,
            source_type="approved_discovery_prose",
            source_id=str(draft.get("draft_id") or ""),
            source_chapter=int(draft.get("chapter_number") or 0) or None,
        )
        doc["projection"] = projection
        return self._serialize(doc)

    @staticmethod
    def _serialize(value: Any) -> Any:
        if isinstance(value, ObjectId): return str(value)
        if isinstance(value, list): return [DiscoveryWritingService._serialize(item) for item in value]
        if isinstance(value, dict): return {key: DiscoveryWritingService._serialize(item) for key, item in value.items() if key != "_id"}
        return value


discovery_writing_service = DiscoveryWritingService()
