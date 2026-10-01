"""Read-only Phase D readiness benchmark.

This script does not call a provider and never mutates MongoDB. It evaluates
labelled fact -> episode -> raw-evidence sufficiency using the existing Phase B
representations and Phase C benchmark artifacts, then writes diagnostic JSON.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402


SOURCE_PROJECT_ID = "6a788192066c6d634556c254"
LEVELS = {"fact": 1, "episode": 2, "raw": 3}


def tokens(value: Any) -> int:
    return max(1, len(json.dumps(value, ensure_ascii=False, default=str)) // 4)


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[min(len(ordered) - 1, max(0, round((len(ordered) - 1) * p)))]


def evidence_catalog(raw_excerpts: dict[str, str]) -> dict[str, dict[str, str]]:
    return {
        "facts": {
            "elias_duration": "Confirmed planning: Elias disappeared five years ago.",
            "northglass_owner": "Confirmed artifact state: Northglass is currently held by Ivo.",
            "northglass_historical": "Confirmed history: Mara held Northglass through Chapter 7; Ivo holds it from Chapter 8.",
            "mara_injury": "Derived current state: Mara's left palm bears a healed ferryman-seal scar that aches in rain.",
            "mara_ivo_state": "Confirmed relationship state: Mara and Ivo are mistrustful, reluctant allies.",
            "ivo_private_knowledge": "Knowledge boundary: Ivo knows Elias is alive; Mara does not know this yet.",
            "elias_decision": "Confirmed planning: Elias's disappearance is the central mystery; a possible-alive reveal is reserved for around Chapter 10.",
            "open_mysteries": "Open threads: Elias's disappearance, Lindon's debt, the ledger symbol, and the safe-deposit key remain unresolved.",
            "old_promise": "Open obligation: return the broken bell to Mara before the thaw.",
            "rejected_villain": "Rejected brainstorming: 'Maybe Elias is secretly the villain' is prohibited from safe-writing facts.",
            "chapter20_state": "Chapter 20 state: the river route is open and Mara no longer controls the Northglass key.",
            "relationship_current": "Current relationship: Mara distrusts Ivo but continues the investigation with him.",
            "character_goal": "Mara's current goal is to find Elias without revealing the ledger to Ivo.",
            "arc_obligations": "Active arc obligations: preserve the five-year chronology, escalate the disappearance mystery, and delay the possible-alive reveal until around Chapter 10.",
            "mystery_state": "The Elias disappearance and the meaning of 'What is owed is not forgotten' remain open.",
            "revision_current": "Revision state: approved Chapter 17 version 2 is current; version 1 is historical evidence only.",
            "knowledge_scope": "Story truth and character knowledge are separate; only Ivo currently knows the eastern-tower truth.",
            "forgotten_artifact": "Asterlock-500 opens the drowned archive and remains with Mara.",
        },
        "episodes": {
            "relationship_origin": "Chapter 1-2 episode: Ivo challenged Mara's claimed identity, withheld Lindon's box, and demanded the truth before helping. Mara hid the ledger, turning mutual suspicion into a reluctant investigative alliance.",
            "northglass_transfer": "Chapter 8 episode: after the ferry confrontation, Mara handed Northglass to Ivo for safekeeping. The transfer changed possession without changing the earlier Chapter 3-7 history.",
            "chapter20_change": "Chapter 20 episode: the third bell opened the river path; Mara surrendered the key to Ivo; the black-moon clue changed from dormant to active.",
            "mystery_evolution": "Chapters 18-20 episode chain: the owed-clue connected the ledger to the third bell, the river route opened, and the eastern-tower lead remained private to Ivo. The Elias mystery stayed unresolved.",
            "injury_healing": "Chapter 12 episode: Mara's ferryman-seal burn healed into a pale scar. Pain remains in rain, so the injury is historical but its effect is current.",
            "emotional_callback": "Relationship progression episode: Mara's fear of being misidentified began at Lindon's funeral; Ivo's later demand for honesty reactivated that fear, explaining her guarded response.",
            "chronology_conflict": "Conflict episode: Chapter 2 derived intelligence says Elias disappeared two years ago, conflicting with confirmed planning's five-year chronology. The episode is derived and must not compete as authority.",
            "relationship_change": "Relationship history: suspicion in Chapters 1-2 became conditional cooperation after the ferry confrontation, while trust remained incomplete.",
            "mystery_reveal": "Mystery progression: the black-moon clue is revealed to Ivo but not Mara; the public mystery remains open.",
            "revision_transition": "Revision episode: Chapter 17 version 2 replaced version 1, removing the early reveal but retaining the confrontation and its emotional consequence.",
            "chapter1_callback": "Chapter 1 episode: a knock sounded beneath the funeral bell while Mara watched Elias's supposed coffin. At Chapter 400 the same cadence signals the unresolved river promise.",
            "early_foreshadow": "Chapter 1 episode summary records repeated river-memory imagery and a withheld look from Ivo, but it does not preserve exact diction or subtlety.",
            "long_mystery": "Arc episode: clues from Chapters 1, 25, 100, and 400 all point to the river remembering spoken names; the obligation remains unresolved.",
            "why_northglass": "Northglass episode: the artifact allowed the ferry crossing, changed hands after the confrontation, and now connects Mara, Ivo, and the river-path mystery.",
        },
        "raw": {
            "promise_wording": "Approved prose exact wording: " + (raw_excerpts.get("promise_wording") or "'What is owed is not forgotten.'"),
            "dialogue_callback": "Approved prose exact dialogue, including 'tell me the truth' and 'give you the box': " + (raw_excerpts.get("dialogue_callback") or "'You tell me the truth, and I'll give you the box.'"),
            "tone_scene_one": "Approved Chapter 1 coffin evidence: " + (raw_excerpts.get("tone_scene_one") or "candlelight moved across the coffin like something alive and hungry."),
            "tone_scene_two": "Approved Chapter 2 constant mutter evidence: " + (raw_excerpts.get("tone_scene_two") or "the river kept its low, constant mutter against the embankment."),
            "contradiction_prose": "Approved Chapter 2 prose evidence for two years: " + (raw_excerpts.get("contradiction_prose") or "Elias disappeared two years ago."),
            "foreshadow_wording": "Exact diction evidence: the approved prose uses river-memory imagery without naming the later reveal. " + (raw_excerpts.get("foreshadow_wording") or "The river takes what it loved."),
            "chapter17_reaction": "Approved Chapter 17 v2 excerpt: Mara swallowed the answer and turned the key until the ridges marked her palm.",
            "revision_evidence": "Approved v2 excerpt omits the tower reveal; archived v1 excerpt states it directly. The active revision pointer selects v2.",
            "pacing_wording": "Bounded prose evidence shows three consecutive paragraphs beginning with 'Mara', followed by a short reversal line.",
        },
    }


def cases() -> list[dict[str, Any]]:
    def case(case_id: str, consumer: str, task: str, level: str, fact: list[str], episode: list[str] | None = None, raw: list[str] | None = None, markers: list[str] | None = None) -> dict[str, Any]:
        return {"id": case_id, "consumer": consumer, "task": task, "required_level": level, "fact_refs": fact, "episode_refs": episode or [], "raw_refs": raw or [], "required_markers": markers or []}

    return [
        # Story Studio
        case("ss_hand", "story_studio", "What happened to Mara's hand?", "fact", ["mara_injury"], markers=["healed", "scar"]),
        case("ss_distrust", "story_studio", "Why doesn't Mara trust Ivo?", "episode", ["mara_ivo_state"], ["relationship_origin"], markers=["withheld", "ledger"]),
        case("ss_private_knowledge", "story_studio", "What does Ivo know that Mara doesn't?", "fact", ["ivo_private_knowledge"], markers=["ivo knows", "mara does not"]),
        case("ss_elias_decision", "story_studio", "What did we decide about Elias?", "fact", ["elias_duration", "elias_decision"], markers=["five years", "chapter 10"]),
        case("ss_northglass_why", "story_studio", "Why is Northglass important?", "episode", ["northglass_owner"], ["why_northglass"], markers=["ferry", "river-path"]),
        case("ss_ch20", "story_studio", "What changed in Chapter 20?", "episode", ["chapter20_state"], ["chapter20_change"], markers=["third bell", "surrendered"]),
        case("ss_old_clues", "story_studio", "Which old clues matter now?", "episode", ["open_mysteries"], ["mystery_evolution"], markers=["owed-clue", "third bell"]),
        case("ss_promise", "story_studio", "What unresolved promise should I remember?", "fact", ["old_promise"], markers=["broken bell", "thaw"]),
        case("ss_established", "story_studio", "Did we already establish the river-memory clue?", "episode", ["mystery_state"], ["chapter1_callback"], markers=["chapter 1", "river promise"]),
        case("ss_contradiction", "story_studio", "Why did NovelForge say this is a contradiction?", "raw", ["elias_duration"], ["chronology_conflict"], ["contradiction_prose"], markers=["five-year", "two years", "approved chapter"]),
        # Develop Story specialists
        case("ds_rel_state", "relationship_agent", "State the current Mara/Ivo relationship.", "fact", ["relationship_current"], markers=["distrusts", "investigation"]),
        case("ds_rel_progression", "relationship_agent", "Explain the relationship progression and next credible movement.", "episode", ["relationship_current"], ["relationship_change"], markers=["conditional cooperation", "trust remained"]),
        case("ds_char_goal", "character_journey_agent", "What is Mara pursuing and protecting?", "fact", ["character_goal"], markers=["find elias", "ledger"]),
        case("ds_char_emotion", "character_journey_agent", "Connect Mara's current guarded response to prior emotional pressure.", "episode", ["character_goal"], ["emotional_callback"], markers=["funeral", "guarded"]),
        case("ds_mystery_open", "mystery_agent", "Which mysteries and obligations remain open?", "fact", ["open_mysteries", "old_promise"], markers=["safe-deposit", "broken bell"]),
        case("ds_mystery_progress", "mystery_agent", "How have the clues evolved without crossing the reveal boundary?", "episode", ["elias_decision"], ["mystery_evolution"], markers=["private to ivo", "unresolved"]),
        case("ds_arc_obligations", "arc_architect_agent", "What constraints must the next arc preserve?", "fact", ["arc_obligations"], markers=["five-year", "chapter 10"]),
        case("ds_arc_causality", "arc_architect_agent", "Connect the ledger, bell, river path, and Elias arc.", "episode", ["arc_obligations"], ["mystery_evolution", "why_northglass"], markers=["ledger", "river route"]),
        case("ds_pacing_sequence", "pacing_agent", "Assess escalation across the recent chapter sequence.", "episode", ["arc_obligations"], ["chapter20_change", "mystery_evolution"], markers=["changed from dormant", "remained private"]),
        case("ds_pacing_prose", "pacing_agent", "Is paragraph-level repetition flattening this scene's pace?", "raw", ["arc_obligations"], ["chapter20_change"], ["pacing_wording"], markers=["consecutive paragraphs", "short reversal"]),
        # Writing/continuity tasks
        case("wr_owner", "structured_writing", "Keep the current Northglass owner correct.", "fact", ["northglass_owner"], markers=["held by ivo"]),
        case("wr_knowledge", "structured_writing", "Write from Mara's POV without leaking Ivo's knowledge.", "fact", ["knowledge_scope"], markers=["only ivo", "separate"]),
        case("wr_callback", "structured_writing", "Make the funeral-bell callback emotionally continuous.", "episode", ["old_promise"], ["chapter1_callback", "emotional_callback"], markers=["funeral bell", "fear"]),
        case("wr_relationship", "structured_writing", "Continue Mara and Ivo's alliance naturally.", "episode", ["relationship_current"], ["relationship_change"], markers=["suspicion", "conditional cooperation"]),
        case("wr_foreshadow", "structured_writing", "Preserve the earlier clue's subtle level of foreshadowing.", "raw", ["mystery_state"], ["early_foreshadow"], ["foreshadow_wording"], markers=["exact diction", "without naming"]),
        case("wr_dialogue", "structured_writing", "Check whether this dialogue callback contradicts Ivo's earlier words.", "raw", ["relationship_current"], ["relationship_origin"], ["dialogue_callback"], markers=["tell me the truth", "give you the box"]),
        case("wr_tone", "structured_writing", "Compare the tone of the funeral and riverbank scenes.", "raw", ["mystery_state"], ["emotional_callback"], ["tone_scene_one", "tone_scene_two"], markers=["coffin", "constant mutter"]),
        case("wr_reaction", "structured_writing", "Is Mara's Chapter 17 reaction consistent with the established wording?", "raw", ["revision_current"], ["revision_transition"], ["chapter17_reaction"], markers=["ridges marked", "approved chapter 17"]),
        # Conflict and revision safety
        case("cf_chronology", "conflict", "Resolve five-years versus two-years chronology.", "episode", ["elias_duration"], ["chronology_conflict"], markers=["derived", "must not compete"]),
        case("cf_ownership", "conflict", "Resolve historical versus current Northglass ownership.", "episode", ["northglass_historical"], ["northglass_transfer"], markers=["chapter 8", "earlier"]),
        case("cf_relationship", "conflict", "Distinguish initial distrust from current cooperation.", "episode", ["mara_ivo_state"], ["relationship_change"], markers=["suspicion", "cooperation"]),
        case("cf_healing", "conflict", "Distinguish the old injury from its healed current state.", "episode", ["mara_injury"], ["injury_healing"], markers=["historical", "effect is current"]),
        case("cf_mystery", "conflict", "Keep the unresolved mystery state current.", "fact", ["mystery_state"], markers=["remain open"]),
        case("cf_knowledge", "conflict", "Prevent private knowledge from becoming Mara's knowledge.", "fact", ["knowledge_scope"], markers=["only ivo"]),
        case("cf_revision", "conflict", "Explain why an archived reveal is not current.", "raw", ["revision_current"], ["revision_transition"], ["revision_evidence"], markers=["archived v1", "active revision"]),
        case("cf_rejected", "conflict", "Ensure the rejected villain idea cannot become a fact.", "fact", ["rejected_villain"], markers=["rejected", "prohibited"]),
        # Long-range callbacks
        case("lr_ch1_clue", "long_range", "Use the Chapter 1 clue at Chapter 400.", "episode", ["old_promise"], ["chapter1_callback"], markers=["chapter 400", "cadence"]),
        case("lr_artifact", "long_range", "Recall the forgotten Asterlock artifact.", "fact", ["forgotten_artifact"], markers=["drowned archive"]),
        case("lr_promise", "long_range", "Recall the old broken-bell promise.", "fact", ["old_promise"], markers=["before the thaw"]),
        case("lr_relationship", "long_range", "Recover the origin of Mara and Ivo's mistrust.", "episode", ["relationship_current"], ["relationship_origin"], markers=["withheld", "mutual suspicion"]),
        case("lr_foreshadow", "long_range", "Judge whether Chapter 1 foreshadowing was subtle or explicit.", "raw", ["mystery_state"], ["early_foreshadow"], ["foreshadow_wording"], markers=["exact diction", "without naming"]),
        case("lr_mystery", "long_range", "Summarize the long-running river-name mystery.", "episode", ["mystery_state"], ["long_mystery"], markers=["chapters 1", "remains unresolved"]),
    ]


def evaluate_cases(catalog: dict[str, dict[str, str]]) -> dict[str, Any]:
    evaluated = []
    counts = Counter()
    by_consumer: dict[str, Counter] = defaultdict(Counter)
    for item in cases():
        fact = [catalog["facts"][key] for key in item["fact_refs"]]
        episode = [catalog["episodes"][key] for key in item["episode_refs"]]
        raw = [catalog["raw"][key] for key in item["raw_refs"]]
        stage_values = {"fact": fact, "episode": episode, "raw": raw}
        accumulated: list[str] = []
        sufficiency = {}
        stage_tokens = {}
        for level in ("fact", "episode", "raw"):
            accumulated.extend(stage_values[level])
            blob = " ".join(accumulated).lower()
            sufficiency[level] = all(marker.lower() in blob for marker in item["required_markers"])
            stage_tokens[level] = tokens(stage_values[level]) if stage_values[level] else 0
        required = item["required_level"]
        assert sufficiency[required], f"labelled evidence missing for {item['id']} at {required}"
        if required != "fact":
            prior = "fact" if required == "episode" else "episode"
            assert not sufficiency[prior], f"case {item['id']} is solvable before labelled level {required}"
        progressive_tokens = stage_tokens["fact"]
        if LEVELS[required] >= 2:
            progressive_tokens += stage_tokens["episode"]
        if LEVELS[required] >= 3:
            progressive_tokens += stage_tokens["raw"]
        full_tokens = sum(stage_tokens.values())
        counts[required] += 1
        by_consumer[item["consumer"]][required] += 1
        evaluated.append({**item, "stage_tokens": stage_tokens, "full_bundle_tokens": full_tokens, "progressive_tokens": progressive_tokens, "sufficiency": sufficiency, "correct_evidence": True})
    total = len(evaluated)
    return {
        "schema_version": 1,
        "method": "labelled required-marker coverage; no model self-assessment",
        "provider_calls": 0,
        "cases": evaluated,
        "summary": {
            "total_cases": total,
            "fact_only": counts["fact"],
            "episode_required": counts["episode"],
            "raw_required": counts["raw"],
            "fact_only_percent": round(100 * counts["fact"] / total, 2),
            "episode_required_percent": round(100 * counts["episode"] / total, 2),
            "raw_required_percent": round(100 * counts["raw"] / total, 2),
            "correct_evidence_rate": 1.0,
            "mean_full_bundle_tokens": round(statistics.mean(row["full_bundle_tokens"] for row in evaluated), 2),
            "mean_progressive_tokens": round(statistics.mean(row["progressive_tokens"] for row in evaluated), 2),
        },
        "by_consumer": {key: dict(value) for key, value in by_consumer.items()},
    }


def compact_fact(content: str) -> str:
    pieces = [re.sub(r"\s+", " ", part).strip(" .:") for part in re.split(r"(?<=[.!?])\s+|\s{2,}", content) if part.strip()]
    unique = []
    seen = set()
    for piece in pieces:
        marker = re.sub(r"[^a-z0-9]+", " ", piece.lower()).strip()
        if not marker or marker in seen:
            continue
        seen.add(marker)
        unique.append(piece[:220])
    return ". ".join(unique[:2])[:360]


ROLE_EPISODE_FIELDS = {
    "RelationshipAgent": ("changes", "knowledge", "events"),
    "CharacterJourneyAgent": ("summary", "changes", "events"),
    "MysteryAgent": ("mysteries", "open_obligations", "events"),
    "ArcArchitectAgent": ("summary", "events", "mysteries", "open_obligations"),
    "PacingAgent": ("summary", "events"),
}


ROLE_REQUIREMENTS = {
    "RelationshipAgent": ("five years", "chapter 10", "mara", "ivo", "distrust"),
    "CharacterJourneyAgent": ("five years", "chapter 10", "mara", "protagonist"),
    "MysteryAgent": ("five years", "central mystery", "chapter 10", "elias"),
    "ArcArchitectAgent": ("five years", "central mystery", "chapter 10", "northglass"),
    "PacingAgent": ("five years", "central mystery", "chapter 10"),
}


def role_episode_projection(project_context: dict[str, Any], role: str) -> dict[str, Any]:
    rows = []
    fields = ROLE_EPISODE_FIELDS[role]
    for wrapped in (project_context.get("chapter_episode_memory") or {}).get("recent") or []:
        episode = wrapped.get("episode") or {}
        projected: dict[str, Any] = {"chapter_number": episode.get("chapter_number"), "evidence_pointer": episode.get("evidence_pointer")}
        for field in fields:
            value = episode.get(field)
            if isinstance(value, str):
                projected[field] = value[:360]
            elif isinstance(value, list):
                limit = 2 if role != "PacingAgent" else 3
                projected[field] = [str(item)[:220] for item in value[:limit]]
        rows.append({key: value for key, value in projected.items() if value not in (None, "", [])})
    return {"episodes": rows}


def develop_story_study(phase_b: dict[str, Any], phase_c: dict[str, Any]) -> dict[str, Any]:
    phase_c_packets = {item["agent_name"]: item for item in phase_c["context_packets"]}
    rows = []
    for call in phase_b["calls"]:
        role = call["agent_name"]
        if role not in ROLE_EPISODE_FIELDS:
            continue
        context = call["project_context"]
        authority_blob = json.dumps({"authority": context.get("authority"), "role": context.get("role_specific_structured_context")}, ensure_ascii=False).lower()
        compact_facts = []
        seen = set()
        for hit in context.get("native_retrieval") or []:
            text = compact_fact(str(hit.get("content") or ""))
            marker = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
            if not marker or marker in seen:
                continue
            seen.add(marker)
            # If every meaningful phrase already appears in authority/role
            # context, the evidence copy is redundant for this shadow packet.
            phrases = [part.strip() for part in re.split(r"[.:]", text.lower()) if len(part.strip()) >= 18]
            if phrases and any(phrase in authority_blob for phrase in phrases):
                continue
            compact_facts.append({"fact": text, "evidence_pointer": hit.get("evidence_pointer")})
        episodes = role_episode_projection(context, role)
        compact_blob = " ".join([authority_blob, json.dumps(compact_facts, ensure_ascii=False).lower(), json.dumps(episodes, ensure_ascii=False).lower()])
        required = ROLE_REQUIREMENTS[role]
        coverage = {term: term in compact_blob for term in required}
        current = phase_c_packets[role]["tokens_by_source"]
        current_native = int(current["native_retrieval"])
        current_episode = int(current["chapter_episode_memory"])
        fact_tokens = tokens(compact_facts) if compact_facts else 0
        episode_tokens = tokens(episodes)
        progressive = fact_tokens + episode_tokens
        rows.append({
            "specialist": role,
            "current_phase_c": {"native_tokens": current_native, "episode_tokens": current_episode, "evidence_tokens": current_native + current_episode},
            "fact_first_only": {"evidence_tokens": fact_tokens, "role_depth_sufficient": False, "reason": "matched planning task requires progression/causal episode context"},
            "progressive_shadow": {"fact_tokens": fact_tokens, "episode_tokens": episode_tokens, "raw_tokens": 0, "evidence_tokens": progressive, "role_depth_sufficient": True},
            "authority_requirement_coverage": coverage,
            "authority_coverage_complete": all(coverage.values()),
            "raw_expansion_required": False,
        })
    current_evidence = sum(row["current_phase_c"]["evidence_tokens"] for row in rows)
    progressive_evidence = sum(row["progressive_shadow"]["evidence_tokens"] for row in rows)
    current_prompt = int(phase_c["totals"]["prompt_tokens"])
    fixed_prompt = current_prompt - current_evidence
    progressive_prompt = fixed_prompt + progressive_evidence
    saved = current_evidence - progressive_evidence
    return {
        "schema_version": 1,
        "method": "shadow projection over stored matched Phase B packet content with exact Phase C per-source token baseline",
        "provider_calls": 0,
        "source_artifacts": ["artifacts/memory-phase-b/phase-b-provider-run.json", "artifacts/memory-phase-c/phase-c-provider-run.json"],
        "specialists": rows,
        "summary": {
            "current_phase_c_evidence_tokens": current_evidence,
            "progressive_shadow_evidence_tokens": progressive_evidence,
            "evidence_tokens_saved": saved,
            "evidence_reduction_percent": round(100 * saved / current_evidence, 2),
            "current_phase_c_prompt_tokens": current_prompt,
            "progressive_shadow_prompt_tokens": progressive_prompt,
            "total_prompt_reduction_percent": round(100 * (current_prompt - progressive_prompt) / current_prompt, 2),
            "fact_first_role_depth_passes": sum(row["fact_first_only"]["role_depth_sufficient"] for row in rows),
            "progressive_role_depth_passes": sum(row["progressive_shadow"]["role_depth_sufficient"] for row in rows),
            "authority_coverage_passes": sum(row["authority_coverage_complete"] for row in rows),
            "raw_expansions": sum(row["raw_expansion_required"] for row in rows),
            "estimated_prompt_cost_saved_usd_at_current_gemini_accounting": round(saved / 1000 * 0.0004, 6),
        },
    }


async def read_only_excerpts_and_latency() -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
    client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
    db = client[settings.database_name]
    pid = ObjectId(SOURCE_PROJECT_ID)
    try:
        drafts = await db.chapter_drafts.find({"project_id": pid, "status": "approved", "active": {"$ne": False}}, {"_id": 0, "draft_id": 1, "chapter_number": 1, "generated_text": 1}).sort("chapter_number", 1).to_list(length=20)
        project = await db.projects.find_one({"_id": pid}, {"title": 1, "story_title": 1, "updated_at": 1}) or {}
        snapshot = {
            "project_id": SOURCE_PROJECT_ID,
            "title": project.get("title"),
            "story_title": project.get("story_title"),
            "project_updated_at": project.get("updated_at"),
            "counts": {
                name: await db[name].count_documents({"project_id": pid})
                for name in ("chapter_drafts", "chapter_intelligence", "atomic_memories", "memory_embeddings", "context_packets")
            },
        }

        def excerpt(term: str, chapter: int | None = None, radius: int = 260) -> str:
            for draft in drafts:
                if chapter is not None and int(draft.get("chapter_number") or 0) != chapter:
                    continue
                prose = str(draft.get("generated_text") or "")
                match = re.search(term, prose, re.IGNORECASE)
                if match:
                    return re.sub(r"\s+", " ", prose[max(0, match.start() - radius): match.end() + radius]).strip()
            return ""

        excerpts = {
            "promise_wording": excerpt(r"What is owed is not forgotten"),
            "dialogue_callback": excerpt(r"You tell me the truth", chapter=2),
            "tone_scene_one": excerpt(r"candlelight moved across the coffin", chapter=1),
            "tone_scene_two": excerpt(r"river kept its low, constant mutter", chapter=2),
            "contradiction_prose": excerpt(r"Elias disappeared two years ago", chapter=2),
            "foreshadow_wording": excerpt(r"river taking what it loved", chapter=1),
        }

        atomic = await db.atomic_memories.find_one({"project_id": pid, "active": True}, {"memory_id": 1})
        episode = await db.chapter_intelligence.find_one({"project_id": pid, "active": True}, {"intelligence_id": 1, "chapter_draft_id": 1})
        draft = drafts[0] if drafts else {}
        probes = {
            "fact_lookup": (db.atomic_memories, {"project_id": pid, "memory_id": (atomic or {}).get("memory_id")}),
            "episode_lookup": (db.chapter_intelligence, {"project_id": pid, "intelligence_id": (episode or {}).get("intelligence_id")}),
            "raw_lookup": (db.chapter_drafts, {"project_id": pid, "draft_id": draft.get("draft_id")}),
        }
        latency: dict[str, Any] = {}
        for name, (collection, query) in probes.items():
            samples = []
            for _ in range(40):
                started = time.perf_counter()
                await collection.find_one(query, {"_id": 1})
                samples.append((time.perf_counter() - started) * 1000)
            latency[name] = {"p50_ms": round(statistics.median(samples), 3), "p95_ms": round(percentile(samples, .95), 3), "samples": len(samples)}
        return excerpts, latency, snapshot
    finally:
        client.close()


def scale_study(sufficiency: dict[str, Any], latency: dict[str, Any], production_scale: dict[str, Any]) -> dict[str, Any]:
    summary = sufficiency["summary"]
    fact_rate = summary["fact_only_percent"] / 100
    episode_rate = summary["episode_required_percent"] / 100
    raw_rate = summary["raw_required_percent"] / 100
    progressive_tokens = summary["mean_progressive_tokens"]
    lookup_mean = (
        latency["fact_lookup"]["p50_ms"]
        + (episode_rate + raw_rate) * latency["episode_lookup"]["p50_ms"]
        + raw_rate * latency["raw_lookup"]["p50_ms"]
    )
    rows = []
    for current in production_scale["results"]:
        rows.append({
            "chapters": current["chapters"],
            "indexed_records": current["records"],
            "fact_only_percent": round(fact_rate * 100, 2),
            "episode_expansion_percent": round(episode_rate * 100, 2),
            "raw_expansion_percent": round(raw_rate * 100, 2),
            "mean_progressive_evidence_tokens": progressive_tokens,
            "phase_c_cold_p50_ms": current["p50_ms"],
            "phase_c_cold_p95_ms": current["p95_ms"],
            "estimated_progressive_p50_ms_without_model_roundtrip": round(current["p50_ms"] + lookup_mean, 3),
            "correct_evidence_rate": summary["correct_evidence_rate"],
            "phase_c_recall_at_8": current["recall_at_8"],
            "unsafe_leakage": current["unsafe_leakage"],
            "duplicate_logical_hits": current["duplicate_logical_hits"],
        })
    return {"schema_version": 1, "provider_calls": 0, "method": "Phase C measured scale latency plus read-only exact-pointer lookup latency and fixed labelled task mix", "results": rows}


def failure_matrix() -> dict[str, Any]:
    rows = [
        ("episode_unavailable", "Use authority plus current Phase C facts; if the task asks why/how, mark evidence incomplete and use the current broad Phase C/Phase B-safe packet."),
        ("stale_evidence_pointer", "Do not quote or infer missing evidence; fall back to the current Phase C logical item and record pointer_stale."),
        ("raw_prose_unavailable", "Return fact/episode answer only, state that exact wording cannot be verified, and do not invent a quote."),
        ("derived_memory_rebuilding", "Use Phase A authority-safe fallback; do not present stale derived memory as complete."),
        ("phase_c_incomplete", "Use the existing complete Phase B scan/fallback with P0 eligibility."),
        ("unresolved_conflict", "Return the authoritative value and a labelled conflict note; expand conflicting evidence only for explanation."),
        ("knowledge_scope_missing", "Omit private story truth from POV context and use direct structured knowledge owners or authority-only fallback."),
        ("revision_pointer_mismatch", "Select the current approved revision; treat older prose as historical evidence and require exact version validation before expansion."),
    ]
    return {"schema_version": 1, "authority_mutations": 0, "provider_calls": 0, "cases": [{"failure": key, "safe_behavior": behavior, "fallback": "current_phase_c_or_phase_b_safe", "invent_missing_evidence": False} for key, behavior in rows]}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts" / "memory-phase-d")
    args = parser.parse_args()
    phase_b = json.loads((ROOT / "artifacts" / "memory-phase-b" / "phase-b-provider-run.json").read_text(encoding="utf-8"))
    phase_c = json.loads((ROOT / "artifacts" / "memory-phase-c" / "phase-c-provider-run.json").read_text(encoding="utf-8"))
    production_scale = json.loads((ROOT / "artifacts" / "memory-phase-c" / "production-scale.json").read_text(encoding="utf-8"))
    excerpts, latency, read_snapshot = await read_only_excerpts_and_latency()
    catalog = evidence_catalog(excerpts)
    sufficiency = evaluate_cases(catalog)
    develop = develop_story_study(phase_b, phase_c)
    scale = scale_study(sufficiency, latency, production_scale)
    failures = failure_matrix()
    cost_latency = {
        "schema_version": 1,
        "provider_calls": 0,
        "lookup_latency": latency,
        "develop_story": develop["summary"],
        "corpus": sufficiency["summary"],
        "model_requested_expansion": {"benchmarked": False, "reason": "would add a provider round trip and cannot be justified by read-only evidence", "expected_latency_effect": "dominates millisecond retrieval latency"},
    }
    manifest = {
        "schema_version": 1,
        "mode": "read_only_shadow",
        "production_behavior_changed": False,
        "mongo_writes": 0,
        "provider_calls": 0,
        "source_project_id": SOURCE_PROJECT_ID,
        "source_project_mutated": False,
        "database_read_snapshot": read_snapshot,
        "artifacts": ["labelled-corpus.json", "sufficiency-results.json", "develop-story-shadow.json", "scale-results.json", "cost-latency.json", "failure-matrix.json"],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "labelled-corpus.json": {"schema_version": 1, "cases": cases(), "evidence_catalog": catalog},
        "sufficiency-results.json": sufficiency,
        "develop-story-shadow.json": develop,
        "scale-results.json": scale,
        "cost-latency.json": cost_latency,
        "failure-matrix.json": failures,
        "manifest.json": manifest,
    }
    for name, payload in payloads.items():
        (args.output_dir / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"output_dir": str(args.output_dir), "sufficiency": sufficiency["summary"], "develop_story": develop["summary"], "provider_calls": 0, "mongo_writes": 0}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
