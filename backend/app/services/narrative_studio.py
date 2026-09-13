"""Provider-backed Narrative Studio agents and structured artifact processing."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Tuple
from uuid import uuid4

from bson import ObjectId

from app.services.canon_validation_service import validate_against_canon
from app.services.observability_service import estimate_cost
from app.services.orchestration_engine import AgentModelAssignment, orchestration_engine
from app.services.project_event_service import emit_project_event
from app.services.provider_gateway import ProviderError, provider_gateway
from app.services.model_registry_service import model_registry_service, normalize_provider
from app.services.memory_provider import memory_provider_service
from app.services.agent_memory_service import agent_memory_service
from app.services.workflow_persistence import save_questions
from app.services.chapter_intelligence_service import chapter_intelligence_service
from app.services.draft_validation_service import draft_validation_service
from app.services.execution_trace_service import execution_trace_service
from app.services.canon_service import get_canon_context
from app.services.development_state_service import development_state_service
from app.services.develop_story_context_service import develop_story_context_service


def agent_spec_label(agent_name: str) -> str:
    labels = {
        "NarrativeDirectorAgent": "the overall story direction",
        "StoryArchitectAgent": "the story structure",
        "CharacterJourneyAgent": "the characters",
        "WorldAgent": "the world",
        "PowerSystemAgent": "the story rules and powers",
        "FactionAgent": "the groups and factions",
        "RelationshipAgent": "the relationships",
        "ThemeAgent": "the themes",
        "MysteryAgent": "the mysteries and reveals",
        "ArcArchitectAgent": "the story arcs",
        "PacingAgent": "the pacing",
        "QuestionAgent": "important choices for you",
        "ReadinessAgent": "what is ready next",
        "KnowledgeAgent": "who knows what",
        "StoryDevelopmentAgent": "chapter-level planning",
        "ScenePlannerAgent": "the next scenes",
        "SceneWriterAgent": "the selected scene draft",
        "ChapterAssemblerAgent": "the chapter assembly",
        "EditorAgent": "the editorial review",
        "DialogueAgent": "the dialogue review",
        "RevisionAgent": "the revision proposal",
        "ManuscriptAgent": "the manuscript review",
        "CanonAgent": "the canon review",
        "StoryAuditorAgent": "the complete story review",
    }
    return labels.get(agent_name, "the story plan")


AGENT_SPECS: List[Dict[str, Any]] = [
    {
        "name": "NarrativeDirectorAgent",
        "purpose": "Evaluate the current story, coordinate the writers room, and identify quality risks.",
        "schema": {
            "summary": "string",
            "reasoning": "string",
            "concerns": ["string"],
            "recommendation": "string",
            "story_vision": {
                "premise": "string", "genre": "string", "themes": ["string"],
                "target_length": "string", "inspirations": ["string"],
                "audience": "string", "narrative_goals": ["string"],
            },
            "ai_insights": {
                "contradictions": ["string"], "missing_information": ["string"],
                "weak_characters": ["string"], "weak_pacing": ["string"],
                "dead_plot_threads": ["string"], "suggested_improvements": ["string"],
                "consistency_score": 0, "worldbuilding_score": 0,
                "character_score": 0, "power_system_score": 0,
            },
        },
    },
    {
        "name": "StoryArchitectAgent",
        "purpose": "Develop open plot threads without creating chapter plans.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "plot_threads": [{
                "title": "string", "description": "string", "status": "open",
                "related_characters": ["string"], "possible_resolutions": ["string"],
            }],
        },
    },
    {
        "name": "CharacterJourneyAgent",
        "purpose": "Create or update concrete characters and their long-term journeys.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "characters": [{
                "name": "string", "role": "string", "age": "string",
                "description": "string", "personality": ["string"], "goals": ["string"],
                "fears": ["string"], "secrets": ["string"], "relationships": ["object"],
                "power": "string", "arc": "string", "current_status": "string",
                "future_payoffs": ["string"], "timeline": ["string"], "agent_notes": "string",
                "beliefs": ["string"], "growth": "string", "future_plans": ["string"],
            }],
        },
    },
    {
        "name": "WorldAgent",
        "purpose": "Develop only world details supported by project context and label unresolved areas.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "world": {
                "world_rules": ["string"], "locations": ["object"], "races": ["object"],
                "history": ["object"], "religion": ["object"], "politics": ["object"],
                "technology": ["object"], "economy": ["object"], "academies": ["object"],
                "current_conflicts": ["string"],
            },
        },
    },
    {
        "name": "PowerSystemAgent",
        "purpose": "Develop the actual power system while preserving locked user decisions.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "power_system": {
                "ranks": ["string"], "levels": ["string"], "cultivation": "string",
                "skills": ["string"], "classes": ["string"], "evolution_paths": ["string"],
                "concept_tree": ["object"], "limitations": ["string"],
                "resources": ["string"], "costs": ["string"],
                "compatibility_rules": ["string"], "progression_logic": "string",
                "progression_curve": "string",
            },
        },
    },
    {
        "name": "FactionAgent",
        "purpose": "Create factions grounded in the current world and conflicts.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "factions": [{
                "name": "string", "leader": "string", "goals": ["string"],
                "enemies": ["string"], "allies": ["string"], "influence": "string",
                "secrets": ["string"], "territory": ["string"],
            }],
        },
    },
    {
        "name": "RelationshipAgent",
        "purpose": "Create relationship edges only between actual named project characters.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "relationships": [{
                "character_a": "string", "character_b": "string", "type": "string",
                "strength": 0, "trust": 0, "history": "string",
                "future_payoff": "string", "status": "string",
            }],
        },
    },
    {
        "name": "ThemeAgent",
        "purpose": "Connect themes, motifs, and symbols to characters and arcs.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "themes": {
                "themes": ["string"], "motifs": ["string"], "symbols": ["string"],
                "payoffs": ["string"], "related_characters": ["string"],
                "related_arcs": ["string"],
            },
        },
    },
    {
        "name": "MysteryAgent",
        "purpose": "Track mysteries, clues, red herrings, reveal targets, and resolution state.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "mysteries": [{
                "question": "string", "truth": "string", "known_clues": ["string"],
                "hidden_clues": ["string"], "red_herrings": ["string"],
                "reveal_target": "string", "status": "open",
            }],
        },
    },
    {
        "name": "ArcArchitectAgent",
        "purpose": "Plan only the requested or current arc and a few lightweight timeline anchors. Preserve unknown future areas and never require all arcs.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "arcs": [{
                "arc_id": "optional stable string", "title": "string",
                "purpose": "string", "goal": "string", "conflict": "string",
                "stakes": "string", "chapter_range": [0, 0],
                "major_events": ["string"], "conflicts": ["string"], "payoffs": ["string"],
                "mysteries": ["string"], "character_growth": ["string"],
                "dependencies": ["arc_id"], "approval_status": "draft",
            }],
            "timeline_events": [{
                "entry_id": "optional stable string", "arc_id": "string",
                "title": "string", "summary": "string", "importance": "major",
                "status": "planned", "certainty": "known|probable|unknown",
                "dependencies": ["entry_id"], "chapter_range": [0, 0],
            }],
        },
    },
    {
        "name": "PacingAgent",
        "purpose": "Evaluate escalation, breathing room, dead zones, and pacing risk across planned arcs.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "pacing_analysis": {
                "weak_pacing": ["string"], "dead_zones": ["string"],
                "escalation_risks": ["string"], "recommendations": ["string"],
                "pacing_score": 0,
            },
        },
    },
    {
        "name": "QuestionAgent",
        "purpose": "Ask only unresolved, optional, high-value questions and offer a default.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "questions": [{
                "text": "string", "choices": ["string"],
                "default_recommendation": "string", "story_area": "string",
            }],
        },
    },
    {
        "name": "ReadinessAgent",
        "purpose": "Propose extensible planning requirements and evidence for the current project or arc. Never mark an item approved or ready.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "readiness_items": [{
                "arc_id": "optional string", "category": "string",
                "title": "string", "description": "string",
                "priority": "required|recommended|optional",
                "status": "missing|discussed|proposed",
                "evidence": ["string"], "blocking": True,
            }],
        },
    },
    {
        "name": "KnowledgeAgent",
        "purpose": "Maintain explicit world truth, reader knowledge, and character knowledge without collapsing their visibility layers.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "knowledge_entries": [{
                "entry_id": "optional stable string", "arc_id": "optional string",
                "title": "string", "content": "string",
                "knowledge_type": "WORLD_TRUTH|READER_KNOWLEDGE|CHARACTER_KNOWLEDGE",
                "known_by": ["string"], "not_known_by": ["string"],
                "learned_how": "string", "is_false": False,
                "confidence": 1.0, "source": "string",
                "reveal_target": "string", "world_truth_entry_id": "optional string",
            }],
        },
    },
    {
        "name": "StoryDevelopmentAgent",
        "purpose": "Develop only the selected current arc as a story-room proposal. Use its maturity, checklist, dependencies, chapter and scene plans, progression, knowledge, foreshadowing, and artifacts. Return proposals only and never write prose or approve work.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "development_proposals": [{
                "arc_id": "string",
                "proposal_type": "arc_refinement|checklist|chapter_plan|scene_plan|progression|knowledge_evolution|foreshadow_chain|artifact_evolution",
                "title": "string",
                "description": "string",
                "rationale": "string",
                "affected_ids": ["string"],
                "priority": "required|recommended|optional",
                "details": {
                    "chapter_number": 1,
                    "purpose": "string", "conflict": "string",
                    "character_focus": ["string"],
                    "dimension": "string", "status": "proposed"
                },
            }],
            "open_questions": ["string"],
        },
    },
    {
        "name": "ScenePlannerAgent",
        "purpose": "Create structured scene plans for approved chapter plans in the selected draftable arc. Never draft prose, dialogue, or scene text.",
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "scene_plans": [{
                "scene_id": "optional stable string", "arc_id": "string",
                "chapter_plan_id": "string", "title": "string",
                "purpose": "string", "conflict": "string", "outcome": "string",
                "character_focus": ["string"], "character_change": "string",
                "knowledge_changes": ["entry_id"], "foreshadow_links": ["entry_id"],
                "artifact_interactions": ["artifact_id"],
                "timeline_impacts": ["entry_id"], "order": 0,
                "status": "planned",
            }],
        },
    },
    {
        "name": "SceneWriterAgent",
        "purpose": (
            "Write a complete reader-facing scene from the approved scene plan and authoritative "
            "Narrative Intelligence context, while also decomposing it into structured paragraph "
            "skeletons for the existing Paragraph Engine. Preserve the author's decisions, voice, "
            "canon, chronology, character knowledge and planned outcome. Use character-driven "
            "conflict, clear stakes, emotional subtext expressed through action and sensory detail, "
            "and meaningful transitions. Avoid exposition dumps and emotional over-explanation. "
            "Never approve prose or mutate planning truth."
        ),
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "scene_draft": {
                "scene_id": "string",
                "generated_text": "complete reader-facing scene prose with dialogue",
                "why": "why this draft approach serves the approved scene plan",
                "expected_impact": "reader-facing narrative effect",
                "affected_narrative_areas": ["character|pacing|emotion|tension|dialogue|description|continuity|theme"],
                "estimated_change_scope": "small|medium|large",
                "preserved_elements": ["approved facts, beats, voice, or outcomes kept unchanged"],
                "context_evidence": ["author decisions or Narrative Intelligence records used"],
                "connection_from_previous": "how this scene begins after the previous approved scene without replaying it",
                "handoff_to_next": "the changed condition or open pressure that makes the next planned scene necessary",
                "scene_goal": "the viewpoint character's concrete goal in this scene",
                "scene_trouble": "the active obstacle that makes the goal difficult",
                "scene_stakes": "what can be lost now, expressed through the approved plan",
                "distinct_progression": "the concrete new event, decision, discovery, or reversal completed in this scene",
                "canon_proposals": [{
                    "canon_type": "character|power|artifact|timeline|knowledge|faction|world|mystery|relationship",
                    "subject": "story subject",
                    "field": "fact field",
                    "value": "new stable fact introduced by the draft",
                    "confidence": 0.0,
                    "evidence": ["exact draft evidence"],
                }],
                "paragraphs": [{
                    "paragraph_id": "string",
                    "order": 1,
                    "purpose": "string",
                    "narrative_goal": "string",
                    "scene_goal": "string",
                    "emotion": "string",
                    "tension_level": "string",
                    "pov": "string",
                    "location": "string",
                    "dialogue_goal": "string",
                    "exposition_goal": "string",
                    "target_word_count": 250,
                    "participating_characters": ["string"],
                    "required_canon": ["string"],
                    "foreshadowing": ["string"],
                    "callbacks": ["string"],
                    "required_events": ["string"],
                    "transition_from_previous": "string",
                    "transition_to_next": "string"
                }],
                "continuity_claims": {
                    "knowledge_entry_ids": ["string"],
                    "artifact_ids": ["string"],
                    "timeline_entry_ids": ["string"],
                    "foreshadow_ids": ["string"],
                    "characters": ["string"],
                    "power_changes": ["string"],
                    "dependency_ids": ["string"]
                },
                "generation_notes": ["string"]
            }
        }
    },
    {
        "name": "ChapterAssemblerAgent",
        "purpose": (
            "Assemble one chapter from the supplied ordered approved scene drafts by "
            "proposing transitions only. Transition links must copy the exact draft_id "
            "values from adjacent approved_scene_drafts. Never rewrite scene prose, invent "
            "scenes or major events, or alter planning truth."
        ),
        "schema": {
            "summary": "string", "reasoning": "string", "concerns": ["string"],
            "recommendation": "string",
            "chapter_assembly": {
                "chapter_plan_id": "string",
                "transitions": [{
                    "from_scene_draft_id": "string",
                    "to_scene_draft_id": "string",
                    "generated_text": "short transition prose",
                }],
                "generation_notes": ["string"],
            },
        },
    },
    {
        "name": "EditorAgent",
        "purpose": (
            "Review exactly the supplied approved scene, chapter, or arc package. "
            "Identify style, voice, pacing, emotional progression, and objective "
            "fulfillment issues with evidence. Do not rewrite prose, modify planning, "
            "or approve any draft or revision."
        ),
        "schema": {
            "summary": "string",
            "reasoning": "string",
            "concerns": ["string"],
            "recommendation": "string",
            "editorial_review": {
                "subject_type": "scene|chapter|arc",
                "subject_id": "string",
                "dimension_scores": {
                    "style": "integer 0-100",
                    "voice_consistency": "integer 0-100",
                    "pacing": "integer 0-100",
                    "objective_fulfillment": "integer 0-100",
                    "emotional_progression": "integer 0-100",
                    "progression_quality": "integer 0-100",
                    "consistency": "integer 0-100",
                    "payoff_readiness": "integer 0-100",
                },
                "findings": {
                    "style": ["object"],
                    "voice": ["object"],
                    "pacing": ["object"],
                    "emotional_progression": ["object"],
                    "objective_fulfillment": ["object"],
                },
                "blockers": ["string"],
                "recommendations": ["string"],
                "evidence": ["string"],
            },
        },
    },
    {
        "name": "DialogueAgent",
        "purpose": (
            "Analyze dialogue in exactly the supplied approved scene or chapter. "
            "Assess realism, distinctiveness, exposition, speaker differentiation, "
            "and conversation flow. Return analysis and recommendations only; never "
            "rewrite or approve prose."
        ),
        "schema": {
            "summary": "string",
            "reasoning": "string",
            "concerns": ["string"],
            "recommendation": "string",
            "dialogue_review": {
                "subject_type": "scene|chapter",
                "subject_id": "string",
                "dimension_scores": {
                    "dialogue": "integer 0-100",
                    "realism": "integer 0-100",
                    "distinctiveness": "integer 0-100",
                    "exposition_control": "integer 0-100",
                    "speaker_differentiation": "integer 0-100",
                    "conversation_flow": "integer 0-100",
                },
                "findings": {"dialogue": ["object"]},
                "blockers": ["string"],
                "recommendations": ["string"],
                "evidence": ["string"],
            },
        },
    },
    {
        "name": "RevisionAgent",
        "purpose": (
            "Create one alternative, author-reviewable revision from the supplied immutable "
            "source snapshot, selected editorial evidence and requested revision pass. "
            "Preserve planning truth, canon, chronology, required events and explicitly "
            "protected elements. Never replace source prose, approve a branch, or create "
            "a manuscript."
        ),
        "schema": {
            "summary": "string",
            "reasoning": "string",
            "concerns": ["string"],
            "recommendation": "string",
            "revision_proposal": {
                "branch_id": "string",
                "generated_text": "alternative revision prose",
                "summary": "string",
                "applied_recommendations": ["string"],
                "changes": ["specific author-facing change"],
                "reason": "why these changes address the selected evidence",
                "affected_elements": ["character|dialogue|pacing|emotion|description|continuity|style|grammar"],
                "estimated_improvement": "small|medium|large with a concise explanation",
                "what_stays_unchanged": ["protected plan, fact, event, voice, or passage"],
            },
        },
    },
    {
        "name": "ManuscriptAgent",
        "purpose": (
            "Review exactly the supplied immutable manuscript version and approved "
            "chapter lineage. Identify book-level structure, continuity, pacing, "
            "progression, and unresolved editorial risks. Return findings and "
            "recommendations only. Never rewrite, assemble, validate, or approve."
        ),
        "schema": {
            "summary": "string",
            "reasoning": "string",
            "concerns": ["string"],
            "recommendation": "string",
            "manuscript_review": {
                "result": "PASS|WARNING|FAIL",
                "findings": ["object"],
                "recommendations": ["string"],
                "evidence": ["string"],
            },
        },
    },
    {
        "name": "CanonAgent",
        "purpose": (
            "Review the supplied active canon and deterministic conflict report. "
            "Identify possible contradictions and missing evidence. Return observations "
            "and recommendations only. Never promote, deactivate, resolve, or approve "
            "canon and never modify planning or drafts."
        ),
        "schema": {
            "summary": "string",
            "reasoning": "string",
            "concerns": ["string"],
            "recommendation": "string",
            "canon_review": {
                "result": "PASS|WARNING|FAIL",
                "findings": ["object"],
                "recommendations": ["string"],
                "evidence": ["string"],
            },
        },
    },
    {
        "name": "StoryAuditorAgent",
        "purpose": (
            "Act as a read-only AI Narrative Reviewer over the supplied shared analysis "
            "graph. Review pacing, repetition, emotional rhythm, structural weaknesses, "
            "continuity, unresolved threads, chapter balance, and tension progression. "
            "Every recommendation must cite supporting evidence and affected story elements. "
            "Return findings only. Never rewrite or modify "
            "drafts, chapters, manuscripts, canon, planning, relationships, mysteries, "
            "artifacts, timelines, or foreshadowing."
        ),
        "schema": {
            "summary": "string",
            "reasoning": "string",
            "concerns": ["string"],
            "recommendation": "string",
            "story_audit": {
                "result": "PASS|WARNING|FAIL",
                "findings": [{
                    "category": "string",
                    "severity": "info|warning|high|critical",
                    "subject_type": "string",
                    "subject_id": "string",
                    "message": "string",
                    "evidence": ["string"],
                    "affected_chapters": ["number"],
                    "affected_scenes": ["string"],
                    "affected_elements": ["string"],
                    "recommended_actions": ["string"],
                }],
            },
        },
    },
]

STUDIO_AGENT_NAMES = [spec["name"] for spec in AGENT_SPECS]


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if value and all(isinstance(item, dict) for item in value.values()):
            return [
                {"name": key, **item} if "name" not in item else item
                for key, item in value.items()
            ]
        return [value]
    if value is None or value == "":
        return []
    return [value]


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _bounded_story_section(value: Any, limit: int = 1600) -> Any:
    """Keep an author-readable Story Bible projection inside the prompt budget."""
    if value in (None, "", [], {}):
        return value
    serialized = json.dumps(value, default=str, ensure_ascii=True)
    if len(serialized) <= limit:
        return value
    return {
        "bounded_excerpt": serialized[:limit],
        "note": "The shared Story Bible section was bounded for this writing request.",
    }


def _writing_story_context(
    story_bible: Any,
    drafting_context: Any,
) -> Dict[str, Any]:
    """Project the shared Story Bible for writing without creating new story truth."""
    bible = _safe_dict(story_bible)
    drafting = _safe_dict(drafting_context)
    scene = _safe_dict(drafting.get("scene_plan"))
    arc = _safe_dict(drafting.get("arc"))
    focus_names = {
        str(value).strip().lower()
        for value in _safe_list(scene.get("character_focus"))
        if str(value).strip()
    }
    arc_id = str(arc.get("arc_id") or scene.get("arc_id") or "")

    def relevant(values: Any, *, maximum: int = 8) -> List[Any]:
        rows = [item for item in _safe_list(values) if isinstance(item, dict)]
        if focus_names:
            matched = [
                item
                for item in rows
                if any(name in json.dumps(item, default=str).lower() for name in focus_names)
            ]
            if matched:
                rows = matched
        return rows[:maximum]

    progressions = [
        item
        for item in _safe_list(bible.get("character_progressions"))
        if isinstance(item, dict)
        and (not arc_id or str(item.get("arc_id") or "") == arc_id)
    ][:8]
    return {
        "story_vision": _bounded_story_section(bible.get("story_vision")),
        "characters": _bounded_story_section(relevant(bible.get("characters"))),
        "character_arcs": _bounded_story_section(progressions),
        "world": _bounded_story_section(bible.get("world")),
        "power_system": _bounded_story_section(bible.get("power_system")),
        "relationships": _bounded_story_section(relevant(bible.get("relationships"))),
        "plot_threads": _bounded_story_section(relevant(bible.get("plot_threads"))),
        "mysteries": _bounded_story_section(relevant(bible.get("mysteries"))),
        "themes": _bounded_story_section(bible.get("themes")),
    }


def _required_output_error(agent_name: str, payload: Any) -> str:
    structured = _safe_dict(payload)
    required_text_paths = {
        "SceneWriterAgent": ("scene_draft", "generated_text"),
        "RevisionAgent": ("revision_proposal", "generated_text"),
    }
    path = required_text_paths.get(agent_name)
    if not path:
        return ""
    nested = _safe_dict(structured.get(path[0]))
    if str(nested.get(path[1]) or "").strip():
        return ""
    return f"{path[0]}.{path[1]} must be a non-empty string"


def _normalize_agent_payload(agent_name: str, payload: Any) -> Dict[str, Any]:
    """Normalize legitimate provider shape variation before strict validation.

    This is deliberately structural only. It never supplies prose, authority
    references, or missing semantic facts on the provider's behalf.
    """
    normalized = dict(_safe_dict(payload))
    if agent_name == "SceneWriterAgent":
        candidate = next(
            (
                _safe_dict(normalized.get(key))
                for key in ("scene_draft", "draft", "scene", "output")
                if _safe_dict(normalized.get(key))
            ),
            {},
        )
        if not candidate and any(
            key in normalized for key in ("generated_text", "prose", "text", "content")
        ):
            candidate = normalized
        draft = dict(candidate)
        if not str(draft.get("generated_text") or "").strip():
            for alias in ("prose", "text", "content", "draft_text", "scene_text"):
                if str(draft.get(alias) or "").strip():
                    draft["generated_text"] = str(draft[alias])
                    break
        if not draft.get("paragraphs"):
            draft["paragraphs"] = draft.get("paragraph_blueprint") or draft.get("beats") or []
        if not draft.get("continuity_claims"):
            draft["continuity_claims"] = draft.get("references") or draft.get("claims") or {}
        normalized["scene_draft"] = draft
    elif agent_name == "RevisionAgent":
        candidate = next(
            (
                _safe_dict(normalized.get(key))
                for key in ("revision_proposal", "revision", "draft", "output")
                if _safe_dict(normalized.get(key))
            ),
            {},
        )
        if not candidate and any(
            key in normalized for key in ("generated_text", "revised_text", "prose", "text")
        ):
            candidate = normalized
        revision = dict(candidate)
        if not str(revision.get("generated_text") or "").strip():
            for alias in ("revised_text", "prose", "text", "content"):
                if str(revision.get(alias) or "").strip():
                    revision["generated_text"] = str(revision[alias])
                    break
        normalized["revision_proposal"] = revision
    elif agent_name == "ChapterAssemblerAgent":
        candidate = next(
            (
                _safe_dict(normalized.get(key))
                for key in ("chapter_assembly", "assembly", "chapter", "output")
                if _safe_dict(normalized.get(key))
            ),
            {},
        )
        if candidate:
            assembly = dict(candidate)
            if not assembly.get("transitions"):
                assembly["transitions"] = assembly.get("scene_transitions") or []
            normalized["chapter_assembly"] = assembly
    return normalized


def _recover_required_text_payload(agent_name: str, content: Any) -> Dict[str, Any]:
    """Recover provider prose when the surrounding structured envelope is malformed.

    The recovery is deliberately narrow: it extracts only a valid JSON string for
    the required prose field, or a clearly unstructured prose response. It never
    recovers canon claims, authority references, approvals, or planning mutations.
    The resulting draft therefore remains derivative author-review material.
    """
    raw = str(content or "").strip()
    if agent_name not in {"SceneWriterAgent", "RevisionAgent"} or not raw:
        return {}
    field = "generated_text"
    marker = f'"{field}"'
    marker_index = raw.find(marker)
    if marker_index >= 0:
        colon_index = raw.find(":", marker_index + len(marker))
        quote_index = raw.find('"', colon_index + 1) if colon_index >= 0 else -1
        if quote_index >= 0:
            try:
                recovered, _ = json.JSONDecoder().raw_decode(raw[quote_index:])
            except (TypeError, ValueError, json.JSONDecodeError):
                recovered = ""
            if isinstance(recovered, str) and recovered.strip():
                container = "scene_draft" if agent_name == "SceneWriterAgent" else "revision_proposal"
                return {container: {field: recovered.strip()}}
    # Some OpenAI-compatible providers ignore response_format and return only
    # reader-facing prose. Accept that as a draft, but never mistake malformed
    # structured JSON for prose.
    if len(raw) >= 300 and marker_index < 0 and not raw.lstrip().startswith(("{", "[")):
        container = "scene_draft" if agent_name == "SceneWriterAgent" else "revision_proposal"
        return {container: {field: raw}}
    return {}


async def _structured_output_error(
    db,
    project_id: str,
    agent_name: str,
    payload: Any,
    state: Dict[str, Any],
) -> str:
    required_error = _required_output_error(agent_name, payload)
    if required_error or agent_name != "SceneWriterAgent":
        return required_error
    scene_draft = _safe_dict(_safe_dict(payload).get("scene_draft"))
    drafting = _safe_dict(state.get("drafting_context"))
    scene = _safe_dict(drafting.get("scene_plan"))
    if not scene:
        return ""
    provider_claims = _safe_dict(scene_draft.get("continuity_claims"))
    reconciled_claims = {
        **provider_claims,
        "knowledge_entry_ids": _safe_list(scene.get("knowledge_changes")),
        "artifact_ids": _safe_list(scene.get("artifact_interactions")),
        "timeline_entry_ids": _safe_list(scene.get("timeline_impacts")),
        "foreshadow_ids": _safe_list(scene.get("foreshadow_links")),
        "characters": _safe_list(scene.get("character_focus")),
    }
    probe = {
        **scene_draft,
        "continuity_claims": reconciled_claims,
        "draft_id": "provider-validation-probe",
        "scene_id": scene.get("scene_id"),
        "arc_id": scene.get("arc_id"),
        "chapter_plan_id": scene.get("chapter_plan_id"),
        "version_number": 0,
    }
    report = await draft_validation_service.validate_scene_draft(
        db,
        project_id,
        probe,
        stage="provider_output",
        persist=False,
    )
    if report["result"] != "FAIL":
        return ""
    preflight = await draft_validation_service.preflight_scene(
        db,
        project_id,
        str(scene.get("scene_id") or ""),
        persist=False,
    )
    violations = [
        str(value)
        for key, values in report.items()
        if key.endswith("_violations") and isinstance(values, list)
        for value in values
        if str(value) not in {
            str(item) for item in preflight.get(key) or []
        }
        # Missing bookkeeping evidence belongs in the review/approval report.
        # It is not proof that provider prose exceeded author-approved authority,
        # so it must not make an otherwise recoverable draft disappear.
        and not str(value).startswith("Missing planned ")
    ]
    if not violations:
        return ""
    return "Deterministic scene authority validation failed: " + "; ".join(violations[:8])


def _compact_cycle_outputs(values: Any) -> List[Dict[str, Any]]:
    compact = []
    for item in _safe_list(values)[-10:]:
        if not isinstance(item, dict):
            continue
        structured = _safe_dict(item.get("structured_output"))
        compact.append(
            {
                "agent_name": item.get("agent_name"),
                "summary": item.get("summary") or structured.get("summary"),
                "recommendation": structured.get("recommendation"),
                "concerns": _safe_list(structured.get("concerns"))[:3],
                "artifacts_created": item.get("artifacts_created") or {},
            }
        )
    return compact


class NarrativeStudioService:
    async def _refresh_live_story_context(self, db, project_id: str, state: Dict[str, Any]) -> None:
        """Expose artifacts saved earlier in this cycle to downstream agents."""
        pid = ObjectId(project_id)
        active = {"project_id": pid, "authority_status": {"$ne": "stale"}}
        story_bible = dict(state.get("story_bible") or {})
        story_bible.update({
            "characters": await db.character_bibles.find(active).sort("name", 1).to_list(length=500),
            "character_journeys": await db.character_journeys.find(active).sort("character_name", 1).to_list(length=500),
            "world": await db.world_bibles.find_one(active) or {},
            "power_system": await db.power_systems.find_one(active) or {},
            "factions": await db.factions.find(active).to_list(length=500),
            "relationships": await db.relationship_graphs.find(active).to_list(length=1000),
            "themes": await db.theme_registry.find_one(active) or {},
            "mysteries": await db.mystery_registry.find(active).to_list(length=1000),
            "timeline": await db.timeline_entries.find(active).sort("order", 1).to_list(length=5000),
            "arcs": await db.story_arcs.find(active).sort("order", 1).to_list(length=1000),
            "plot_threads": await db.plot_threads.find(active).to_list(length=1000),
            "questions": await db.questions.find({"project_id": pid}).sort("created_at", 1).to_list(length=1000),
            "drafting": {
                "chapter_plans": await db.chapter_plans.find(active).sort("chapter_number", 1).to_list(length=5000),
                "scene_plans": await db.scene_plans.find(active).sort("order", 1).to_list(length=20000),
            },
        })
        state["story_bible"] = story_bible
        canon = await get_canon_context(db, project_id)
        state["canon_facts"] = canon["locked_facts"]
        state["decision_registry"] = canon["decisions"]
        state["rejected_decisions"] = canon["rejected_decisions"]

    async def _assignment(self, db, agent_name: str) -> Tuple[Any, AgentModelAssignment]:
        settings = await orchestration_engine.get_settings(db)
        assignments = {item.agent_name: item for item in await orchestration_engine.get_assignments(db)}
        assignment = assignments.get(agent_name) or AgentModelAssignment(
            agent_name=agent_name,
            provider=settings.default_provider,
            model=settings.default_model,
        )
        return settings, assignment

    async def _run_agent(
        self,
        db,
        *,
        agent_spec: Dict[str, Any],
        project: Dict[str, Any],
        state: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        agent_name = agent_spec["name"]
        settings, assignment = await self._assignment(db, agent_name)
        model_override = (state.get("agent_model_overrides") or {}).get(agent_name) or {}
        provider = normalize_provider(model_override.get("provider") or assignment.provider or settings.default_provider)
        model = str(model_override.get("model") or assignment.model or settings.default_model)
        if settings.execution_mode == "mock":
            provider = "mock"
            model = "mock-narrative-intelligence"
        elif provider == "mock":
            provider = normalize_provider(settings.default_provider)
            model = settings.default_model
            if provider == "mock":
                raise ProviderError(
                    "MOCK_MODE",
                    f"{agent_name} requires a real provider in {settings.execution_mode} mode",
                    provider,
                    model,
                )

        memory_query = " ".join([
            agent_spec["purpose"],
            *(str(item.get("content") or "") for item in state.get("new_messages") or []),
        ])
        provider_recall = await memory_provider_service.recall(
            db, str(project["_id"]), memory_query, top_k=8,
            refresh_index=False, safe_for_writing=True,
            consumer="develop_story_specialist",
        )
        retrieved_memory = provider_recall.get("primary", {}).get("hits") or []
        await agent_memory_service.sync_important(
            db,
            project_id=str(project["_id"]),
            agent_name=agent_name,
            canon_facts=state.get("canon_facts") or [],
            decisions=state.get("decision_registry") or [],
        )
        agent_memory = await agent_memory_service.get_context(
            db,
            project_id=str(project["_id"]),
            agent_name=agent_name,
        )
        target_arc_id = str(state.get("target_arc_id") or "")
        target_arc = None
        if target_arc_id:
            target_arc = await db.story_arcs.find_one(
                {
                    "project_id": project["_id"],
                    "arc_id": target_arc_id,
                    "authority_status": {"$ne": "stale"},
                }
            )
        if not target_arc:
            target_arc = await db.story_arcs.find_one(
                {
                    "project_id": project["_id"],
                    "authority_status": {"$ne": "stale"},
                    "focus_role": "current",
                    "development_status": {"$nin": ["completed", "archived"]},
                },
                sort=[("order", 1)],
            )
        context = {
            "project": {
                key: project.get(key)
                for key in [
                    "title", "premise", "idea_dump", "genre", "tone", "themes",
                    "inspirations", "target_length", "audience", "narrative_goals",
                    "character_notes", "world_notes", "plot_notes", "notes",
                ]
            },
            "cycle_number": int(state.get("cycle_number") or 1),
            "new_messages": state.get("new_messages") or [],
            "confirmed_story_studio_planning": state.get("confirmed_story_studio_planning") or [],
            "canon_facts": state.get("canon_facts") or [],
            "decisions": state.get("decision_registry") or [],
            "rejected_decisions": state.get("rejected_decisions") or [],
            "retrieved_memory": retrieved_memory,
            "agent_memory": agent_memory,
            "arc_focus": {
                "target_arc_id": str((target_arc or {}).get("arc_id") or ""),
                "focus_role": (target_arc or {}).get("focus_role"),
                "development_status": (target_arc or {}).get("development_status"),
                "maturity_score": (target_arc or {}).get("arc_maturity_score"),
                "arc": target_arc or {},
            },
            "story_bible": state.get("story_bible") or {},
            "cycle_outputs": state.get("cycle_outputs") or [],
            "drafting_context": state.get("drafting_context") or {},
            "editorial_context": state.get("editorial_context") or {},
            "manuscript_context": state.get("manuscript_context") or {},
            "canon_governance_context": state.get("canon_governance_context") or {},
            "story_audit_context": state.get("story_audit_context") or {},
            "chapter_memory": await chapter_intelligence_service.memory_packet(
                db,
                str(project["_id"]),
                recent_limit=10,
                obligation_limit=12,
            ),
        }
        model_info = await model_registry_service.get_model(provider, model)
        model_window = int((model_info.context_window if model_info else 0) or settings.max_context_tokens or 120000)
        output_reserve = max(int(assignment.max_tokens or 4096) * 2, 8192)
        # Never claim more prompt space than the selected model can accept.
        # Small/local models use a proportional response reserve; large models
        # keep the wider fixed reserve requested by the assignment.
        safe_reserve = min(output_reserve, max(1024, model_window // 4))
        available_context = max(2048, model_window - safe_reserve)
        if model_info and model_info.supports_large_context:
            # Large-context models should be allowed to see the broad Story
            # Bible when useful. Keep a reserve for the response and provider
            # tokenisation differences rather than treating context as truly
            # unbounded.
            context_budget = min(available_context, 900000)
        else:
            configured_budget = int(settings.max_context_tokens or 120000)
            context_budget = min(configured_budget, available_context)

        def context_tokens() -> int:
            return max(1, len(json.dumps(context, default=str, ensure_ascii=False)) // 4)

        # Progressive disclosure: exact authority records remain, while broad
        # projections and older retrieval results are reduced first when a
        # smaller model cannot accept the complete project packet.
        while context_tokens() > context_budget and len(context["retrieved_memory"]) > 4:
            context["retrieved_memory"].pop()
        while context_tokens() > context_budget and len(context["cycle_outputs"]) > 2:
            context["cycle_outputs"].pop(0)
        if context_tokens() > context_budget and isinstance(context["story_bible"], dict):
            always_keep = {
                "story_vision", "characters", "world", "arcs", "plot_threads",
                "timeline", "questions", "canon_governance", "decisions",
                "readiness", "arc_development", "drafting",
            }
            context["story_bible"] = {
                key: value
                for key, value in context["story_bible"].items()
                if key in always_keep
            }
        if context_tokens() > context_budget:
            for key in ("chapter_memory", "story_audit_context", "editorial_context"):
                value = context.get(key)
                if isinstance(value, dict):
                    context[key] = {
                        child_key: child_value[:20] if isinstance(child_value, list) else child_value
                        for child_key, child_value in value.items()
                    }

        final_context_tokens = context_tokens()
        context_packet = {
            "project_id": project["_id"],
            "cycle_number": int(state.get("cycle_number") or 1),
            "agent_name": agent_name,
            "task": agent_spec["purpose"],
            "packet": {
                "active_context": context["new_messages"],
                "working_memory": context["canon_facts"] + context["decisions"],
                "retrieved_memory": retrieved_memory,
                "compressed_memory": agent_memory["compressed"],
                "important_memory": agent_memory["important"],
                "recent_memory": agent_memory["recent"],
                "core_memory": agent_memory.get("core", []),
                "token_estimate": final_context_tokens,
                "context_budget": context_budget,
                "model_context_window": model_window,
            },
            "token_estimate": final_context_tokens,
            "context_budget": context_budget,
            "model_context_window": model_window,
            "tokens_by_source": {
                key: max(1, len(json.dumps(value, default=str, ensure_ascii=False)) // 4)
                for key, value in context.items()
            },
            "created_at": datetime.utcnow(),
        }
        context_packet_result = await db.context_packets.insert_one(context_packet)
        drafting_agent = agent_name in {"SceneWriterAgent", "ChapterAssemblerAgent"}
        editorial_agent = agent_name in {
            "EditorAgent",
            "DialogueAgent",
            "RevisionAgent",
        }
        governance_agent = agent_name in {"ManuscriptAgent", "CanonAgent"}
        audit_agent = agent_name == "StoryAuditorAgent"
        if agent_name == "SceneWriterAgent":
            authority_instruction = (
                "Generated prose is derivative. Use only the supplied approved planning and "
                "drafting context. Return no planning mutations and never approve a draft. "
                "Describe story references using the supplied story labels when useful. The "
                "application resolves stable machine identity; never guess or manufacture an "
                "internal ID. power_changes must be exact strings "
                "from approved new_abilities or mastered_abilities and must be [] when the "
                "scene does not explicitly realize one of those changes."
                " Keep human imperfection in the prose: characters may misunderstand, "
                "hold biased or incorrect beliefs, speak unevenly, overreact, underreact, "
                "or make poor decisions. Vary rhythm and structure. Preserve ambiguity "
                "and imperfect outcomes. Avoid polished filler, emotional over-explanation, "
                "formulaic beats, and uniformly clean resolutions."
                " When previous_approved_scene is supplied, begin after its ending, treat its "
                "events as already completed, and do not replay its discovery, confrontation, "
                "or resolution. Make the current character goal, active trouble, and stakes "
                "visible through action. Use next_scene_plan only to leave a meaningful changed "
                "condition or pressure; do not draft that future scene early."
                " The current linked drafting_context.timeline event is the concrete new "
                "progression for this scene. Enact it rather than merely repeating an earlier "
                "realization. If adjacent plans use similar wording, differentiate this scene "
                "through its linked timeline event, chapter purpose, and a new decision, "
                "discovery, confrontation, or reversal."
                " Only scene_plan.character_focus may appear as named participating characters "
                "in this scene. Relationship and Story Bible characters outside that list are "
                "reference-only; do not place them in dialogue or action, and never include them "
                "in continuity_claims.characters."
                " Do not invent a proper name or stable world, relationship, history, power, "
                "or character fact when the context leaves it undefined; keep it unnamed or "
                "ambiguous. If a new stable fact is genuinely necessary for the prose, include "
                "it in scene_draft.canon_proposals so it remains pending author approval."
            )
        elif agent_name == "ChapterAssemblerAgent":
            authority_instruction = (
                "Generated prose is derivative. Preserve approved scene drafts verbatim. "
                "Return transitions only between adjacent supplied draft IDs, invent no "
                "scene or event, make no planning mutation, and never approve a draft."
            )
        elif agent_name == "EditorAgent":
            authority_instruction = (
                "Editorial findings are derivative. Review only the supplied immutable "
                "approved content and planning evidence. Do not rewrite prose, change a "
                "score record, alter planning truth, or approve any work."
            )
        elif agent_name == "DialogueAgent":
            authority_instruction = (
                "Dialogue findings are derivative. Analyze only the supplied immutable "
                "approved content. Do not return rewritten dialogue, modify a draft, "
                "alter planning truth, or approve any work."
            )
        elif agent_name == "RevisionAgent":
            authority_instruction = (
                "The revision is an alternative proposal only. Preserve approved planning "
                "events and continuity, return one complete proposal, do not modify or "
                "replace the approved source, and never approve the branch."
            )
        elif agent_name == "ManuscriptAgent":
            authority_instruction = (
                "The supplied manuscript version and approved chapters are immutable. "
                "Return review findings only. Do not rewrite, assemble, validate, approve, "
                "archive, or change any manuscript, chapter, scene, plan, or canon record."
            )
        elif agent_name == "CanonAgent":
            authority_instruction = (
                "Canon authority is deterministic and user-governed. Return observations "
                "only. Do not promote, deactivate, resolve, approve, or modify canon, "
                "planning records, drafts, or manuscript content."
            )
        elif audit_agent:
            authority_instruction = (
                "This is a read-only audit. Return findings with concrete evidence only. "
                "Do not propose replacement prose and do not mutate or approve any story "
                "record. Look specifically for abandoned obligations, canon drift, "
                "repetitive structures, artificial emotional regularity, excessive "
                "exposition, overly clean resolutions, and stereotypical AI prose."
            )
        else:
            authority_instruction = (
                "Chapter and scene prose is forbidden for this planning agent."
            )
        if drafting_agent:
            prompt_context = {
                "project": context["project"],
                "drafting_context": context["drafting_context"],
                "arc_focus": context["arc_focus"],
                "narrative_intelligence": _writing_story_context(
                    context["story_bible"],
                    context["drafting_context"],
                ),
                "recent_chapter_memory": context["chapter_memory"],
                "canon_facts": context["canon_facts"],
                "approved_decisions": context["decisions"],
                "confirmed_story_studio_planning": context["confirmed_story_studio_planning"],
                "rejected_decisions": context["rejected_decisions"],
                "agent_memory": context["agent_memory"],
            }
        elif editorial_agent:
            prompt_context = {
                "project": context["project"],
                "editorial_context": context["editorial_context"],
                "arc_focus": context["arc_focus"],
                "canon_facts": context["canon_facts"],
                "approved_decisions": context["decisions"],
                "confirmed_story_studio_planning": context["confirmed_story_studio_planning"],
                "rejected_decisions": context["rejected_decisions"],
                "agent_memory": context["agent_memory"],
            }
        elif governance_agent:
            prompt_context = {
                "project": context["project"],
                "manuscript_context": context["manuscript_context"],
                "canon_governance_context": context["canon_governance_context"],
                "canon_facts": context["canon_facts"],
                "approved_decisions": context["decisions"],
                "agent_memory": context["agent_memory"],
            }
        elif audit_agent:
            prompt_context = {
                "project": {
                    key: context["project"].get(key)
                    for key in (
                        "title",
                        "premise",
                        "genre",
                        "tone",
                        "themes",
                        "target_length",
                        "audience",
                        "narrative_goals",
                    )
                    if context["project"].get(key) not in (None, "", [], {})
                },
                "story_audit_context": context["story_audit_context"],
            }
        else:
            legacy_prompt_context = {
                "project": context["project"],
                "new_messages": context["new_messages"][-20:],
                # This is refreshed after every successful specialist so later
                # specialists in the same development pass see newly-created
                # characters, world facts, arcs, relationships, and timelines.
                "current_story_plan": context["story_bible"],
                "canon_facts": context["canon_facts"][-60:],
                "approved_decisions": context["decisions"][-60:],
                "confirmed_story_studio_planning": context["confirmed_story_studio_planning"][-120:],
                "rejected_decisions": context["rejected_decisions"][-30:],
                "retrieved_memory": context["retrieved_memory"][:20],
                "agent_memory": context["agent_memory"],
                "arc_focus": context["arc_focus"],
                "recent_cycle_outputs": _compact_cycle_outputs(
                    context["cycle_outputs"]
                ),
                "chapter_memory": context["chapter_memory"],
            }
            phase_e_attribution: Dict[str, Any] = {
                "mode": "legacy",
                "fallback_reason": "",
                "duplicate_tokens_removed": 0,
            }
            if state.get("develop_story_context_mode") == "legacy":
                prompt_context = legacy_prompt_context
            else:
                role_packet = develop_story_context_service.build_packet(
                    agent_name=agent_name,
                    project=project,
                    state={
                        **state,
                        "arc_focus": context["arc_focus"],
                        "chapter_memory": context["chapter_memory"],
                    },
                    retrieved_memory=context["retrieved_memory"],
                    agent_memory=context["agent_memory"],
                )
                phase_e_attribution = role_packet["attribution"]
                if role_packet["fallback_required"]:
                    prompt_context = legacy_prompt_context
                    phase_e_attribution = {
                        **phase_e_attribution,
                        "mode": "broad_fallback",
                    }
                else:
                    prompt_context = role_packet["context"]
        serialized_context = json.dumps(
            prompt_context,
            default=str,
            ensure_ascii=False,
        )
        await db.context_packets.update_one(
            {"_id": context_packet_result.inserted_id},
            {"$set": {
                "prompt_tokens": max(1, len(serialized_context) // 4),
                "prompt_tokens_by_source": {
                    key: max(1, len(json.dumps(value, default=str, ensure_ascii=False)) // 4)
                    for key, value in prompt_context.items()
                },
                "repeated_information": {
                    "story_bible_and_confirmed_planning_present": bool(
                        prompt_context.get("current_story_plan")
                        and prompt_context.get("confirmed_story_studio_planning")
                    ),
                    "story_bible_and_chapter_memory_present": bool(
                        prompt_context.get("current_story_plan")
                        and prompt_context.get("chapter_memory")
                    ),
                    "previous_agent_outputs_present": bool(
                        prompt_context.get("recent_cycle_outputs")
                    ),
                },
                "phase_e_attribution": (
                    phase_e_attribution
                    if not drafting_agent and not editorial_agent and not governance_agent and not audit_agent
                    else {"mode": "not_applicable"}
                ),
            }},
        )
        # Match the prompt guard to the selected model instead of imposing the
        # historical 30k-character ceiling on large-context providers.
        phase_e_budget = (
            (
                context_budget
                if phase_e_attribution.get("mode") == "broad_fallback"
                else int(phase_e_attribution.get("packet_budget_tokens") or context_budget)
            )
            if not drafting_agent and not editorial_agent and not governance_agent and not audit_agent
            else context_budget
        )
        prompt_character_budget = max(30000, min(phase_e_budget * 4 + 20000, 3_600_000))
        if len(serialized_context) > prompt_character_budget:
            raise ValueError(
                f"{agent_name} context exceeds the selected model's safe prompt budget of {prompt_character_budget} characters"
            )
        prompt = (
            "You are an agent in NovelForge, a professional narrative planning studio. "
            "Return ONLY valid JSON matching the supplied schema. Do not invent generic filler. "
            "Create entities only when supported by the project context. Locked canon and approved "
            f"decisions are binding. Do not re-ask resolved questions. {authority_instruction}\n\n"
            f"Agent: {agent_name}\nPurpose: {agent_spec['purpose']}\n"
            "Confirmed Story Studio planning is author-confirmed planning input. Preserve it unless the workflow creates an explicit reconsideration question; raw conversation and candidate memory never outrank it.\n"
            "Native retrieval, chapter intelligence, and specialist handoffs are derived evidence. If they conflict with the authority snapshot, identify the conflict and follow authority; never promote candidate, rejected, stale, or superseded material into a story fact.\n"
            f"Required JSON schema example:\n{json.dumps(agent_spec['schema'], ensure_ascii=True)}\n\n"
            f"Project context:\n{serialized_context}"
        )
        fallbacks = list(model_override.get("fallbacks") or [])
        if settings.execution_mode == "hybrid":
            configured = [
                {"provider": item.provider, "model": item.model}
                for item in await orchestration_engine.get_assignments(db)
                if item.enabled and item.provider != "mock" and item.model
            ]
            fallbacks = [
                item for item in configured
                if normalize_provider(item["provider"]) != provider or item["model"] != model
            ][:2]
            fallbacks.extend(configured)
        deduped_fallbacks = []
        seen_fallbacks: set[tuple[str, str]] = set()
        for item in fallbacks:
            key = (normalize_provider(str(item.get("provider") or "")), str(item.get("model") or ""))
            if not key[0] or not key[1] or key == (provider, model) or key in seen_fallbacks:
                continue
            seen_fallbacks.add(key)
            deduped_fallbacks.append({"provider": key[0], "model": key[1]})
        fallbacks = deduped_fallbacks
        messages = [
            {
                "role": "system",
                "content": (
                    "Return strict structured derivative-drafting JSON."
                    if drafting_agent
                    else (
                        "Return strict structured read-only narrative-audit JSON."
                        if audit_agent
                        else "Return strict structured narrative-planning JSON."
                    )
                ),
            },
            {"role": "user", "content": prompt},
        ]
        final_serialized_prompt_tokens = sum(
            max(1, len(str(message.get("content") or "")) // 4)
            for message in messages
        )
        prompt_telemetry: Dict[str, Any] = {
            "final_serialized_prompt_tokens": final_serialized_prompt_tokens,
            "prompt_envelope_tokens": max(
                0,
                final_serialized_prompt_tokens - max(1, len(serialized_context) // 4),
            ),
        }
        if not drafting_agent and not editorial_agent and not governance_agent and not audit_agent:
            prompt_telemetry["phase_e_attribution.final_serialized_prompt_tokens"] = final_serialized_prompt_tokens
        await db.context_packets.update_one(
            {"_id": context_packet_result.inserted_id},
            {"$set": prompt_telemetry},
        )
        trace_context = {
            "project_id": str(project["_id"]),
            "run_id": str(state.get("run_id") or ""),
            "cycle_number": int(state.get("cycle_number") or 1),
            "plan_id": str(state.get("plan_id") or ""),
        }
        # Reader-facing prose plus its governed metadata is substantially larger
        # than a planning artifact. Respect the configured assignment budget for
        # prose-producing agents; the former 3k cap could truncate valid JSON
        # before generated_text closed, causing needless corrective retries.
        output_tokens = (
            assignment.max_tokens
            if agent_name in {"SceneWriterAgent", "RevisionAgent"}
            else min(assignment.max_tokens, 3000)
        )
        result = await provider_gateway.generate_with_failover(
            db,
            messages,
            provider=provider,
            model=model,
            fallbacks=fallbacks,
            temperature=assignment.temperature,
            max_tokens=output_tokens,
            agent_name=agent_name,
            expect_json=True,
            trace_context=trace_context,
        )
        parsed = _normalize_agent_payload(
            agent_name,
            result.get("parsed")
            or _recover_required_text_payload(agent_name, result.get("content")),
        )
        attempts = [result]
        output_error = await _structured_output_error(
            db,
            str(project["_id"]),
            agent_name,
            parsed,
            state,
        )
        await execution_trace_service.mark_application_outcome(
            db,
            result.get("execution_trace_id"),
            provider_success=True,
            parse_success=isinstance(result.get("parsed"), dict),
            validation_success=not bool(output_error),
            reference_resolution_success=(not bool(output_error) if drafting_agent else None),
            persistence_success=False,
            approval_eligible=False,
            final_outcome=(
                "ready_for_application_persistence"
                if not output_error
                else "application_validation_failed_pending_correction"
            ),
            failure_reason=output_error or None,
        )
        if output_error:
            result = await provider_gateway.generate_with_failover(
                db,
                [
                    *messages,
                    {
                        "role": "user",
                        "content": (
                            "The previous response was valid JSON but failed a required output "
                            f"constraint: {output_error}. Generate the complete response again. "
                            "Return only the full corrected JSON object, preserving every required "
                            "schema field and including substantive prose in the missing field."
                        ),
                    },
                ],
                provider=provider,
                model=model,
                fallbacks=fallbacks,
                temperature=assignment.temperature,
                max_tokens=output_tokens,
                agent_name=agent_name,
                expect_json=True,
                trace_context={
                    **trace_context,
                    "corrective_retry": True,
                    "corrective_reason": output_error,
                },
            )
            attempts.append(result)
            parsed = _normalize_agent_payload(
                agent_name,
                result.get("parsed")
                or _recover_required_text_payload(agent_name, result.get("content")),
            )
            remaining_error = await _structured_output_error(
                db,
                str(project["_id"]),
                agent_name,
                parsed,
                state,
            )
            await execution_trace_service.mark_application_outcome(
                db,
                result.get("execution_trace_id"),
                provider_success=True,
                parse_success=isinstance(result.get("parsed"), dict),
                validation_success=not bool(remaining_error),
                reference_resolution_success=(not bool(remaining_error) if drafting_agent else None),
                persistence_success=False,
                approval_eligible=False,
                final_outcome=(
                    "ready_for_application_persistence"
                    if not remaining_error
                    else "application_validation_failed"
                ),
                failure_reason=remaining_error or None,
            )
            if remaining_error:
                raise ValueError(
                    f"{agent_name} could not satisfy authority constraints after correction: "
                    f"{remaining_error}"
                )
        tokens = sum(int(item.get("tokens_used") or 0) for item in attempts)
        estimated_cost = sum(
            estimate_cost(
                int(item.get("tokens_used") or 0),
                item.get("provider") or provider,
                item.get("model") or model,
            )
            for item in attempts
        )
        metadata = {
            "provider": normalize_provider(result.get("provider") or provider),
            "model": result.get("model") or model,
            "tokens": tokens,
            "cost": round(estimated_cost, 6),
            "latency": sum(int(item.get("latency_ms") or 0) for item in attempts),
            "execution_trace_id": str(result.get("execution_trace_id") or ""),
            "execution_trace_ids": [
                str(item.get("execution_trace_id") or "")
                for item in attempts
                if item.get("execution_trace_id")
            ],
            "corrective_retry_count": len(attempts) - 1,
            "cycle_generated": int(state.get("cycle_number") or 1),
            "timestamp": datetime.utcnow(),
            "source_type": "real_ai" if result.get("provider") != "mock" else "test_mock",
            "mock_used": result.get("provider") == "mock",
            "fallback_used": any(bool(item.get("fallback_used")) for item in attempts),
            "contributing_agents": [agent_name],
            "application_outcome": {
                "provider_success": True,
                "parse_success": True,
                "validation_success": True,
                "reference_resolution_success": True if drafting_agent else None,
                "persistence_success": False,
                "approval_eligible": False,
                "final_outcome": "ready_for_application_persistence",
            },
        }
        return parsed, metadata

    async def _upsert_many(self, collection, project_id: str, cycle: int, items, key_fields, meta):
        saved = 0
        for item in _safe_list(items):
            if not isinstance(item, dict) or not all(item.get(key) for key in key_fields):
                continue
            query = {"project_id": ObjectId(project_id), **{key: item[key] for key in key_fields}}
            doc = {
                "project_id": ObjectId(project_id),
                **item,
                **meta,
                "cycle_generated": cycle,
                "updated_at": datetime.utcnow(),
            }
            await collection.update_one(
                query,
                {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                upsert=True,
            )
            saved += 1
        return saved

    async def _persist_artifacts(
        self,
        db,
        *,
        project_id: str,
        cycle: int,
        agent_name: str,
        payload: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        pid = ObjectId(project_id)
        if payload.get("story_vision"):
            vision = _safe_dict(payload["story_vision"])
            for field in ["themes", "inspirations", "narrative_goals"]:
                vision[field] = _safe_list(vision.get(field))
            doc = {"project_id": pid, **vision, **meta, "cycle_generated": cycle, "updated_at": datetime.utcnow()}
            await db.story_visions.update_one({"project_id": pid}, {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}}, upsert=True)
            counts["story_vision"] = 1
        if payload.get("ai_insights"):
            insight = _safe_dict(payload["ai_insights"])
            for field in [
                "contradictions", "missing_information", "weak_characters",
                "weak_pacing", "dead_plot_threads", "suggested_improvements",
            ]:
                insight[field] = _safe_list(insight.get(field))
            doc = {
                "project_id": pid,
                **insight,
                "agent_concerns": insight.get("concerns") or payload.get("concerns") or [],
                "missing_story_areas": insight.get("missing_information") or [],
                "potential_contradictions": insight.get("contradictions") or [],
                **meta, "cycle_generated": cycle, "updated_at": datetime.utcnow(),
            }
            await db.ai_insights.update_one({"project_id": pid}, {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}}, upsert=True)
            counts["ai_insights"] = 1
        if payload.get("pacing_analysis"):
            pacing = _safe_dict(payload["pacing_analysis"])
            await db.ai_insights.update_one(
                {"project_id": pid},
                {
                    "$set": {
                        "project_id": pid,
                        "weak_pacing": pacing.get("weak_pacing") or [],
                        "pacing_dead_zones": pacing.get("dead_zones") or [],
                        "pacing_escalation_risks": pacing.get("escalation_risks") or [],
                        "pacing_recommendations": pacing.get("recommendations") or [],
                        "pacing_score": pacing.get("pacing_score"),
                        **meta,
                        "cycle_generated": cycle,
                        "updated_at": datetime.utcnow(),
                    },
                    "$setOnInsert": {"created_at": datetime.utcnow()},
                },
                upsert=True,
            )
            counts["ai_insights"] = 1
        if payload.get("characters"):
            counts["characters"] = await self._upsert_many(db.character_bibles, project_id, cycle, payload["characters"], ["name"], meta)
            for item in _safe_list(payload["characters"]):
                if not isinstance(item, dict) or not item.get("name"):
                    continue
                journey = {
                    "project_id": pid, "character_name": item["name"],
                    "goals": [str(value).strip() for value in _safe_list(item.get("goals")) if str(value).strip()],
                    "fears": [str(value).strip() for value in _safe_list(item.get("fears")) if str(value).strip()],
                    "beliefs": item.get("beliefs") or [], "growth": item.get("growth") or item.get("arc") or "",
                    "relationships": item.get("relationships") or [], "status": item.get("current_status") or "",
                    "arc_progression": item.get("timeline") or [], "future_plans": item.get("future_plans") or item.get("future_payoffs") or [],
                    **meta, "cycle_generated": cycle, "updated_at": datetime.utcnow(),
                }
                await db.character_journeys.update_one(
                    {"project_id": pid, "character_name": item["name"]},
                    {"$set": journey, "$setOnInsert": {"created_at": datetime.utcnow()}},
                    upsert=True,
                )
        if payload.get("world"):
            world_payload = _safe_dict(payload["world"])
            for field in [
                "world_rules", "locations", "races", "history", "religion",
                "politics", "technology", "economy", "academies",
                "current_conflicts",
            ]:
                world_payload[field] = _safe_list(world_payload.get(field))
            world = {"project_id": pid, **world_payload, **meta, "cycle_generated": cycle, "updated_at": datetime.utcnow()}
            await db.world_bibles.update_one({"project_id": pid}, {"$set": world, "$setOnInsert": {"created_at": datetime.utcnow()}}, upsert=True)
            counts["world"] = 1
        if payload.get("power_system"):
            power_payload = _safe_dict(payload["power_system"])
            for field in [
                "ranks", "levels", "skills", "classes", "evolution_paths",
                "concept_tree", "limitations", "resources", "costs",
                "compatibility_rules",
            ]:
                power_payload[field] = _safe_list(power_payload.get(field))
            power = {"project_id": pid, **power_payload, **meta, "cycle_generated": cycle, "updated_at": datetime.utcnow()}
            await db.power_systems.update_one({"project_id": pid}, {"$set": power, "$setOnInsert": {"created_at": datetime.utcnow()}}, upsert=True)
            counts["power_system"] = 1
        if payload.get("arcs"):
            saved = 0
            for index, item in enumerate(_safe_list(payload["arcs"]), start=1):
                if not isinstance(item, dict) or not item.get("title"):
                    continue
                existing = None
                if item.get("arc_id"):
                    existing = await db.story_arcs.find_one(
                        {"project_id": pid, "arc_id": str(item["arc_id"])}
                    )
                if not existing:
                    existing = await db.story_arcs.find_one(
                        {"project_id": pid, "title": item["title"]}
                    )
                if existing and str(existing.get("approval_status") or "").lower() in {
                    "approved", "active", "completed"
                }:
                    continue
                arc_id = str((existing or {}).get("arc_id") or item.get("arc_id") or uuid4())
                chapter_range = item.get("chapter_range") or (existing or {}).get("chapter_range") or []
                arc_doc = {
                    "project_id": pid,
                    **item,
                    "arc_id": arc_id,
                    "approval_status": str(item.get("approval_status") or "draft").lower(),
                    "development_status": str(
                        item.get("development_status")
                        or (existing or {}).get("development_status")
                        or "idea"
                    ).lower(),
                    "focus_role": str(
                        item.get("focus_role")
                        or (existing or {}).get("focus_role")
                        or "future"
                    ).lower(),
                    "chapter_range": chapter_range if isinstance(chapter_range, list) else [],
                    "readiness_status": (existing or {}).get("readiness_status") or "NOT_READY",
                    "drafting_eligible": False,
                    "arc_maturity_score": int(
                        (existing or {}).get("arc_maturity_score") or 0
                    ),
                    "maturity_threshold": int(
                        (existing or {}).get("maturity_threshold") or 85
                    ),
                    "maturity_details": (existing or {}).get("maturity_details") or {},
                    "resolution_direction": str(
                        item.get("resolution_direction")
                        or (existing or {}).get("resolution_direction")
                        or ""
                    ),
                    "order": int((existing or {}).get("order") or index),
                    **meta,
                    "cycle_generated": cycle,
                    "updated_at": datetime.utcnow(),
                }
                query = {"_id": existing["_id"]} if existing else {
                    "project_id": pid, "arc_id": arc_id
                }
                await db.story_arcs.update_one(
                    query,
                    {"$set": arc_doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                    upsert=True,
                )
                saved += 1
            counts["arcs"] = saved
        for key, collection, fields in [
            ("factions", db.factions, ["name"]),
            ("relationships", db.relationship_graphs, ["character_a", "character_b"]),
            ("mysteries", db.mystery_registry, ["question"]),
            ("plot_threads", db.plot_threads, ["title"]),
        ]:
            if payload.get(key):
                counts[key] = await self._upsert_many(collection, project_id, cycle, payload[key], fields, meta)
        if payload.get("scene_plans"):
            saved = 0
            for index, item in enumerate(_safe_list(payload["scene_plans"]), start=1):
                if not isinstance(item, dict) or not item.get("title"):
                    continue
                arc_id = str(item.get("arc_id") or "")
                chapter_plan_id = str(item.get("chapter_plan_id") or "")
                chapter = await db.chapter_plans.find_one(
                    {
                        "project_id": pid,
                        "chapter_plan_id": chapter_plan_id,
                        "arc_id": arc_id,
                    }
                )
                if not chapter:
                    continue
                scene_id = str(item.get("scene_id") or uuid4())
                doc = {
                    "project_id": pid,
                    "scene_id": scene_id,
                    "arc_id": arc_id,
                    "chapter_plan_id": chapter_plan_id,
                    "title": str(item.get("title") or "Untitled scene plan"),
                    "purpose": str(item.get("purpose") or ""),
                    "conflict": str(item.get("conflict") or ""),
                    "outcome": str(item.get("outcome") or ""),
                    "character_focus": _safe_list(item.get("character_focus")),
                    "character_change": str(item.get("character_change") or ""),
                    "knowledge_changes": _safe_list(item.get("knowledge_changes")),
                    "foreshadow_links": _safe_list(item.get("foreshadow_links")),
                    "artifact_interactions": _safe_list(item.get("artifact_interactions")),
                    "timeline_impacts": _safe_list(item.get("timeline_impacts")),
                    "status": str(item.get("status") or "planned").lower(),
                    "order": int(item.get("order") or index),
                    **meta,
                    "cycle_generated": cycle,
                    "updated_at": datetime.utcnow(),
                }
                await db.scene_plans.update_one(
                    {"project_id": pid, "scene_id": scene_id},
                    {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                    upsert=True,
                )
                saved += 1
            counts["scene_plans"] = saved
        if payload.get("themes"):
            theme_payload = _safe_dict(payload["themes"])
            for field in ["themes", "motifs", "symbols", "payoffs", "related_characters", "related_arcs"]:
                theme_payload[field] = _safe_list(theme_payload.get(field))
            themes = {"project_id": pid, **theme_payload, **meta, "cycle_generated": cycle, "updated_at": datetime.utcnow()}
            await db.theme_registry.update_one({"project_id": pid}, {"$set": themes, "$setOnInsert": {"created_at": datetime.utcnow()}}, upsert=True)
            counts["themes"] = 1
        if payload.get("timeline_events"):
            saved = 0
            for index, item in enumerate(_safe_list(payload["timeline_events"]), start=1):
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or item.get("event") or "Unknown future event")
                arc_id = str(item.get("arc_id") or "")
                existing = None
                if item.get("entry_id"):
                    existing = await db.timeline_entries.find_one({
                        "project_id": pid, "entry_id": str(item["entry_id"])
                    })
                if not existing:
                    existing = await db.timeline_entries.find_one({
                        "project_id": pid, "arc_id": arc_id or None, "title": title
                    })
                entry_id = str((existing or {}).get("entry_id") or item.get("entry_id") or uuid4())
                doc = {
                    "project_id": pid,
                    "entry_id": entry_id,
                    "arc_id": arc_id or None,
                    "title": title,
                    "summary": str(item.get("summary") or ""),
                    "importance": str(item.get("importance") or "major"),
                    "status": str(item.get("status") or "planned").lower(),
                    "certainty": str(item.get("certainty") or "unknown").lower(),
                    "dependencies": _safe_list(item.get("dependencies")),
                    "chapter_range": _safe_list(item.get("chapter_range")),
                    "order": int(item.get("order") or cycle * 1000 + index),
                    **meta,
                    "cycle_generated": cycle,
                    "updated_at": datetime.utcnow(),
                }
                query = {"_id": existing["_id"]} if existing else {
                    "project_id": pid, "entry_id": entry_id
                }
                await db.timeline_entries.update_one(
                    query,
                    {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                    upsert=True,
                )
                saved += 1
            counts["timeline"] = saved
        if payload.get("readiness_items"):
            saved = 0
            for item in _safe_list(payload["readiness_items"]):
                if not isinstance(item, dict) or not item.get("title"):
                    continue
                query = {
                    "project_id": pid,
                    "arc_id": str(item.get("arc_id") or "") or None,
                    "category": str(item.get("category") or "Uncategorized"),
                    "title": str(item["title"]),
                }
                existing = await db.story_readiness.find_one(query)
                existing_status = str((existing or {}).get("status") or "")
                status = existing_status if existing_status in {"approved", "ready"} else (
                    str(item.get("status") or "proposed").lower()
                )
                if status not in {"missing", "discussed", "proposed"} and not existing:
                    status = "proposed"
                doc = {
                    **query,
                    "item_id": str((existing or {}).get("item_id") or uuid4()),
                    "description": str(item.get("description") or ""),
                    "priority": str(item.get("priority") or "recommended").lower(),
                    "status": status,
                    "evidence": _safe_list(item.get("evidence")),
                    # AI may suggest a requirement, but only a human-authored
                    # readiness record can become a drafting blocker.
                    "blocking": False,
                    "source": agent_name,
                    "updated_at": datetime.utcnow(),
                }
                await db.story_readiness.update_one(
                    {"_id": existing["_id"]} if existing else query,
                    {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                    upsert=True,
                )
                saved += 1
            counts["readiness"] = saved
        if payload.get("knowledge_entries"):
            saved = 0
            for item in _safe_list(payload["knowledge_entries"]):
                if not isinstance(item, dict) or not item.get("content"):
                    continue
                knowledge_type = str(item.get("knowledge_type") or "WORLD_TRUTH").upper()
                title = str(item.get("title") or str(item["content"])[:100])
                existing = None
                if item.get("entry_id"):
                    existing = await db.knowledge_entries.find_one({
                        "project_id": pid, "entry_id": str(item["entry_id"])
                    })
                if not existing:
                    existing = await db.knowledge_entries.find_one({
                        "project_id": pid,
                        "knowledge_type": knowledge_type,
                        "arc_id": str(item.get("arc_id") or "") or None,
                        "title": title,
                    })
                doc = {
                    "project_id": pid,
                    "entry_id": str((existing or {}).get("entry_id") or item.get("entry_id") or uuid4()),
                    "arc_id": str(item.get("arc_id") or "") or None,
                    "title": title,
                    "content": str(item["content"]),
                    "knowledge_type": knowledge_type,
                    "known_by": _safe_list(item.get("known_by")),
                    "not_known_by": _safe_list(item.get("not_known_by")),
                    "learned_how": str(item.get("learned_how") or ""),
                    "is_false": bool(item.get("is_false", False)),
                    "confidence": max(0.0, min(float(item.get("confidence") or 0), 1.0)),
                    "source": str(item.get("source") or agent_name),
                    "source_id": str(item.get("source_id") or ""),
                    "reveal_target": str(item.get("reveal_target") or ""),
                    "world_truth_entry_id": str(item.get("world_truth_entry_id") or "") or None,
                    **meta,
                    "cycle_generated": cycle,
                    "updated_at": datetime.utcnow(),
                }
                query = {"_id": existing["_id"]} if existing else {
                    "project_id": pid, "entry_id": doc["entry_id"]
                }
                await db.knowledge_entries.update_one(
                    query,
                    {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                    upsert=True,
                )
                saved += 1
            counts["knowledge"] = saved
        if payload.get("questions"):
            before = await db.questions.count_documents({"project_id": pid})
            questions = [
                {**item, "cycle_number": cycle, "agent_name": agent_name}
                for item in _safe_list(payload["questions"]) if isinstance(item, dict)
            ]
            await save_questions(db, project_id, questions, cycle_number=cycle, agent_name=agent_name)
            after = await db.questions.count_documents({"project_id": pid})
            counts["questions"] = max(0, after - before)
        if payload.get("development_proposals"):
            saved = 0
            chapter_plans_saved = 0
            for item in _safe_list(payload["development_proposals"]):
                if not isinstance(item, dict) or not item.get("title"):
                    continue
                arc_id = str(item.get("arc_id") or "")
                arc = await db.story_arcs.find_one(
                    {"project_id": pid, "arc_id": arc_id}
                )
                if not arc:
                    continue
                proposal_type = str(item.get("proposal_type") or "arc_refinement")
                details = _safe_dict(item.get("details"))
                title = str(item.get("title") or "Planning proposal").strip()
                description = str(item.get("description") or "").strip()
                priority = str(item.get("priority") or "recommended").lower()
                if priority not in {"required", "recommended", "optional"}:
                    priority = "recommended"

                # Every proposal becomes a visible, author-reviewable arc item.
                # AI-created items remain proposed and non-blocking until the
                # author changes their status.
                checklist_query = {
                    "project_id": pid,
                    "arc_id": arc_id,
                    "title": title,
                    "source": agent_name,
                }
                existing_checklist = await db.arc_checklists.find_one(checklist_query)
                await db.arc_checklists.update_one(
                    checklist_query,
                    {"$set": {
                        **checklist_query,
                        "item_id": str(
                            (existing_checklist or {}).get("item_id")
                            or item.get("proposal_id")
                            or uuid4()
                        ),
                        "category": proposal_type.replace("_", " ").title(),
                        "description": description,
                        "priority": priority,
                        "status": "proposed",
                        "dimension": str(details.get("dimension") or "resolution_planning"),
                        "weight": 1,
                        "evidence": _safe_list(item.get("affected_ids")),
                        "blocking": False,
                        "rationale": str(item.get("rationale") or ""),
                        **meta,
                        "cycle_generated": cycle,
                        "updated_at": datetime.utcnow(),
                    }, "$setOnInsert": {"created_at": datetime.utcnow()}},
                    upsert=True,
                )
                saved += 1

                if proposal_type == "chapter_plan":
                    existing_chapters = await db.chapter_plans.count_documents(
                        {"project_id": pid, "arc_id": arc_id}
                    )
                    chapter_number = max(
                        1, int(details.get("chapter_number") or existing_chapters + 1)
                    )
                    chapter_query = {
                        "project_id": pid,
                        "arc_id": arc_id,
                        "chapter_number": chapter_number,
                    }
                    existing_chapter = await db.chapter_plans.find_one(chapter_query)
                    await db.chapter_plans.update_one(
                        chapter_query,
                        {"$set": {
                            "project_id": pid,
                            "arc_id": arc_id,
                            "chapter_plan_id": str(
                                (existing_chapter or {}).get("chapter_plan_id")
                                or details.get("chapter_plan_id")
                                or uuid4()
                            ),
                            "chapter_number": chapter_number,
                            "title": title,
                            "purpose": str(details.get("purpose") or description),
                            "conflict": str(details.get("conflict") or ""),
                            "character_focus": _safe_list(details.get("character_focus")),
                            "knowledge_changes": [], "artifact_ids": [],
                            "foreshadow_ids": [], "timeline_entry_ids": [],
                            "status": "planned",
                            "approval_status": "proposed",
                            "source": agent_name,
                            **meta,
                            "cycle_generated": cycle,
                            "updated_at": datetime.utcnow(),
                        }, "$setOnInsert": {"created_at": datetime.utcnow()}},
                        upsert=True,
                    )
                    chapter_plans_saved += 1
            counts["development_proposals"] = saved
            if chapter_plans_saved:
                counts["chapter_plans"] = chapter_plans_saved
        return counts

    async def run(
        self,
        db,
        *,
        project_id: str,
        state: Dict[str, Any],
        run_id: str | None = None,
        agent_names: List[str] | None = None,
        plan_id: str | None = None,
        max_cycle_cost_usd: float | None = None,
        max_agent_calls: int | None = None,
    ) -> Dict[str, Any]:
        project = await db.projects.find_one({"_id": ObjectId(project_id)}) or {}
        cycle = int(state.get("cycle_number") or 1)
        agents_run: List[str] = []
        artifacts: Dict[str, int] = {}
        actual_cost = 0.0
        stop_reason = None

        if agent_names is None:
            raise ValueError("Narrative Studio execution requires an explicit agent plan")
        specs_by_name = {spec["name"]: spec for spec in AGENT_SPECS}
        selected_specs = [
            specs_by_name[name]
            for name in agent_names
            if name in specs_by_name
        ]
        state["run_id"] = run_id or ""
        state["plan_id"] = plan_id or ""
        state.setdefault("cycle_outputs", [])
        state["cycle_handoffs"] = await develop_story_context_service.load_handoffs(
            db,
            project_id,
            run_id or "",
            cycle,
        )
        for agent_index, spec in enumerate(selected_specs):
            agent_name = spec["name"]
            audit_only = agent_name == "StoryAuditorAgent"
            if max_agent_calls is not None and len(agents_run) >= max_agent_calls:
                stop_reason = (
                    f"Stopped at max_agent_calls_per_cycle={max_agent_calls}"
                )
                break
            if (
                max_cycle_cost_usd is not None
                and actual_cost >= max_cycle_cost_usd
            ):
                stop_reason = (
                    f"Stopped at max_cycle_cost_usd=${max_cycle_cost_usd:.6f}"
                )
                break
            task_query = None
            if plan_id and ObjectId.is_valid(plan_id):
                task_query = {
                    "plan_id": ObjectId(plan_id),
                    "agent_name": agent_name,
                }
                await db.orchestration_tasks.update_one(
                    task_query,
                    {
                        "$set": {
                            "status": "running",
                            "started_at": datetime.utcnow(),
                        }
                    },
                )
            if run_id:
                await development_state_service.heartbeat(db, project_id, run_id)
                await db.runs.update_one(
                    {
                        "_id": ObjectId(run_id),
                        "project_id": ObjectId(project_id),
                    },
                    {"$set": {
                        "current_agent": agent_name,
                        "status": "running",
                        "metadata.author_phase": f"Working on {agent_spec_label(agent_name)}",
                        "metadata.progress_completed": len(agents_run),
                        "metadata.progress_total": len(selected_specs),
                        "metadata.current_agent_index": agent_index + 1,
                        "metadata.heartbeat_at": datetime.utcnow(),
                    }},
                )
                await emit_project_event(
                    db, project_id, "agent_started", cycle_number=cycle,
                    payload={
                        "run_id": run_id,
                        "agent_name": agent_name,
                        "label": agent_spec_label(agent_name),
                        "position": agent_index + 1,
                        "total": len(selected_specs),
                    },
                )
            try:
                payload, meta = await self._run_agent(
                    db,
                    agent_spec=spec,
                    project=project,
                    state=state,
                )
            except Exception as exc:
                if task_query:
                    await db.orchestration_tasks.update_one(
                        task_query,
                        {
                            "$set": {
                                "status": "failed",
                                "reason": str(exc),
                                "completed_at": datetime.utcnow(),
                            }
                        },
                    )
                raise
            contradiction_reports = []
            counts: Dict[str, int] = {}
            if not audit_only:
                contradiction_reports = await validate_against_canon(
                    db,
                    project_id=project_id,
                    agent_name=agent_name,
                    cycle_number=cycle,
                    structured_output=payload,
                )
                counts = await self._persist_artifacts(
                    db,
                    project_id=project_id,
                    cycle=cycle,
                    agent_name=agent_name,
                    payload=payload,
                    meta=meta,
                )
            for key, value in counts.items():
                artifacts[key] = artifacts.get(key, 0) + value
            summary = str(payload.get("summary") or "").strip()
            if not summary:
                changed = [
                    f"{value} {key.replace('_', ' ')}"
                    for key, value in counts.items()
                    if int(value or 0) > 0
                ]
                summary = (
                    f"Completed {agent_spec_label(agent_name)}. Updated "
                    + ", ".join(changed)
                    + "."
                    if changed
                    else f"Completed {agent_spec_label(agent_name)}. No current planning records needed to change."
                )
            proposal = {
                "project_id": ObjectId(project_id),
                "author": agent_name,
                "role": "agent",
                "cycle": cycle,
                "cycle_number": cycle,
                "summary": summary,
                "reasoning": str(payload.get("reasoning") or ""),
                "concerns": _safe_list(payload.get("concerns")),
                "recommendation": str(payload.get("recommendation") or ""),
                "references": list(counts.keys()),
                "content": summary,
                "structured_output": payload,
                "artifact_counts": counts,
                "decision_status": "pending",
                "contradiction_status": "open" if contradiction_reports else "clear",
                "timestamp": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                **meta,
            }
            discussion_result = None
            if not audit_only:
                discussion_result = await db.discussion_messages.insert_one(proposal)
            handoff = None
            if develop_story_context_service.supports_agent(agent_name):
                handoff = develop_story_context_service.build_handoff(
                    agent_name=agent_name,
                    cycle_number=cycle,
                    payload=payload,
                    counts=counts,
                    contradiction_reports=contradiction_reports,
                    proposal_id=(str(discussion_result.inserted_id) if discussion_result else ""),
                    run_id=run_id or "",
                )
                if run_id:
                    await develop_story_context_service.persist_handoff(
                        db,
                        project_id,
                        run_id,
                        handoff,
                    )
                state["cycle_handoffs"] = [
                    item
                    for item in state.get("cycle_handoffs") or []
                    if item.get("specialist") != agent_name
                ] + [handoff]
            if run_id:
                await db.agent_outputs.insert_one({
                    "project_id": ObjectId(project_id),
                    "run_id": ObjectId(run_id),
                    "agent_name": agent_name,
                    "agent_slug": agent_name.removesuffix("Agent").lower(),
                    "summary": summary,
                    "structured_output": payload,
                    "content": summary,
                    "metadata": {
                        **meta,
                        "cycle_number": cycle,
                        "duration_ms": meta["latency"],
                        "artifacts_created": counts,
                        "canon_decisions_read": len(state.get("canon_facts") or []),
                        "questions_generated": counts.get("questions", 0),
                        "proposal_id": (
                            str(discussion_result.inserted_id)
                            if discussion_result
                            else ""
                        ),
                        "handoff_available": bool(handoff),
                    },
                    "created_at": datetime.utcnow(),
                })
            agents_run.append(agent_name)
            actual_cost += float(meta.get("cost") or 0)
            state["cycle_outputs"].append(
                {
                    "agent_name": agent_name,
                    "summary": summary,
                    "structured_output": payload,
                    "artifacts_created": counts,
                    "generation_metadata": meta,
                }
            )
            if not audit_only:
                await agent_memory_service.record_result(
                    db,
                    project_id=project_id,
                    agent_name=agent_name,
                    cycle_number=cycle,
                    summary=summary,
                    concerns=_safe_list(payload.get("concerns")),
                )
            if task_query:
                await db.orchestration_tasks.update_one(
                    task_query,
                    {
                        "$set": {
                            "status": "completed",
                            "completed_at": datetime.utcnow(),
                            "provider": meta.get("provider"),
                            "model": meta.get("model"),
                            "tokens_used": int(meta.get("tokens") or 0),
                            "cost_usd": float(meta.get("cost") or 0),
                            "execution_trace_id": meta.get("execution_trace_id"),
                        }
                    },
                )
            # Artifacts saved by this specialist must be available to the next
            # specialist in the same cycle. Refresh the shared projection and
            # retrieval index before continuing.
            if not audit_only:
                await self._refresh_live_story_context(db, project_id, state)
            if run_id:
                await development_state_service.heartbeat(db, project_id, run_id)
                await db.runs.update_one(
                    {"_id": ObjectId(run_id), "project_id": ObjectId(project_id)},
                    {
                        "$addToSet": {"metadata.completed_agents": agent_name},
                        "$set": {
                            "metadata.progress_completed": len(agents_run),
                            "metadata.progress_total": len(selected_specs),
                            "metadata.last_completed_label": agent_spec_label(agent_name),
                            "metadata.heartbeat_at": datetime.utcnow(),
                        },
                    },
                )
            await emit_project_event(
                db, project_id, "agent_completed",
                cycle_number=cycle,
                payload={
                    "agent_name": agent_name,
                    "artifacts": counts,
                    "plan_id": plan_id,
                },
            )

        await db.projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"updated_at": datetime.utcnow()}},
        )
        return {
            "agents_run": agents_run,
            "artifacts": artifacts,
            "story_bible_version": None,
            "actual_cost_usd": round(actual_cost, 6),
            "stop_reason": stop_reason,
        }


narrative_studio_service = NarrativeStudioService()
