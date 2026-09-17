"""Conversation-first author entry point over existing NovelForge services."""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Dict
from uuid import uuid4

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.schemas.story_studio import (
    MutationClass,
    StoryIntent,
    StoryStudioIntent,
    StoryStudioRequest,
)
from app.services.narrative_interaction_service import narrative_interaction_service
from app.services.project_event_service import emit_project_event
from app.services.provider_gateway import provider_gateway
from app.services.task_routing_service import task_routing_service
from app.services.story_knowledge_projection_service import story_knowledge_projection_service
from app.services.discovery_writing_service import discovery_writing_service
from app.services.narrative_critique_service import narrative_critique_service
from app.services.editorial_service import editorial_service
from app.services.drafting_service import drafting_service
from app.services.development_state_service import development_state_service
from app.services.memory_provider import memory_provider_service
import json


class StoryStudioService:
    """Routes conversation without allowing model text to mutate authority."""

    @staticmethod
    def classify(query: str, *, allow_mutations: bool) -> StoryStudioIntent:
        text = " ".join((query or "").lower().split())
        if any(phrase in text for phrase in ("what should i work on next", "what should i do next", "continue writing", "where do i go")):
            return StoryStudioIntent(intent=StoryIntent.NAVIGATE, explanation="This request asks for a next action or destination.")
        if any(phrase in text for phrase in ("find contradictions", "is there a contradiction", "check continuity", "review my story", "are we repeating", "too generic", "too similar", "what is distinctive", "does this feel", "does this work as a first chapter", "opening chapter", "chapter 1 quality")):
            return StoryStudioIntent(intent=StoryIntent.REVIEW, explanation="This request asks NovelForge to inspect existing story evidence.")
        if any(phrase in text for phrase in ("give me alternatives", "explore alternatives", "brainstorm", "what if", "ideas for")):
            return StoryStudioIntent(intent=StoryIntent.BRAINSTORM, explanation="This request asks for possibilities, not a story mutation.")
        explicitly_non_mutating = any(phrase in text for phrase in ("do not change", "don't change", "without changing", "no mutation", "do not modify", "without modifying"))
        question_prefix = bool(re.match(r"^(why|what|how|does|can|is|are|tell me|explain)\b", text))
        revision_language = any(phrase in text for phrase in ("rewrite", "revise", "doesn't feel", "does not feel", "too dramatic", "too abrupt", "less ai", "less artificial", "humanize", "human-written", "human written", "human prose", "make it more natural", "feel more natural", "make it quieter", "make it more tense", "boring", "improve", "reduce repetitive"))
        chapter_revision_request = bool(re.search(r"\bchapter\s+\d+\b", text)) and revision_language and not (question_prefix and not any(phrase in text for phrase in ("rewrite", "revise", "humanize", "make it", "feel more natural")))
        if chapter_revision_request and not explicitly_non_mutating:
            return StoryStudioIntent(intent=StoryIntent.MODIFY, mutation_class=MutationClass.PROPOSAL, confidence=0.9, requires_author_decision=False, explanation="This is a chapter revision request. NovelForge will prepare a protected version for review.")
        if any(phrase in text for phrase in ("why does", "explain", "what happened", "what is", "who is", "how does", "tell me about")):
            return StoryStudioIntent(intent=StoryIntent.RETRIEVE_EXPLAIN, explanation="This request asks for an explanation grounded in the existing story.")
        development_request = any(phrase in text for phrase in (
            "develop the story", "develop my story", "continue developing",
            "build the first arc", "develop the characters", "develop the relationships",
            "develop the world", "plan the first", "plan up to chapter",
            "flesh this out", "rework the first arc", "develop this story",
        ))
        if development_request:
            return StoryStudioIntent(
                intent=StoryIntent.DEVELOP,
                mutation_class=MutationClass.PROPOSAL,
                confidence=0.94,
                requires_author_decision=False,
                explanation="This asks the existing story-development workflow to expand confirmed planning without silently changing canon.",
            )
        mutation_markers = ("change ", "make ", "modify ", "update ", "rewrite ", "develop ", "reconsider ", "remove ", "add ")
        if not explicitly_non_mutating and any(marker in text for marker in mutation_markers):
            if not allow_mutations:
                return StoryStudioIntent(
                    intent=StoryIntent.AUTHOR_DECISION_REQUIRED,
                    mutation_class=MutationClass.AMBIGUOUS,
                    confidence=0.72,
                    requires_author_decision=True,
                    explanation="This could change authoritative story state, so NovelForge needs confirmation before applying it.",
                )
            return StoryStudioIntent(
                intent=StoryIntent.MODIFY,
                mutation_class=MutationClass.EXPLICIT_MUTATION,
                confidence=0.72,
                requires_author_decision=True,
                explanation="This request may change story state and must pass through a governed proposal or decision.",
            )
        if any(phrase in text for phrase in ("write ", "start writing", "continue the chapter", "continue the scene")):
            return StoryStudioIntent(intent=StoryIntent.WRITE, explanation="This request asks for prose and should open the governed writing flow.")
        return StoryStudioIntent(intent=StoryIntent.ANSWER, explanation="This request is treated as a grounded story question unless the author clarifies otherwise.")

    async def _chapter_revision(self, db, project_id: str, query: str, model_preference: str = "auto") -> Dict[str, Any] | None:
        match = re.search(r"\bchapter\s+(\d+)\b", query, flags=re.IGNORECASE)
        if not match:
            return None
        chapter_number = int(match.group(1))
        draft = await db.chapter_drafts.find_one({"project_id": ObjectId(project_id), "chapter_number": chapter_number, "active": True, "status": {"$in": ["draft", "review", "approved"]}})
        if not draft:
            return {"error": f"I could not find a reviewable Chapter {chapter_number}. No prose was changed."}
        if draft.get("status") == "draft":
            # Editorial branches require a reviewable source. Moving an
            # unapproved generated draft into review preserves the source and
            # makes the requested polish safe to inspect before approval.
            transitioned = await drafting_service.transition(
                db,
                project_id,
                "chapter",
                draft["draft_id"],
                "review",
                reason="Prepared for author-requested Story Studio revision",
            )
            draft = transitioned.get("draft") or draft
        await editorial_service.request_review(db, project_id, subject_type="chapter", subject_id=draft["draft_id"], report_type="editorial")
        humanization = any(term in query.lower() for term in ("humanize", "less ai", "less artificial", "more natural", "natural sentence", "human written"))
        protected_guidance = (
            " Polish only where it improves the reading experience: vary sentence rhythm and paragraph cadence, remove generic sensory filler, repeated gestures, over-explained emotion, formulaic dialogue tags, unnecessary em dashes, and recap. Preserve voice, POV, meaning, named facts, chronology, dialogue intent, foreshadowing, and the scene outcome. Do not rewrite every sentence merely to make it different."
            if humanization else ""
        )
        branch = await editorial_service.create_branch(
            db, project_id, source_draft_type="chapter", source_draft_id=draft["draft_id"],
            title=f"Story Studio revision: {query[:70]}", revision_pass="style" if humanization or any(term in query.lower() for term in ("ai", "artificial", "natural", "human")) else "development",
        )
        revision = await editorial_service.generate_revision(
            db, project_id, branch["branch_id"],
            change_reason=(
                f"Author request from Story Studio: {query}. Preserve canon, approved decisions, chronology, POV, protected knowledge boundaries, and the chapter's intended outcome. Create a reviewable alternative; do not overwrite the source.{protected_guidance}"
            ),
            revision_pass=branch.get("revision_pass"),
            model_preference=model_preference,
        )
        return {"chapter_number": chapter_number, "draft_id": draft["draft_id"], "branch": branch, "revision": revision}

    @staticmethod
    def _looks_like_planning(query: str, intent: StoryStudioIntent) -> bool:
        if intent.intent in {StoryIntent.BRAINSTORM, StoryIntent.RETRIEVE_EXPLAIN, StoryIntent.REVIEW, StoryIntent.NAVIGATE, StoryIntent.WRITE}:
            return False
        text = " ".join((query or "").lower().split())
        return any(marker in text for marker in (
            "protagonist", "main character", "missing brother", "relationship", "central mystery",
            "main mystery", "story arc", "first arc", "reveal around", "chapter 10", "should be",
            "is important", "setting", "location", "world rule", "plot thread", "promise",
            "opening", "funeral", "emotional", "morally grey", "morally gray", "supernatural",
            "political layer", "future reveal", "reveal later", "become important", "distinctive",
            "memory can", "the story should", "i want the", "i want mara", "i want ivo",
        ))

    @staticmethod
    def _clarification_prompt(query: str, intent: StoryStudioIntent) -> str | None:
        """Ask only when a vague creative phrase has materially different meanings."""
        text = " ".join((query or "").lower().split())
        if intent.intent not in {StoryIntent.MODIFY, StoryIntent.DEVELOP, StoryIntent.RECONSIDER, StoryIntent.AUTHOR_DECISION_REQUIRED}:
            return None
        has_target = bool(re.search(r"\b(chapter|scene|character|relationship|mystery|arc|opening|ending|protagonist|mara|ivo|elias)\b", text))
        if "darker" in text and not any(term in text for term in ("emotion", "violent", "violence", "myster", "tragic", "tone", "grim")):
            return "When you say darker, should the change be mainly emotional, more mysterious, more tragic, or more physically dangerous?"
        if any(phrase in text for phrase in ("make it better", "fix it", "not right", "change something", "improve this")) and not has_target:
            return "What should I focus on: the prose, the pacing, the character emotion, or the story direction?"
        return None

    async def _capture_planning(self, db, project_id: str, query: str) -> Dict[str, Any]:
        route = await task_routing_service.select("planning_capture")
        messages = [
            {"role": "system", "content": "Extract only concrete story-planning candidates from the author's message. Return JSON with candidates. Each candidate must contain type and description. Allowed types: character, relationship, world_fact, mystery, plot_thread, timeline_event, artifact, arc, knowledge_change, author_intention. Do not treat ideas as canon, do not invent missing details, and return an empty list for brainstorming or vague discussion."},
            {"role": "user", "content": json.dumps({"author_message": query}, ensure_ascii=True)},
        ]
        try:
            result = await provider_gateway.generate_with_failover(
                db, messages, provider=route["provider"], model=route["model"], fallbacks=route.get("fallbacks"),
                temperature=0.1, max_tokens=1200, agent_name="StoryPlanningCapture", expect_json=True,
                trace_context={"task": "planning_capture", "task_tier": route.get("tier"), "routing_reason": route.get("reason")},
            )
            candidates = [item for item in (result.get("parsed") or {}).get("candidates") or [] if isinstance(item, dict)][:30]
            deterministic: list[Dict[str, Any]] = []
            normalized_query = " ".join((query or "").split())
            protagonist = re.search(r"(?:the\s+)?protagonist\s+is\s+([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)?)", normalized_query)
            if protagonist:
                deterministic.append({"type": "character", "subject": protagonist.group(1), "description": f"{protagonist.group(1)} is the protagonist.", "confidence": 1.0, "evidence": [query]})
            missing = re.search(r"(?:missing|disappeared|lost)\s+(?:brother|sister|father|mother|friend)\s+([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)?)", normalized_query, flags=re.IGNORECASE)
            if missing:
                relation_word = re.search(r"(?:missing|disappeared|lost)\s+(brother|sister|father|mother|friend)", normalized_query, flags=re.IGNORECASE)
                relation = relation_word.group(1) if relation_word else "relative"
                deterministic.append({"type": "character", "subject": missing.group(1), "description": f"{missing.group(1)} is the author's stated missing {relation}.", "confidence": 1.0, "evidence": [query]})
            relationship = re.search(r"\b([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)?)\s+(distrusts|trusts|loves|hates|protects|fears|avoids|follows|owes|needs)\s+([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)?)\b", normalized_query)
            if relationship:
                deterministic.append({"type": "relationship", "subject": f"{relationship.group(1)} and {relationship.group(3)}", "description": relationship.group(0), "confidence": 1.0, "evidence": [query]})
            world_fact = re.search(r"\b([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)?)\s+is\s+(?:a|an|the)\s+([^.;]+)", normalized_query)
            if world_fact and any(term in world_fact.group(2).lower() for term in ("city", "river", "kingdom", "world", "dangerous", "rule", "place", "district")):
                deterministic.append({"type": "world_fact", "subject": world_fact.group(1), "description": world_fact.group(0), "confidence": 1.0, "evidence": [query]})
            reveal = re.search(r"(?:reveal|resolution|truth|discovery)\s+(?:that\s+)?(.{3,120}?)\s+(?:around|by|in)\s+Chapter\s+(\d+)", normalized_query, flags=re.IGNORECASE)
            if reveal:
                detail = f"{reveal.group(1).strip()} around Chapter {reveal.group(2)}."
                deterministic.extend([
                    {"type": "plot_thread", "subject": detail, "description": detail, "confidence": 1.0, "evidence": [query]},
                    {"type": "timeline_event", "subject": detail, "description": detail, "confidence": 1.0, "evidence": [query]},
                ])
            merged: list[Dict[str, Any]] = []
            seen: set[tuple[str, str]] = set()
            for item in [*deterministic, *candidates]:
                key = (str(item.get("type") or item.get("candidate_type") or "").lower(), " ".join(str(item.get("description") or item.get("value") or item.get("subject") or "").lower().split()))
                if key[0] and key[1] and key not in seen:
                    seen.add(key)
                    merged.append(item)
            candidates = merged[:30]
            projection = await story_knowledge_projection_service.project_candidates(
                db, project_id, candidates, source_type="story_studio_planning", source_id=result.get("execution_trace_id"),
            )
            return {"status": "suggestion", "candidates": candidates, "projection": projection, "provider": result.get("provider"), "model": result.get("model"), "execution_trace_id": result.get("execution_trace_id")}
        except Exception as exc:
            return {"status": "unavailable", "candidates": [], "projection": {"counts": {}, "projected": []}, "error": str(exc)}

    async def _creative_review(self, db, project_id: str, query: str) -> Dict[str, Any]:
        """Use the existing critique/analysis owner for evidence-backed creative guidance."""
        critique = await narrative_critique_service.refresh(db, project_id, include_latest_agent_audit=False)
        findings = [
            item for item in critique.get("findings") or []
            if item.get("finding_type") == "critique"
        ]
        lowered = query.lower()
        focus_terms = {
            "repetition": ("repetitive", "repeating", "same structure", "again and again"),
            "genericness": ("generic", "similar", "familiar", "obvious"),
            "opening": ("first chapter", "opening", "chapter 1", "hook"),
            "distinctiveness": ("distinctive", "memorable", "original", "stand out"),
        }
        focus = next((name for name, terms in focus_terms.items() if any(term in lowered for term in terms)), "overall")
        selected = [
            item for item in findings
            if (
                focus == "repetition" and ("repetitive" in str(item.get("category")) or "pattern" in str(item.get("category")))
            ) or (
                focus == "genericness" and ("generic" in str(item.get("category")) or "exposition" in str(item.get("category")) or "repetitive" in str(item.get("category")))
            ) or (
                focus == "opening" and (item.get("category") in {"weak_chapter_hook", "weak_chapter_ending"} or 1 in (item.get("affected_chapters") or []))
            )
        ]
        if focus == "overall":
            selected = findings[:8]
        selected = selected[:8]
        pid = ObjectId(project_id)
        authority_query = {"$or": [{"authority_status": {"$exists": False}}, {"authority_status": {"$in": ["confirmed", "approved", "active"]}}]}
        characters = await db.character_bibles.find({"project_id": pid, **authority_query}).sort("updated_at", -1).to_list(length=8)
        worlds = await db.world_bibles.find_one({"project_id": pid}) or {}
        mysteries = await db.mystery_registry.find({"project_id": pid, **authority_query}).sort("updated_at", -1).to_list(length=6)
        approved_drafts = await db.chapter_drafts.find({
            "project_id": pid, "active": True, "status": "approved",
        }).sort("chapter_number", 1).to_list(length=200)
        distinctive_elements = [
            *[str(item.get("description") or item.get("name")) for item in characters if item.get("description") or item.get("name")],
            *[str(item) for item in (worlds.get("world_rules") or [])[:4]],
            *[str(item.get("question") or item.get("setup")) for item in mysteries if item.get("question") or item.get("setup")],
        ][:10]
        opening_checks: list[str] = []
        answer = ""
        if approved_drafts:
            opening = approved_drafts[0]
            opening_text = str(opening.get("generated_text") or opening.get("content") or opening.get("prose") or opening.get("text") or "")
            opening_words = opening_text.split()
            if len(opening_words) >= 350:
                opening_checks.append("Chapter 1 sustains a full scene rather than only summarising the premise")
            if re.search(r"[?!]|\b(?:but|until|suddenly|refused|discovered|threat|danger|wanted|must)\b", " ".join(opening_words[:140]).lower()):
                opening_checks.append("the opening contains a detectable disruption, question, desire, or pressure")
            if re.search(r"[?!]|\b(?:but|however|until|then|realized|decided|discovered|promised|refused|arrived)\b", " ".join(opening_words[-140:]).lower()):
                opening_checks.append("the ending leaves a detectable turn or forward pressure")
            if opening_checks and focus == "opening" and not selected:
                answer = "I checked the current approved prose and shared story analysis. " + "; ".join(opening_checks) + ". No active Chapter 1 hook or ending warning was found. This is a structural signal, not a claim of professional literary quality."
            elif opening_checks and focus == "distinctiveness" and not selected:
                answer = "I did not find an active repetition or genericness warning. The current story's distinctiveness is coming from its confirmed elements and concrete choices, including: " + "; ".join(distinctive_elements[:4]) + ". The shared analysis also checked the approved opening for structural pressure."
        if selected:
            lead = "; ".join(str(item.get("explanation") or "") for item in selected[:3])
            answer = f"I checked the current story evidence for {focus}. {lead}"
        elif focus == "distinctiveness" and not answer:
            answer = "I did not find an active repetition or genericness warning. The most distinctive material currently visible in the story is grounded in the confirmed story records below. This is a project-level signal, not a claim about every novel ever written."
        elif not answer:
            answer = f"I did not find a current {focus} warning in the shared story analysis. That is a useful signal, not a guarantee; the evidence below shows what was checked."
        return {
            "focus": focus,
            "answer": answer,
            "findings": selected,
            "distinctive_elements": [item for item in distinctive_elements if item],
            "health_before": critique.get("story_health_before"),
            "health_after": critique.get("story_health_after"),
            "source": "Narrative Critique and Narrative Analysis",
        }

    @staticmethod
    def _write_parameters(query: str) -> Dict[str, Any]:
        """Turn natural word-range language into the existing Discovery contract."""
        text = " ".join((query or "").split())
        text = text.replace("–", "-").replace("—", "-")
        numbers = lambda value: int(str(value).replace(",", ""))
        chapter_match = re.search(r"\bchapter\s+(\d+)\b", text, flags=re.IGNORECASE)
        chapter_number = int(chapter_match.group(1)) if chapter_match else None
        minimum, target, maximum = 1000, 1400, 2200
        range_match = re.search(
            r"(?:between\s+)?([\d,]+)\s*(?:-|–|—|to)\s*([\d,]+)\s+words?",
            text,
            flags=re.IGNORECASE,
        )
        around_match = re.search(r"(?:around|about|roughly)\s+([\d,]+)\s+words?", text, flags=re.IGNORECASE)
        minimum_match = re.search(r"(?:at least|minimum(?: of)?)\s+([\d,]+)\s+words?", text, flags=re.IGNORECASE)
        if range_match:
            minimum = numbers(range_match.group(1))
            maximum = numbers(range_match.group(2))
            target = round((minimum + maximum) / 2)
        elif around_match:
            target = numbers(around_match.group(1))
            minimum = max(1000, round(target * 0.8))
            maximum = round(target * 1.2)
        elif minimum_match:
            minimum = numbers(minimum_match.group(1))
            target = round(minimum * 1.15)
            maximum = round(minimum * 1.35)
        return {
            "chapter_number": chapter_number,
            "instruction": text,
            "minimum": minimum,
            "target": target,
            "maximum": max(maximum, target),
        }

    async def _job(self, db, project_id: str, request: StoryStudioRequest, intent: StoryStudioIntent) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        request_id = str(request.request_id or uuid4())
        if request_id:
            existing = await db.story_studio_jobs.find_one({"project_id": pid, "request_id": request_id})
            if existing:
                return existing
        job_id = str(uuid4())
        doc = {
            "project_id": pid,
            "job_id": job_id,
            "request_id": request_id,
            "query": request.query,
            "intent": intent.intent.value,
            "mutation_class": intent.mutation_class.value,
            "model_preference": request.model_preference,
            "model_scope": request.model_scope,
            "status": "running",
            "events": [{"stage": "understand", "status": "running", "summary": "NovelForge is understanding your request.", "created_at": datetime.utcnow()}],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        try:
            await db.story_studio_jobs.insert_one(doc)
        except DuplicateKeyError:
            existing = await db.story_studio_jobs.find_one({"project_id": pid, "request_id": request_id})
            if existing:
                return existing
            raise
        await emit_project_event(db, project_id, "story_studio_job_started", payload={"job_id": job_id, "intent": intent.intent.value})
        return doc

    @staticmethod
    def _development_is_targeted(query: str) -> bool:
        text = " ".join((query or "").lower().split())
        targeted_terms = (
            "relationship", "relationships", "character", "characters", "world",
            "magic", "mystery", "mysteries", "timeline", "arc", "chapter", "chapters",
            "plot thread", "plot threads", "setting",
        )
        return any(term in text for term in targeted_terms) and not any(
            phrase in text for phrase in ("develop the story", "develop my story", "continue developing", "develop this story")
        )

    async def _start_development(self, db, project_id: str, job: Dict[str, Any], query: str) -> Dict[str, Any]:
        launched = await development_state_service.start_story_studio_development(
            db,
            project_id,
            instruction=query,
            story_studio_job_id=str(job["job_id"]),
            targeted=self._development_is_targeted(query),
        )
        development = {
            "status": "running",
            "run_id": launched["run_id"],
            "cycle_id": launched["cycle_id"],
            "cycle_number": launched["cycle_number"],
            "targeted": launched["targeted"],
            "summary": launched["message"],
            "confirmed_planning_used": True,
        }
        result = {
            "understood": query,
            "intent": StoryStudioIntent(
                intent=StoryIntent.DEVELOP,
                mutation_class=MutationClass.PROPOSAL,
                confidence=0.94,
                requires_author_decision=False,
                explanation="The existing development workflow is expanding confirmed planning.",
            ).model_dump(),
            "answer": launched["message"],
            "mutation_applied": False,
            "author_decision_required": False,
            "navigation_actions": [{"target": "project-activity", "section": "project-activity", "label": "Follow story development"}],
            "evidence": {"source": "existing story-development workflow", "authority_changed": False, "confirmed_planning_used": True},
            "development": development,
            "job_id": job["job_id"],
            "request_id": job.get("request_id"),
            "mutation_class": MutationClass.PROPOSAL.value,
        }
        now = datetime.utcnow()
        await db.story_studio_jobs.update_one(
            {"project_id": ObjectId(project_id), "job_id": job["job_id"]},
            {"$set": {"status": "running", "development_run_id": ObjectId(launched["run_id"]), "development_cycle_id": ObjectId(launched["cycle_id"]), "result": result, "updated_at": now}, "$push": {"events": {"stage": "development", "status": "running", "summary": "Story development is running from confirmed planning.", "created_at": now}}},
        )
        try:
            await memory_provider_service.capture(
                db,
                project_id,
                user_content=query,
                assistant_content=launched["message"],
                source_type="story_studio_development",
                source_id=str(job["job_id"]),
            )
        except Exception:
            pass
        return result

    async def _job_event(self, db, project_id: str, job_id: str, *, stage: str, status: str, summary: str, error: str | None = None) -> None:
        now = datetime.utcnow()
        update: Dict[str, Any] = {"updated_at": now}
        if status == "failed":
            update["status"] = "failed"
        elif status == "waiting":
            update["status"] = "waiting"
        elif status == "running":
            update["status"] = "running"
        if error:
            update["error"] = error
        await db.story_studio_jobs.update_one(
            {"project_id": ObjectId(project_id), "job_id": job_id},
            {"$set": update, "$push": {"events": {"stage": stage, "status": status, "summary": summary, "created_at": now}}},
        )

    async def recover_interrupted_jobs(self, db) -> int:
        """Mark in-process Story Studio work orphaned by an API restart honestly."""
        cursor = db.story_studio_jobs.find(
            {
                "status": {"$in": ["running", "queued"]},
                "development_run_id": {"$exists": False},
            }
        )
        recovered = 0
        async for job in cursor:
            result = dict(job.get("result") or {})
            result.setdefault("understood", job.get("query") or "Your Story Studio request")
            result.setdefault("answer", "This Story Studio task was interrupted by a restart. Your story data was not changed; retry it when ready.")
            result.setdefault("mutation_applied", False)
            result.setdefault("author_decision_required", False)
            result["error_state"] = "interrupted"
            now = datetime.utcnow()
            await db.story_studio_jobs.update_one(
                {"_id": job["_id"], "status": {"$in": ["running", "queued"]}},
                {
                    "$set": {"status": "interrupted", "result": result, "updated_at": now},
                    "$push": {
                        "events": {
                            "stage": "recovery",
                            "status": "interrupted",
                            "summary": "Story Studio work was interrupted by an application restart. Existing story data is safe.",
                            "created_at": now,
                        }
                    },
                },
            )
            recovered += 1
        return recovered

    async def request(self, db, project_id: str, request: StoryStudioRequest) -> Dict[str, Any]:
        reply_to_job_id = str((request.target or {}).get("reply_to_job_id") or "").strip() or None
        parent_job = None
        effective_query = request.query
        if reply_to_job_id:
            parent_job = await db.story_studio_jobs.find_one({"project_id": ObjectId(project_id), "job_id": reply_to_job_id})
            if parent_job and parent_job.get("status") == "waiting" and parent_job.get("clarification"):
                original_query = str(parent_job.get("query") or "").strip()
                effective_query = f"{original_query}\nAuthor clarification: {request.query.strip()}"
        intent = self.classify(effective_query, allow_mutations=request.allow_mutations or bool(parent_job))
        job = await self._job(db, project_id, request, intent)
        if job.get("status") == "completed" and job.get("result"):
            return job["result"]
        operation_id = str(job.get("request_id") or job["job_id"])
        planning_capture = await self._capture_planning(db, project_id, effective_query) if self._looks_like_planning(effective_query, intent) else None
        clarification = self._clarification_prompt(effective_query, intent) if not parent_job else None
        if clarification:
            await self._job_event(db, project_id, job["job_id"], stage="clarification", status="waiting", summary="NovelForge needs one creative choice before it can continue.")
            result = {
                "understood": request.query,
                "intent": StoryStudioIntent(intent=StoryIntent.AUTHOR_DECISION_REQUIRED, mutation_class=MutationClass.AMBIGUOUS, confidence=0.92, requires_author_decision=True, explanation="The request has more than one materially different creative meaning.").model_dump(),
            "answer": f"Nothing has been changed. {clarification}",
                "mutation_applied": False,
                "author_decision_required": True,
                "clarification": {"question": clarification, "original_query": request.query, "status": "waiting"},
                "navigation_actions": [],
                "evidence": {"source": "story_studio_router", "authority_changed": False},
                "job_id": job["job_id"],
                "request_id": operation_id,
            }
            now = datetime.utcnow()
            await db.story_studio_jobs.update_one({"project_id": ObjectId(project_id), "job_id": job["job_id"]}, {"$set": {"status": "waiting", "clarification": result["clarification"], "result": result, "updated_at": now}})
            return result
        if intent.intent == StoryIntent.AUTHOR_DECISION_REQUIRED:
            answer = "I understand this as a possible story change. Nothing has been changed. Would you like me to prepare a governed proposal for your review?"
            result = {
                "understood": request.query,
                "intent": intent.model_dump(),
                "answer": answer,
                "mutation_applied": False,
                "author_decision_required": True,
                "navigation_actions": [],
                "evidence": {"source": "story_studio_router", "authority_changed": False},
                "job_id": job["job_id"],
                "request_id": operation_id,
                "planning_capture": planning_capture,
            }
        elif intent.intent == StoryIntent.REVIEW and any(marker in effective_query.lower() for marker in ("generic", "repetitive", "repeating", "distinctive", "similar", "first chapter", "opening", "quality", "memorable")):
            review = await self._creative_review(db, project_id, effective_query)
            result = {
                "understood": request.query,
                "intent": intent.model_dump(),
                "answer": review["answer"],
                "mutation_applied": False,
                "author_decision_required": False,
                "navigation_actions": [{"target": "story-health", "section": "story-health", "label": "Open Story Health"}],
                "creative_review": review,
                "evidence": {
                    "source": review["source"],
                    "authority_changed": False,
                    "findings": review["findings"],
                    "distinctive_elements": review["distinctive_elements"],
                },
                "job_id": job["job_id"],
                "request_id": operation_id,
            }
        elif intent.intent == StoryIntent.MODIFY and intent.mutation_class == MutationClass.PROPOSAL:
            try:
                revision = await self._chapter_revision(db, project_id, effective_query, request.model_preference)
            except Exception as exc:
                await self._job_event(
                    db,
                    project_id,
                    job["job_id"],
                    stage="revision",
                    status="failed",
                    summary="The revision could not be prepared. The approved chapter remains safe and unchanged.",
                    error=str(exc),
                )
                result = {
                    "understood": request.query,
                    "intent": intent.model_dump(),
                    "answer": "I could not prepare that revision safely. The approved chapter is unchanged; you can retry from Story Studio or Editorial.",
                    "mutation_applied": False,
                    "author_decision_required": False,
                    "navigation_actions": [{"target": "editorial", "section": "editorial", "label": "Open Editorial"}],
                    "evidence": {"source": "existing Editorial revision workflow", "authority_changed": False, "failure_safe": True},
                    "job_id": job["job_id"],
                    "request_id": operation_id,
                    "error_state": "failed_safe",
                }
                return result
            if revision and revision.get("error"):
                answer = revision["error"]
                navigation_actions = []
                evidence = {"source": "existing chapter draft lineage", "authority_changed": False}
            else:
                answer = f"I prepared a protected revision proposal for Chapter {revision['chapter_number']}. The approved source is unchanged; review the alternative before deciding whether to use it."
                navigation_actions = [{"target": "editorial", "section": "editorial", "label": "Review suggested version"}]
                evidence = {"source": "existing Editorial revision workflow", "authority_changed": False, "chapter": revision["chapter_number"], "revision_branch_id": revision["branch"].get("branch_id"), "revision_id": revision["revision"].get("revision_id")}
            result = {
                "understood": request.query,
                "intent": intent.model_dump(),
                "answer": answer,
                "mutation_applied": False,
                "author_decision_required": False,
                "navigation_actions": navigation_actions,
                "evidence": evidence,
                "change_receipt": {"what_changed": "A reviewable revision proposal was created; source prose was preserved.", "what_was_preserved": "Approved chapter source, canon, decisions, chronology, and draft lineage.", "what_needs_review": "Compare the proposed version in Editorial before using it."},
                "job_id": job["job_id"],
                "request_id": operation_id,
            }
            if revision and not revision.get("error"):
                result["revision"] = revision
                result["generation_metadata"] = (
                    revision.get("generation_metadata")
                    or (revision.get("revision") or {}).get("generation_metadata")
                    or {}
                )
        elif intent.intent == StoryIntent.DEVELOP:
            return await self._start_development(db, project_id, job, effective_query)
        elif intent.intent in {StoryIntent.MODIFY, StoryIntent.RECONSIDER, StoryIntent.DEVELOP}:
            # Explicit conversational intent still creates only a governed
            # proposal. The existing Canon Proposal Queue / owning services
            # remain the only path that can change authority.
            assistant = await narrative_interaction_service.assistant(
                db, project_id, query=effective_query, mode=request.mode,
                active_surface=request.active_surface, intent=None,
                request_id=operation_id, allow_proposals=True,
                model_preference=request.model_preference, model_scope=request.model_scope,
            )
            proposal_count = len(assistant.get("canon_proposal_ids") or [])
            result = {
                "understood": request.query,
                "intent": intent.model_dump(),
                "answer": assistant.get("answer") or "I prepared this as a governed proposal for your review.",
                "mutation_applied": False,
                "author_decision_required": True,
                "navigation_actions": [{"target": "canon-queue", "label": "Canon Queue"}] if proposal_count else [],
                "evidence": assistant.get("evidence") or {"authority_changed": False},
                "change_receipt": {"what_changed": "No authoritative state", "proposals_created": proposal_count, "next_step": "Review the governed proposal before approval"},
                "job_id": job["job_id"],
                "request_id": operation_id,
                "planning_capture": planning_capture,
            }
        elif intent.intent == StoryIntent.WRITE:
            parameters = self._write_parameters(effective_query)
            await self._job_event(
                db, project_id, job["job_id"], stage="write", status="running",
                summary="NovelForge is writing a reviewable chapter draft from the current governed story context.",
            )
            try:
                writing = await discovery_writing_service.generate(
                    db,
                    project_id,
                    {
                        "workflow_mode": "discovery",
                        "instruction": parameters["instruction"],
                        "chapter_number": parameters["chapter_number"],
                        "target_word_min": parameters["minimum"],
                        "target_word_count": parameters["target"],
                        "target_word_max": parameters["maximum"],
                    },
                )
            except Exception as exc:
                await self._job_event(
                    db, project_id, job["job_id"], stage="write", status="failed",
                    summary="Chapter writing failed safely. Existing approved prose and story authority are unchanged.",
                    error=str(exc),
                )
                raise
            draft = writing.get("draft") or {}
            chapter_number = int(draft.get("chapter_number") or parameters["chapter_number"] or 0)
            word_count = int(draft.get("word_count") or 0)
            result = {
                "understood": request.query,
                "intent": intent.model_dump(),
                "answer": f"Chapter {chapter_number} is ready to review. It is a new draft, not approved story truth.",
                "mutation_applied": False,
                "author_decision_required": False,
                "navigation_actions": [
                    {"type": "navigate", "target": "writing", "section": "writing", "label": f"Open Chapter {chapter_number}"},
                    {"type": "navigate", "target": "editorial", "section": "editorial", "label": "Edit or revise"},
                ],
                "writing_actions": ["Open chapter", "Edit", "Revise", "Approve", "Continue"],
                "draft": {
                    "draft_id": draft.get("draft_id"),
                    "chapter_number": chapter_number,
                    "status": draft.get("status") or "draft",
                    "word_count": word_count,
                    "range_compliant": draft.get("range_compliant"),
                    "target_word_min": draft.get("target_word_min"),
                    "target_word_count": draft.get("target_word_count"),
                    "target_word_max": draft.get("target_word_max"),
                    "validation_result": draft.get("validation_result"),
                    "generated_text": str(draft.get("generated_text") or ""),
                },
                "change_receipt": {
                    "what_changed": f"Created a reviewable Chapter {chapter_number} draft ({word_count:,} words).",
                    "what_was_preserved": "Approved prose, canon, decisions, and structured story authority.",
                    "what_needs_review": "Read the draft and approve it only when it represents your novel.",
                    "next_step": f"Review Chapter {chapter_number} in Writing or Editorial.",
                },
                "evidence": {
                    "source": "existing Discovery Writing pipeline",
                    "authority_changed": False,
                    "chapter": chapter_number,
                    "word_range": {"minimum": parameters["minimum"], "target": parameters["target"], "maximum": parameters["maximum"]},
                    "continuity_result": draft.get("validation_result"),
                },
                "job_id": job["job_id"],
                "request_id": operation_id,
                "generation_metadata": draft.get("generation_metadata") or {},
                "planning_capture": planning_capture,
            }
        else:
            narrative_intent = "narrative_creation" if intent.intent == StoryIntent.BRAINSTORM else None
            assistant = await narrative_interaction_service.assistant(
                db,
                project_id,
                query=effective_query,
                mode=request.mode,
                active_surface=request.active_surface,
                intent=narrative_intent,
                request_id=operation_id,
                allow_proposals=False,
                model_preference=request.model_preference,
                model_scope=request.model_scope,
            )
            result = {
                "understood": request.query,
                "intent": intent.model_dump(),
                "mutation_class": intent.mutation_class.value,
                "answer": assistant.get("answer") or "NovelForge completed the request.",
                "mutation_applied": False,
                "author_decision_required": False,
                "navigation_actions": assistant.get("navigation_actions") or [],
                "evidence": assistant.get("evidence") or {},
                "job_id": job["job_id"],
                "request_id": operation_id,
                "assistant_message_id": assistant.get("message_id"),
                "generation_metadata": assistant.get("generation_metadata") or {},
                "planning_capture": planning_capture,
            }
        result.setdefault("mutation_class", intent.mutation_class.value)
        if reply_to_job_id:
            result["continued_from_job_id"] = reply_to_job_id
        now = datetime.utcnow()
        final_summary = (
            "NovelForge finished a reviewable chapter draft; approved story authority was unchanged."
            if intent.intent == StoryIntent.WRITE
            else "NovelForge finished without changing authoritative story state."
        )
        await db.story_studio_jobs.update_one(
            {"project_id": ObjectId(project_id), "job_id": job["job_id"]},
            {"$set": {"status": "completed", "result": result, "updated_at": now}, "$push": {"events": {"stage": "result", "status": "completed", "summary": final_summary, "created_at": now}}},
        )
        await emit_project_event(db, project_id, "story_studio_job_completed", payload={"job_id": job["job_id"], "intent": intent.intent.value})
        try:
            await memory_provider_service.capture(
                db,
                project_id,
                user_content=effective_query,
                assistant_content=str(result.get("answer") or ""),
                source_type="story_studio_job",
                source_id=str(job["job_id"]),
            )
        except Exception:
            pass
        return result

    async def jobs(self, db, project_id: str, limit: int = 50) -> list[Dict[str, Any]]:
        rows = await db.story_studio_jobs.find({"project_id": ObjectId(project_id)}).sort("created_at", -1).to_list(length=min(max(limit, 1), 200))
        for row in rows:
            run = None
            development_run_id = row.get("development_run_id")
            if development_run_id and ObjectId.is_valid(str(development_run_id)):
                run = await db.runs.find_one({"_id": ObjectId(str(development_run_id)), "project_id": ObjectId(project_id)})
            if run:
                metadata = run.get("metadata") or {}
                run_status = str(run.get("status") or "running")
                result = dict(row.get("result") or {})
                development = dict(result.get("development") or {})
                development.update({
                    "run_id": str(run.get("_id")),
                    "cycle_id": str(metadata.get("cycle_id") or row.get("development_cycle_id") or ""),
                    "status": "waiting" if run_status in {"waiting", "waiting_for_user"} else ("failed" if run_status in {"failed", "interrupted"} else ("completed" if run_status == "completed" else "running")),
                    "author_phase": metadata.get("author_phase") or "Story development is running",
                    "planned_agents": metadata.get("planned_agents") or [],
                    "completed_agents": metadata.get("completed_agents") or [],
                    "run_status": run_status,
                })
                if development["status"] == "waiting":
                    question_query = {"project_id": ObjectId(project_id), "answered": False}
                    if run.get("started_at"):
                        question_query["created_at"] = {"$gte": run["started_at"]}
                    question = await db.questions.find_one(
                        question_query,
                        sort=[("created_at", -1)],
                    )
                    if question:
                        development["question"] = str(question.get("text") or "NovelForge needs one story decision before continuing.")
                        development["question_id"] = str(question.get("_id"))
                    result["answer"] = "Story development is waiting for an important author decision. Nothing was silently promoted to canon."
                    result["author_decision_required"] = True
                elif development["status"] == "completed":
                    result["answer"] = "Story development finished using your confirmed planning. Review the updated story workspaces when you are ready."
                elif development["status"] == "failed":
                    result["answer"] = "Story development stopped safely. Your existing story state and approved prose remain unchanged; retry from Project Activity when ready."
                    result["error"] = run.get("error") or "The development pass needs attention."
                development["confirmed_planning_used"] = True
                result["development"] = development
                row["result"] = result
                row["status"] = development["status"]
                row["progress"] = {
                    "completed": int(metadata.get("progress_completed") or len(metadata.get("completed_agents") or [])),
                    "total": int(metadata.get("progress_total") or len(metadata.get("planned_agents") or [])),
                    "message": development.get("author_phase") or "Story development is running",
                }
                await db.story_studio_jobs.update_one(
                    {"_id": row["_id"]},
                    {"$set": {"status": row["status"], "result": result, "progress": row["progress"], "updated_at": datetime.utcnow()}},
                )
            row["job_id"] = str(row.get("job_id"))
            if row.get("development_run_id"):
                row["development_run_id"] = str(row["development_run_id"])
            if row.get("development_cycle_id"):
                row["development_cycle_id"] = str(row["development_cycle_id"])
            row.pop("_id", None)
            row["project_id"] = str(row.get("project_id"))
        return list(reversed(rows))


story_studio_service = StoryStudioService()
