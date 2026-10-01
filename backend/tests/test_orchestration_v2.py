import json
import time
from datetime import datetime

import pytest
from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config
from app.services.provider_rate_limiter import ProviderRateLimiter
from app.services.provider_gateway import provider_gateway


def create_project(client, title="The Ashes of Valeria"):
    response = client.post(
        "/api/projects",
        json={
            "title": f"{title} {time.time_ns()}",
            "premise": "A dispossessed heir tends the memories left in sacred ash.",
            "idea_dump": "Mercy and ambition collide after a fallen empire wakes.",
            "genre": "Fantasy",
            "tone": "Mythic",
        },
    )
    assert response.status_code == 200
    return response.json()


def run_cycle(client, project_id):
    response = client.post(f"/api/projects/{project_id}/cycle")
    assert response.status_code == 200
    runs = client.get(f"/api/projects/{project_id}/runs").json()
    assert runs[0]["status"] in {"completed", "waiting_for_user"}
    return client.get(
        f"/api/projects/{project_id}/orchestration/latest"
    ).json()


def test_ashes_of_valeria_demand_driven_simulation(client):
    project = create_project(client)
    project_id = project["id"]

    premise_plan = run_cycle(client, project_id)
    assert 0 < len(premise_plan["selected_agents"]) <= 5
    assert len(premise_plan["tasks"]) == len(premise_plan["selected_agents"]) + len(
        premise_plan["skipped_agents"]
    )

    response = client.put(
        f"/api/projects/{project_id}",
        json={
            "character_notes": (
                "The protagonist Valeria is proud, grief-stricken, and afraid "
                "that mercy will look like weakness."
            )
        },
    )
    assert response.status_code == 200
    character_plan = run_cycle(client, project_id)
    assert "CharacterJourneyAgent" in character_plan["selected_agents"]
    assert "RelationshipAgent" in character_plan["selected_agents"]
    assert "WorldAgent" in character_plan["skipped_agents"]
    assert "PowerSystemAgent" in character_plan["skipped_agents"]
    assert "FactionAgent" in character_plan["skipped_agents"]

    world_notes = (
        "Valeria's world is organized around ash gardens that preserve public "
        "memory, while rival courts control access."
    )
    response = client.put(
        f"/api/projects/{project_id}",
        json={"world_notes": world_notes},
    )
    assert response.status_code == 200
    world_plan = run_cycle(client, project_id)
    assert "WorldAgent" in world_plan["selected_agents"]
    assert "FactionAgent" in world_plan["selected_agents"]
    assert "CharacterJourneyAgent" in world_plan["skipped_agents"]

    response = client.put(
        f"/api/projects/{project_id}",
        json={"world_notes": world_notes},
    )
    assert response.status_code == 200
    no_op_plan = run_cycle(client, project_id)
    assert no_op_plan["selected_agents"] == []
    assert no_op_plan["actual_agent_calls"] == 0
    assert "NO_CHANGE_TERMINATION" in no_op_plan["stop_reason"]

    plans = [premise_plan, character_plan, world_plan, no_op_plan]
    total_calls = sum(plan["actual_agent_calls"] for plan in plans)
    average = total_calls / len(plans)
    skip_percentage = (
        sum(len(plan["skipped_agents"]) for plan in plans)
        / (12 * len(plans))
        * 100
    )
    assert average < 5
    assert total_calls <= 24
    assert skip_percentage >= 50


def test_disabled_agent_is_never_selected(client):
    project_id = create_project(client, "Disabled Agent")["id"]
    run_cycle(client, project_id)
    assignments = client.get("/api/settings/agents").json()
    for assignment in assignments:
        if assignment["agent_name"] == "RelationshipAgent":
            assignment["enabled"] = False
    response = client.put("/api/settings/agents", json=assignments)
    assert response.status_code == 200

    client.put(
        f"/api/projects/{project_id}",
        json={"character_notes": "The protagonist distrusts her closest ally."},
    )
    plan = run_cycle(client, project_id)
    assert "RelationshipAgent" not in plan["selected_agents"]
    task = next(
        item for item in plan["tasks"]
        if item["agent_name"] == "RelationshipAgent"
    )
    assert task["status"] == "skipped"
    assert "disabled" in task["reason"].lower()


def test_story_bible_rebuilds_once_per_agent_cycle(client):
    project_id = create_project(client, "Single Bible Rebuild")["id"]
    client.post(
        f"/api/projects/{project_id}/messages",
        json={"content": "Make the protagonist's flaw more emotionally costly."},
    )
    before = client.get(f"/api/projects/{project_id}/story-bible").json()["version"]
    plan = run_cycle(client, project_id)
    assert len(plan["selected_agents"]) > 1
    after = client.get(f"/api/projects/{project_id}/story-bible").json()["version"]
    assert after == before + 1


def test_same_cycle_relationship_work_sees_new_character_planning(client, monkeypatch):
    captured = {}
    original = provider_gateway.generate_with_failover

    async def capture_context(*args, **kwargs):
        messages = args[1] if len(args) > 1 else []
        prompt = str((messages[-1] if messages else {}).get("content") or "")
        marker = "Project context:\n"
        if marker in prompt:
            captured[kwargs.get("agent_name")] = json.loads(prompt.split(marker, 1)[1])
        return await original(*args, **kwargs)

    monkeypatch.setattr(provider_gateway, "generate_with_failover", capture_context)
    project_id = create_project(client, "Same Cycle Context")["id"]
    response = client.post(f"/api/projects/{project_id}/run")
    assert response.status_code == 200
    relationship_context = captured["RelationshipAgent"]
    characters = relationship_context["role_specific_structured_context"]["characters"]
    assert any(item.get("name") == "Mentor" for item in characters)
    assert "current_story_plan" not in relationship_context


def test_changed_author_decision_supersedes_incompatible_planning(client):
    project_id = create_project(client, "Decision Reconciliation")["id"]
    mongo = MongoClient(app_config.mongodb_url)
    db = mongo[app_config.database_name]
    pid = ObjectId(project_id)
    question_id = db.questions.insert_one({
        "project_id": pid,
        "text": "Who leads the rebellion?",
        "choices": ["Mara", "Ilya"],
        "answered": True,
        "answer": "Mara",
        "blocking": True,
        "cycle_number": 1,
        "created_at": datetime.utcnow(),
    }).inserted_id
    arc_id = db.story_arcs.insert_one({
        "project_id": pid,
        "arc_id": "rebellion-arc",
        "title": "Mara leads the rebellion",
        "goal": "Mara unites the city against the court.",
        "development_status": "planned",
        "focus_role": "current",
    }).inserted_id
    response = client.put(
        f"/api/projects/{project_id}/decisions/{question_id}",
        json={"answer": "Ilya", "reason": "The author changed the protagonist."},
    )
    assert response.status_code == 200, response.text
    stale_arc = db.story_arcs.find_one({"_id": arc_id})
    invalidation = db.planning_invalidations.find_one({"decision_id": question_id})
    active_canon = db.canon_registry.find_one({
        "project_id": pid, "source_id": str(question_id), "active": True,
    })
    mongo.close()
    assert stale_arc["authority_status"] == "stale"
    assert invalidation["status"] == "pending"
    assert "ArcArchitectAgent" in invalidation["required_agents"]
    assert "Ilya" in active_canon["fact"]
    bible = client.get(f"/api/projects/{project_id}/story-bible").json()
    assert all(item.get("arc_id") != "rebellion-arc" for item in bible["sections"]["arcs"])


def test_first_non_default_answer_supersedes_planning_built_from_optional_default(client):
    project_id = create_project(client, "Optional Default Reconciliation")["id"]
    mongo = MongoClient(app_config.mongodb_url)
    db = mongo[app_config.database_name]
    pid = ObjectId(project_id)
    default = "Mira is guarded and cautious around everyone; the brother remains reckless, which creates protective tension."
    question_id = db.questions.insert_one({
        "project_id": pid,
        "text": "How do the siblings relate?",
        "choices": [default, "They are open and deeply collaborative."],
        "answered": False,
        "default_recommendation": default,
        "blocking": False,
        "cycle_number": 1,
        "created_at": datetime.utcnow(),
    }).inserted_id
    character_id = db.character_bibles.insert_one({
        "project_id": pid,
        "name": "Mira",
        "description": "Mira is guarded and cautious around everyone.",
        "agent_notes": "The brother remains reckless, which creates protective tension.",
        "cycle_generated": 1,
    }).inserted_id

    response = client.post(
        f"/api/projects/{project_id}/answers",
        json={"question_id": str(question_id), "answer": "They are open and deeply collaborative."},
    )
    assert response.status_code == 200, response.text
    stale_character = db.character_bibles.find_one({"_id": character_id})
    invalidation = db.planning_invalidations.find_one({"decision_id": question_id})
    mongo.close()
    assert stale_character["authority_status"] == "stale"
    assert invalidation["status"] == "pending"
    assert "CharacterJourneyAgent" in invalidation["required_agents"]


def test_beginner_and_workspace_changes_reenter_orchestration(client):
    project_id = create_project(client, "Guided Change Propagation")["id"]
    run_cycle(client, project_id)

    response = client.put(
        f"/api/projects/{project_id}/beginner-flow/main_character",
        json={
            "action": "save",
            "title": "Mara Vale",
            "details": "A patient archivist who fears becoming the story's villain.",
            "source_mode": "manual",
        },
    )
    assert response.status_code == 200
    character_plan = run_cycle(client, project_id)
    assert "CharacterJourneyAgent" in character_plan["selected_agents"]
    assert "RelationshipAgent" in character_plan["selected_agents"]

    response = client.post(
        f"/api/projects/{project_id}/workspace-entries",
        json={
            "area": "theme",
            "title": "Memory has a cost",
            "details": "Every preserved truth requires someone to surrender a comforting lie.",
            "source_mode": "manual",
        },
    )
    assert response.status_code == 200
    theme_plan = run_cycle(client, project_id)
    assert "ThemeAgent" in theme_plan["selected_agents"]
    assert "ArcArchitectAgent" in theme_plan["selected_agents"]


def test_child_resources_are_project_owned(client):
    first = create_project(client, "Ownership One")
    second = create_project(client, "Ownership Two")
    first_plan = run_cycle(client, first["id"])
    runs = client.get(f"/api/projects/{first['id']}/runs").json()
    run_id = runs[0]["id"]

    assert client.get(
        f"/api/projects/{second['id']}/runs/{run_id}"
    ).status_code == 404
    assert client.get(
        f"/api/projects/{second['id']}/outputs",
        params={"run_id": run_id},
    ).status_code == 404

    questions = client.get(f"/api/projects/{first['id']}/questions").json()
    assert questions
    assert client.post(
        f"/api/projects/{second['id']}/answers",
        json={"question_id": questions[0]["id"], "answer": "A forbidden memory"},
    ).status_code == 404
    assert first_plan["project_id"] == first["id"]


def test_memory_versions_are_active_and_bounded(client):
    project_id = create_project(client, "Memory Versions")["id"]
    run_cycle(client, project_id)
    for index in range(4):
        client.put(
            f"/api/projects/{project_id}",
            json={"notes": f"Project memory revision {index}"},
        )
        run_cycle(client, project_id)

    mongo = MongoClient(app_config.mongodb_url)
    docs = list(
        mongo[app_config.database_name].memory_embeddings.find(
            {
                "project_id": ObjectId(project_id),
                "source_type": "project",
                "source_id": project_id,
            }
        )
    )
    mongo.close()
    assert len(docs) <= 2
    assert sum(1 for document in docs if document.get("active")) == 1
    assert all(int(document.get("source_version") or 0) > 0 for document in docs)


def test_phase_1a_indexes_are_installed(client):
    mongo = MongoClient(app_config.mongodb_url)
    db = mongo[app_config.database_name]
    required = {
        "runs": {"runs_project_started_at", "runs_project_status"},
        "cycles": {"cycles_project_cycle"},
        "agent_outputs": {
            "agent_outputs_project_created_at",
            "agent_outputs_run_created_at",
        },
        "questions": {"questions_project_answered_created_at"},
        "timeline_messages": {"timeline_messages_project_created_at"},
        "discussion_messages": {
            "discussion_messages_project_cycle_created_at"
        },
        "story_bibles": {"story_bibles_project"},
        "memory_embeddings": {
            "memory_source_version",
            "memory_project_active_source",
        },
        "project_events": {"project_events_project_id"},
        "execution_traces": {
            "execution_traces_project_created_at",
            "execution_traces_run",
        },
        "orchestration_plans": {
            "orchestration_plans_project_created_at",
            "orchestration_plans_run",
        },
        "orchestration_tasks": {
            "orchestration_tasks_plan_agent",
            "orchestration_tasks_plan_status",
        },
    }
    for collection, expected in required.items():
        names = {index["name"] for index in db[collection].list_indexes()}
        assert expected <= names
    mongo.close()


@pytest.mark.asyncio
async def test_provider_rate_limiter_never_exceeds_window():
    now = [0.0]
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    limiter = ProviderRateLimiter(
        clock=lambda: now[0],
        sleep=fake_sleep,
        window_seconds=60,
    )
    waits = [await limiter.acquire("gemini", 5) for _ in range(5)]
    sixth = await limiter.acquire("gemini", 5)
    assert waits == [0, 0, 0, 0, 0]
    assert sixth == 60100
    assert sleeps == [60.1]
    assert limiter.normalize_limit(1) == 5
    assert limiter.normalize_limit(99) == 10


@pytest.mark.asyncio
async def test_provider_rate_limiter_only_throttles_google_ai_studio():
    now = [0.0]
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    limiter = ProviderRateLimiter(
        clock=lambda: now[0],
        sleep=fake_sleep,
        window_seconds=60,
    )
    waits = [await limiter.acquire("openrouter", 5) for _ in range(20)]
    assert waits == [0] * 20
    assert sleeps == []
    assert limiter.is_app_limited("gemini") is True
    assert limiter.is_app_limited("openrouter") is False
