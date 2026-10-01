import sys
import os
import json
import random
import string

# Add the backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Override database name for test isolation BEFORE main/app is imported
from app.core.config import settings as app_config
worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
app_config.database_name = f"novelforge_test_{worker_id}_{random_suffix}"

import pytest
from pymongo import MongoClient
from fastapi.testclient import TestClient
from main import app
from bson import ObjectId
from app.services.narrative_studio import STUDIO_AGENT_NAMES
from app.services.provider_gateway import provider_gateway



@pytest.fixture(scope="session", autouse=True)
def test_db_session_isolation():
    """Drop the temporary worker test database at the end of the test session."""
    yield
    mongo = MongoClient(app_config.mongodb_url)
    mongo.drop_database(app_config.database_name)
    mongo.close()
    print(f"\nDropped test database: {app_config.database_name}")


@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI app with startup/shutdown handling."""
    app_config.use_mock_llm = True
    with TestClient(app) as test_client:
        yield test_client


def studio_fixture(agent_name):
    common = {
        "summary": f"{agent_name} completed structured planning.",
        "reasoning": "The proposal follows the persisted project premise and canon.",
        "concerns": [],
        "recommendation": "Continue developing this area in the next cycle.",
    }
    payloads = {
        "NarrativeDirectorAgent": {
            "story_vision": {
                "premise": "A prince hears dead gods.",
                "genre": "Fantasy",
                "themes": ["Mercy"],
                "target_length": "Long form",
                "inspirations": [],
                "audience": "Adult fantasy",
                "narrative_goals": ["Test mercy under pressure"],
            },
            "ai_insights": {
                "contradictions": [],
                "missing_information": ["The gods' motive"],
                "weak_characters": [],
                "weak_pacing": [],
                "dead_plot_threads": [],
                "suggested_improvements": ["Clarify the mentor's cost"],
                "consistency_score": 82,
                "worldbuilding_score": 76,
                "character_score": 80,
                "power_system_score": 65,
            },
        },
        "StoryArchitectAgent": {
            "plot_threads": [{
                "title": "The Mentor's Hidden Cost",
                "description": "The mentor protects the prince at a private cost.",
                "status": "open",
                "related_characters": ["Mentor", "Prince"],
                "possible_resolutions": ["The prince discovers the sacrifice"],
            }],
        },
        "CharacterJourneyAgent": {
            "characters": [{
                "name": "Mentor",
                "role": "mentor",
                "age": "52",
                "description": "A principled guide carrying a tragic obligation.",
                "personality": ["compassionate", "guarded"],
                "goals": ["Protect the prince"],
                "fears": ["Repeating an old failure"],
                "secrets": ["The dead gods know his name"],
                "relationships": [],
                "power": "Listens to divine echoes",
                "arc": "Learns to share the burden",
                "current_status": "active",
                "future_payoffs": ["Confesses the true cost"],
                "timeline": ["Guides the prince"],
                "agent_notes": "Test fixture",
                "beliefs": ["Mercy requires accountability"],
                "growth": "From secrecy to trust",
                "future_plans": ["Prepare the prince for the truth"],
            }],
        },
        "WorldAgent": {
            "world": {
                "world_rules": ["Dead gods can be heard but cannot act directly"],
                "locations": [{"name": "The Listening Court"}],
                "races": [],
                "history": [{"event": "The gods died"}],
                "religion": [{"name": "The Quiet Faith"}],
                "politics": [{"system": "Contested monarchy"}],
                "technology": [],
                "economy": [],
                "academies": [],
                "current_conflicts": ["The court disputes the voices"],
            },
        },
        "PowerSystemAgent": {
            "power_system": {
                "ranks": ["Listener"],
                "levels": ["Echo"],
                "cultivation": "Attunement through costly acts of mercy",
                "skills": ["Hear divine echoes"],
                "classes": ["Listener"],
                "evolution_paths": ["Witness"],
                "concept_tree": [],
                "limitations": ["Voices cannot compel action"],
                "resources": ["Relics"],
                "costs": ["Lost memories"],
                "compatibility_rules": ["Only one divine echo at a time"],
                "progression_logic": "Insight follows sacrifice",
                "progression_curve": "Slow and consequence-driven",
            },
        },
        "FactionAgent": {
            "factions": [{
                "name": "The Quiet Council",
                "leader": "Chancellor Vale",
                "goals": ["Control divine testimony"],
                "enemies": [],
                "allies": [],
                "influence": "Royal court",
                "secrets": ["They suppress one god's voice"],
                "territory": "The capital",
            }],
        },
        "RelationshipAgent": {
            "relationships": [{
                "character_a": "Mentor",
                "character_b": "Prince",
                "type": "mentor",
                "strength": 8,
                "trust": 6,
                "history": "The mentor raised the prince after the first voice.",
                "future_payoff": "The prince chooses whether to forgive the secrecy.",
                "status": "strained",
            }],
        },
        "ThemeAgent": {
            "themes": {
                "themes": ["Mercy without Naivete"],
                "motifs": ["Unanswered bells"],
                "symbols": ["A cracked crown"],
                "payoffs": ["Mercy becomes an informed choice"],
                "related_characters": ["Mentor", "Prince"],
                "related_arcs": ["The First Voice"],
            },
        },
        "MysteryAgent": {
            "mysteries": [{
                "question": "Why can the prince hear dead gods?",
                "truth": "His lineage preserves their final witness.",
                "known_clues": ["Only he hears the bells"],
                "hidden_clues": ["The mentor recognizes the cadence"],
                "red_herrings": [],
                "reveal_target": "The First Voice",
                "status": "open",
            }],
        },
        "ArcArchitectAgent": {
            "arcs": [{
                "title": "The First Voice",
                "goal": "Establish the divine mystery and the prince's choice.",
                "estimated_chapters": 24,
                "major_events": ["The prince hears a warning"],
                "conflicts": ["The court denies the warning"],
                "payoffs": ["The mentor admits partial knowledge"],
                "mysteries": ["Why the prince hears the gods"],
                "character_growth": ["The prince questions inherited authority"],
                "dependencies": [],
                "completion_status": "planned",
            }],
            "timeline_events": [{
                "date": "Year 1",
                "age": "18",
                "event": "The prince hears the first dead god.",
                "participants": ["Prince", "Mentor"],
                "consequences": ["The court divides"],
                "dependencies": [],
                "event_type": "discovery",
            }],
        },
        "PacingAgent": {
            "pacing_analysis": {
                "weak_pacing": ["The middle escalation needs a sharper reversal"],
                "dead_zones": [],
                "escalation_risks": ["Court debate may repeat the same pressure"],
                "recommendations": ["Tie each debate to a new divine consequence"],
                "pacing_score": 74,
            },
        },
        "QuestionAgent": {
            "questions": [{
                "text": "What does the first dead god want the prince to protect?",
                "choices": ["A person", "A city", "A forbidden memory"],
                "default_recommendation": "A forbidden memory",
                "story_area": "mystery",
            }],
        },
        "ScenePlannerAgent": {
            "scene_plans": [{
                "title": "The First Bell",
                "arc_id": "arc-fixture",
                "chapter_plan_id": "chapter-fixture",
                "purpose": "Inciting discovery",
                "conflict": "The court denies the voice.",
                "outcome": "The prince chooses to investigate.",
                "character_focus": ["Prince", "Mentor"],
                "character_change": "certainty to dread",
                "knowledge_changes": [],
                "foreshadow_links": [],
                "artifact_interactions": [],
                "timeline_impacts": [],
                "order": 1,
                "status": "planned",
            }],
        },
        "StoryDevelopmentAgent": {
            "development_proposals": [{
                "arc_id": "arc-fixture",
                "proposal_type": "checklist",
                "title": "Clarify the midpoint reversal",
                "description": "Connect the reversal to the prince's belief change.",
                "rationale": "The selected arc needs visible development.",
                "affected_ids": [],
                "priority": "recommended",
            }],
            "open_questions": ["What belief changes at the midpoint?"],
        },
        "SceneWriterAgent": {},
        "ChapterAssemblerAgent": {},
        "EditorAgent": {},
        "DialogueAgent": {},
        "RevisionAgent": {},
        "ManuscriptAgent": {},
        "CanonAgent": {},
        "StoryAuditorAgent": {},
    }
    return {**common, **payloads.get(agent_name, {})}


@pytest.fixture(autouse=True)
def isolate_ai_execution_settings(client, monkeypatch):
    """Keep persisted local AI settings from leaking into deterministic tests."""
    mongo = MongoClient(app_config.mongodb_url)
    collection = mongo[app_config.database_name].app_settings
    original_settings = collection.find_one({"_id": "global_settings"})
    client.put(
        "/api/settings/execution",
        json={
            "execution_mode": "mock",
            "default_provider": "mock",
            "default_model": "mock-narrative-intelligence",
            "max_cycle_cost_usd": 10.0,
            "max_agent_calls_per_cycle": 10,
        },
    )
    original = provider_gateway.generate_with_failover

    async def deterministic_studio_provider(*args, **kwargs):
        agent_name = kwargs.get("agent_name")
        if agent_name in STUDIO_AGENT_NAMES:
            parsed = studio_fixture(agent_name)
            messages = args[1] if len(args) > 1 else []
            prompt = str((messages[-1] if messages else {}).get("content") or "")
            context = {}
            marker = "Project context:\n"
            if marker in prompt:
                try:
                    context = json.loads(prompt.split(marker, 1)[1])
                except json.JSONDecodeError:
                    context = {}
            drafting = context.get("drafting_context") or {}
            editorial = context.get("editorial_context") or {}
            if agent_name == "SceneWriterAgent":
                scene = drafting.get("scene_plan") or {}
                parsed = {
                    **studio_fixture(agent_name),
                    "scene_draft": {
                        "scene_id": scene.get("scene_id"),
                        "generated_text": (
                            f"{scene.get('title', 'The scene')} unfolds according to "
                            f"the approved purpose: {scene.get('purpose', '')}"
                        ),
                        "paragraphs": [
                            {
                                "paragraph_id": "p1",
                                "order": 1,
                                "pov": (scene.get("character_focus") or ["Ilyra"])[0],
                                "location": "The Gate",
                                "purpose": "Establish character presence",
                                "narrative_goal": "Show Ilyra standing guard",
                                "scene_goal": "Align with the ash gate opening",
                                "emotion": "Pensive",
                                "tension_level": "3",
                                "dialogue_goal": "Introduce dialogue context",
                                "exposition_goal": "Establish exposition details",
                                "target_word_count": 150,
                                "required_canon": scene.get("knowledge_changes") or [],
                                "participating_characters": scene.get("character_focus") or [],
                                "foreshadowing": scene.get("foreshadow_links") or [],
                                "callbacks": [],
                                "required_events": [],
                                "transition_from_previous": "",
                                "transition_to_next": "Transition to next segment"
                            }
                        ],
                        "continuity_claims": {
                            "knowledge_entry_ids": scene.get("knowledge_changes") or [],
                            "artifact_ids": scene.get("artifact_interactions") or [],
                            "timeline_entry_ids": scene.get("timeline_impacts") or [],
                            "foreshadow_ids": scene.get("foreshadow_links") or [],
                            "characters": scene.get("character_focus") or [],
                            "power_changes": [],
                            "dependency_ids": [],
                        },
                        "generation_notes": ["Generated from the approved scene plan."],
                    },
                }
            elif agent_name == "ChapterAssemblerAgent":
                drafts = drafting.get("approved_scene_drafts") or []
                transitions = []
                for left, right in zip(drafts, drafts[1:]):
                    transitions.append({
                        "from_scene_draft_id": left.get("draft_id"),
                        "to_scene_draft_id": right.get("draft_id"),
                        "generated_text": "The consequence carries into the next planned scene.",
                    })
                parsed = {
                    **studio_fixture(agent_name),
                    "chapter_assembly": {
                        "chapter_plan_id": (
                            drafting.get("chapter_plan") or {}
                        ).get("chapter_plan_id"),
                        "transitions": transitions,
                        "generation_notes": ["Approved scene order preserved."],
                    },
                }
            elif agent_name == "EditorAgent":
                subject_type = editorial.get("subject_type") or "scene"
                parsed = {
                    **studio_fixture(agent_name),
                    "editorial_review": {
                        "subject_type": subject_type,
                        "subject_id": editorial.get("subject_id"),
                        "dimension_scores": {
                            "style": 82,
                            "voice_consistency": 84,
                            "pacing": 78,
                            "objective_fulfillment": 88,
                            "emotional_progression": 80,
                            "progression_quality": 81,
                            "consistency": 86,
                            "payoff_readiness": 79,
                        },
                        "findings": {
                            "style": [{
                                "severity": "warning",
                                "message": "One image repeats too quickly.",
                                "evidence": ["Repeated ember image"],
                            }],
                            "voice": [],
                            "pacing": [],
                            "emotional_progression": [],
                            "objective_fulfillment": [],
                        },
                        "blockers": [],
                        "recommendations": ["Vary the repeated image."],
                        "evidence": ["Approved source reviewed without mutation."],
                    },
                }
            elif agent_name == "DialogueAgent":
                parsed = {
                    **studio_fixture(agent_name),
                    "dialogue_review": {
                        "subject_type": editorial.get("subject_type") or "scene",
                        "subject_id": editorial.get("subject_id"),
                        "dimension_scores": {
                            "dialogue": 76,
                            "realism": 78,
                            "distinctiveness": 74,
                            "exposition_control": 72,
                            "speaker_differentiation": 80,
                            "conversation_flow": 77,
                        },
                        "findings": {
                            "dialogue": [{
                                "severity": "warning",
                                "message": "One reply carries too much exposition.",
                                "evidence": ["Second exchange"],
                            }],
                        },
                        "blockers": [],
                        "recommendations": ["Break the exposition across reactions."],
                        "evidence": ["Dialogue passages reviewed."],
                    },
                }
            elif agent_name == "RevisionAgent":
                source = str(editorial.get("approved_source_text") or "")
                parsed = {
                    **studio_fixture(agent_name),
                    "revision_proposal": {
                        "branch_id": editorial.get("branch_id"),
                        "generated_text": (
                            source
                            + "\n\nThe final exchange tightens around the approved conflict."
                        ),
                        "summary": "Tightened the exchange without changing planned events.",
                        "applied_recommendations": [
                            "Break the exposition across reactions."
                        ],
                    },
                }
            elif agent_name == "ManuscriptAgent":
                manuscript = context.get("manuscript_context") or {}
                parsed = {
                    **studio_fixture(agent_name),
                    "manuscript_review": {
                        "result": "PASS",
                        "findings": [{
                            "category": "structure",
                            "severity": "info",
                            "message": "Approved chapter order is coherent.",
                        }],
                        "recommendations": [
                            "Keep the approved chapter lineage attached."
                        ],
                        "evidence": [
                            f"Reviewed {len(manuscript.get('approved_chapters') or [])} chapters."
                        ],
                    },
                }
            elif agent_name == "CanonAgent":
                canon = context.get("canon_governance_context") or {}
                parsed = {
                    **studio_fixture(agent_name),
                    "canon_review": {
                        "result": (canon.get("validation") or {}).get(
                            "result", "PASS"
                        ),
                        "findings": [],
                        "recommendations": [
                            "Resolve deterministic conflicts before approval."
                        ],
                        "evidence": ["Active canon and conflicts reviewed."],
                    },
                }
            elif agent_name == "StoryAuditorAgent":
                audit = context.get("story_audit_context") or {}
                parsed = {
                    **studio_fixture(agent_name),
                    "story_audit": {
                        "result": "WARNING",
                        "findings": [{
                            "category": "agent_observation",
                            "severity": "warning",
                            "subject_type": "project",
                            "subject_id": "",
                            "message": (
                                "Audit agent reviewed bounded chapter intelligence "
                                "and deterministic findings without rewriting content."
                            ),
                            "evidence": [
                                f"deterministic_findings={len(audit.get('deterministic_findings') or [])}"
                            ],
                        }],
                    },
                }
            return {
                "content": str(parsed),
                "parsed": parsed,
                "provider": "mock",
                "model": "test-studio-fixture",
                "tokens_used": 120,
                "latency_ms": 1,
                "fallback_used": False,
            }
        return await original(*args, **kwargs)

    monkeypatch.setattr(
        provider_gateway,
        "generate_with_failover",
        deterministic_studio_provider,
    )
    yield
    if original_settings:
        collection.replace_one({"_id": "global_settings"}, original_settings, upsert=True)
    else:
        collection.delete_one({"_id": "global_settings"})
    mongo.close()


@pytest.fixture
def sample_project():
    """Sample project data for testing."""
    return {
        "title": "Test Project",
        "premise": "A test premise for the story",
        "genre": "Fantasy",
        "tone": "Dark"
    }


@pytest.fixture
def sample_project_id():
    """Generate a sample project ID."""
    return str(ObjectId())
