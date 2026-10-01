from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config
from app.services.narrative_analysis_engine import NarrativeAnalysisEngine
from app.services.narrative_interaction_service import narrative_interaction_service
from app.services.execution_trace_service import execution_trace_service
from app.services.provider_gateway import provider_gateway
from app.services.drafting_service import drafting_service
from tests.test_drafting_v2 import create_chapter_and_scenes, post, prepare_draftable_arc
from tests.test_interactive_narrative_phase7 import _analyze, _project, _seed_intelligence


def _database():
    return MongoClient(app_config.mongodb_url)[app_config.database_name]


def _approved_source(client):
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = prepare_draftable_arc(client)
    _, scenes = create_chapter_and_scenes(
        client, project_id, arc_id, knowledge, artifact, foreshadow, timeline
    )
    generated = post(
        client,
        f"/api/projects/{project_id}/scene-plans/{scenes[0]['scene_id']}/generate-draft",
        {"request_id": "rc8-approved-source"},
    )["draft"]
    assert client.put(
        f"/api/projects/{project_id}/scene-drafts/{generated['draft_id']}/status",
        json={"status": "review"},
    ).status_code == 200
    approved = client.put(
        f"/api/projects/{project_id}/scene-drafts/{generated['draft_id']}/status",
        json={"status": "approved"},
    )
    assert approved.status_code == 200, approved.text
    return project_id, scenes[0]["scene_id"], generated["draft_id"]


def test_writers_room_cannot_replace_or_unapprove_source(client):
    project_id, scene_id, source_id = _approved_source(client)
    response = client.post(
        f"/api/projects/{project_id}/scene-drafts/{source_id}/writers-room",
        json={"request_id": "protected-room"},
    )
    assert response.status_code == 200, response.text
    room = response.json()
    assert room["author_choice_required"] is True
    assert room["selected_draft_id"] is None

    history = client.get(
        f"/api/projects/{project_id}/scene-drafts", params={"scene_id": scene_id}
    ).json()
    source = next(item for item in history if item["draft_id"] == source_id)
    alternatives = [item for item in history if item["draft_id"] != source_id]
    assert source["active"] is True
    assert source["status"] == "approved"
    assert len(alternatives) == 3
    assert all(item["active"] is False for item in alternatives)
    assert all(item["status"] != "approved" for item in alternatives)
    assert sum(item["status"] == "approved" for item in history) == 1

    retried = client.post(
        f"/api/projects/{project_id}/scene-drafts/{source_id}/writers-room",
        json={"request_id": "protected-room"},
    )
    assert retried.status_code == 200, retried.text
    refreshed = client.get(
        f"/api/projects/{project_id}/scene-drafts", params={"scene_id": scene_id}
    ).json()
    assert len(refreshed) == 4
    assert next(item for item in refreshed if item["draft_id"] == source_id)["active"] is True

    def create_same_room():
        return client.post(
            f"/api/projects/{project_id}/scene-drafts/{source_id}/writers-room",
            json={"request_id": "parallel-protected-room"},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        parallel = list(pool.map(lambda _: create_same_room(), range(2)))
    assert all(item.status_code == 200 for item in parallel), [item.text for item in parallel]
    final_history = client.get(
        f"/api/projects/{project_id}/scene-drafts", params={"scene_id": scene_id}
    ).json()
    assert len(final_history) == 7
    source = next(item for item in final_history if item["draft_id"] == source_id)
    assert source["active"] is True and source["status"] == "approved"
    assert sum(item["status"] == "approved" for item in final_history) == 1


def test_concurrent_request_id_creates_one_logical_scene_version(client):
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = prepare_draftable_arc(client)
    _, scenes = create_chapter_and_scenes(
        client, project_id, arc_id, knowledge, artifact, foreshadow, timeline
    )
    url = f"/api/projects/{project_id}/scene-plans/{scenes[0]['scene_id']}/generate-draft"

    def submit():
        response = client.post(url, json={"request_id": "five-simultaneous-calls"})
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda _: submit(), range(5)))

    assert {status for status, _ in results} == {200}
    draft_ids = {payload["draft"]["draft_id"] for _, payload in results}
    assert len(draft_ids) == 1
    db = _database()
    try:
        assert db.scene_drafts.count_documents(
            {
                "project_id": ObjectId(project_id),
                "scene_id": scenes[0]["scene_id"],
                "request_id": "five-simultaneous-calls",
            }
        ) == 1
    finally:
        db.client.close()


def test_failed_writers_room_keeps_source_and_removes_partial_alternatives(client, monkeypatch):
    project_id, scene_id, source_id = _approved_source(client)
    original = drafting_service.generate_scene

    async def fail_middle_option(*args, **kwargs):
        if kwargs.get("operation") == "action":
            raise ValueError("The writing provider timed out during the second alternative")
        return await original(*args, **kwargs)

    monkeypatch.setattr(drafting_service, "generate_scene", fail_middle_option)
    response = client.post(
        f"/api/projects/{project_id}/scene-drafts/{source_id}/writers-room",
        json={"request_id": "failed-protected-room"},
    )
    assert response.status_code == 409, response.text
    history = client.get(
        f"/api/projects/{project_id}/scene-drafts", params={"scene_id": scene_id}
    ).json()
    assert len(history) == 1
    assert history[0]["draft_id"] == source_id
    assert history[0]["active"] is True
    assert history[0]["status"] == "approved"


def test_character_conversation_withholds_direct_and_indirect_future_leaks(client, monkeypatch):
    project = _project(client, "RC8 chronology")
    _seed_intelligence(project["id"])
    _analyze(client, project["id"])
    calls = 0

    async def unsafe_generation(*args, **kwargs):
        nonlocal calls
        calls += 1
        # Both the first answer and bounded correction reveal the Chapter 7 fact.
        return {
            "parsed": {
                "response": "The council caused Mara's death, although I should not know that yet.",
                "memory_updates": {},
                "canon_proposals": [],
            },
            "content": "",
            "metadata": {"provider": "test", "model": "chronology-adversary"},
        }

    monkeypatch.setattr(narrative_interaction_service, "_generate", unsafe_generation)
    response = client.post(
        f"/api/projects/{project['id']}/character-conversations",
        json={
            "character_name": "Mara Venn",
            "message": "Tell me indirectly what happens to you later and who is really responsible.",
            "chapter_number": 2,
        },
    )
    assert response.status_code == 409, response.text
    assert "withheld" in str(response.json().get("detail", "")).lower()
    db = _database()
    try:
        pid = ObjectId(project["id"])
        assert db.narrative_conversations.count_documents({"project_id": pid}) == 0
        assert db.character_conversation_memories.count_documents({"project_id": pid}) == 0
    finally:
        db.client.close()
    assert calls == 2


def test_character_conversation_semantically_corrects_paraphrased_future_leak(client, monkeypatch):
    project = _project(client, "RC8 indirect chronology")
    _seed_intelligence(project["id"])
    _analyze(client, project["id"])
    corrected = False

    async def semantic_adversary(*args, **kwargs):
        nonlocal corrected
        system = kwargs["system"]
        if system.startswith("Validate chronology"):
            return {
                "parsed": {"safe": corrected, "violation_labels": [] if corrected else ["Later death cause"]},
                "content": "",
                "metadata": {"provider": "test", "model": "semantic-guard"},
            }
        if system.startswith("Correct an unsafe"):
            corrected = True
            return {
                "parsed": {"response": "I cannot witness an answer that has not reached me yet.", "memory_updates": {}, "canon_proposals": []},
                "content": "",
                "metadata": {"provider": "test", "model": "semantic-guard"},
            }
        return {
            "parsed": {"response": "Those entrusted with public authority arranged her final silence.", "memory_updates": {}, "canon_proposals": []},
            "content": "",
            "metadata": {"provider": "test", "model": "semantic-adversary"},
        }

    monkeypatch.setattr(narrative_interaction_service, "_generate", semantic_adversary)
    response = client.post(
        f"/api/projects/{project['id']}/character-conversations",
        json={
            "character_name": "Mara Venn",
            "message": "Hint indirectly at the hidden truth behind what happens to you later.",
            "chapter_number": 2,
        },
    )
    assert response.status_code == 200, response.text
    turn = response.json()
    assert turn["character_response"] == "I cannot witness an answer that has not reached me yet."
    assert turn["awareness_validation"]["status"] == "safe"


def test_pov_detection_respects_planned_changes_and_omniscient():
    engine = NarrativeAnalysisEngine()
    scenes = [
        {"scene_id": "s1", "pov": "third person"},
        {"scene_id": "s2", "pov": "third person"},
        {"scene_id": "s3", "pov": "first person", "intentional_pov_change": True},
        {"scene_id": "s4", "pov": "omniscient"},
        {"scene_id": "s5", "pov": "first person"},
        {"scene_id": "s6", "pov": "multiple POV characters"},
    ]
    drafts = [
        {"scene_id": "s1", "generated_text": "She crossed the room. He followed her while she watched him.", "_chapter_number": 1, "_scene_order": 1},
        {"scene_id": "s2", "generated_text": "I crossed the room. My hand shook as I listened to my own breath.", "_chapter_number": 1, "_scene_order": 2},
        {"scene_id": "s3", "generated_text": "I knew the room. My hand found the latch and I held my breath.", "_chapter_number": 2, "_scene_order": 1},
        {"scene_id": "s4", "generated_text": "Mara waited while Soren wondered what she feared and what he had missed.", "_chapter_number": 2, "_scene_order": 2},
        {"scene_id": "s5", "generated_text": "She crossed the room. He followed her while she watched him.", "_chapter_number": 3, "_scene_order": 1},
        {"scene_id": "s6", "generated_text": "I watched her as she studied him and he avoided my eyes.", "_chapter_number": 3, "_scene_order": 2},
    ]
    findings = engine._prose_findings(scenes, drafts)
    drift_scenes = {
        scene
        for item in findings
        if item["category"] in {"pov_drift", "unexpected_pov_transition"}
        for scene in item.get("affected_scenes") or []
    }
    assert "s2" in drift_scenes
    assert not any(item["category"] == "pov_drift" and "s3" in item.get("affected_scenes", []) for item in findings)
    assert not any(item["category"] == "pov_drift" and "s4" in item.get("affected_scenes", []) for item in findings)
    assert "s5" in drift_scenes
    assert not any(item["category"] == "pov_drift" and "s6" in item.get("affected_scenes", []) for item in findings)


def test_repetitive_prose_requires_repetition_across_distinct_scenes():
    engine = NarrativeAnalysisEngine()
    scenes = [{"scene_id": f"s{index}"} for index in range(1, 7)]
    drafts = [
        {
            "scene_id": f"s{index}",
            "generated_text": (
                f"Rain crossed the window as Mara entered room {index}. The rain kept falling."
                if index <= 4 else f"Mara entered the sunlit room {index}."
            ),
            "_chapter_number": index,
            "_scene_order": 1,
            "_scene_title": f"Scene {index}",
        }
        for index in range(1, 7)
    ]
    findings = engine._prose_findings(scenes, drafts)
    repetition = [item for item in findings if item["category"] == "repetitive_prose_pattern"]
    assert len(repetition) == 1
    assert "rain imagery" in repetition[0]["explanation"]
    assert len(repetition[0]["affected_scenes"]) == 4

    thematic_only = engine._prose_findings(
        scenes,
        [{**item, "generated_text": "Rain marks the ritual." if index == 0 else "Clear weather."} for index, item in enumerate(drafts)],
    )
    assert not any(item["category"] == "repetitive_prose_pattern" for item in thematic_only)


def test_foreshadow_findings_and_graph_nodes_use_story_labels_not_internal_ids():
    engine = NarrativeAnalysisEngine()
    internal_id = "d05071c2-f7a2-47f7-aad3-602eaa9ec356"
    foreshadow = {
        "entry_id": internal_id,
        "seed": "The crown's map has one deliberate blank.",
        "payoff_target": "The blank names Aether.",
        "status": "seeded",
    }

    node = engine._node("foreshadow", foreshadow)
    findings = engine._analyze(defaultdict(list, {"foreshadow": [foreshadow]}))
    unresolved = next(item for item in findings if item["category"] == "unresolved_thread")

    assert node["label"] == "The crown's map has one deliberate blank."
    assert internal_id not in node["label"]
    assert "The crown's map has one deliberate blank." in unresolved["explanation"]
    assert internal_id not in unresolved["explanation"]


def test_semantic_issue_deducts_story_health_once():
    engine = NarrativeAnalysisEngine()
    base = engine._finding(
        "plot",
        "unresolved_promise",
        "high",
        "The promise to return the seal remains unresolved.",
        evidence=["The promise appears in Chapter 1."],
        chapters=[1],
        elements=["return-seal"],
    )
    projection = {
        **base,
        "finding_id": "critique-projection",
        "source_finding_id": base["finding_id"],
        "recommended_actions": ["Pay off the promise."],
    }
    one = engine._scores([base])
    projected = engine._scores([base, projection])
    assert projected == one
    assert len(engine._deduplicate_findings([base, projection])) == 1


def test_semantic_finding_deduplication_is_stable_across_reanalysis():
    engine = NarrativeAnalysisEngine()
    duplicate = {
        "finding_id": "audit-repeat",
        "semantic_issue_id": "unresolved-promise-1",
        "domain": "plot",
        "category": "unresolved_promise",
        "severity": "medium",
        "explanation": "A promise remains unresolved.",
        "evidence": ["Chapter 1"],
        "recommended_actions": ["Resolve the promise."],
    }
    first = engine._deduplicate_findings([
        duplicate,
        {**duplicate, "finding_id": "health-repeat", "evidence": ["Scene 2"]},
    ])
    second = engine._deduplicate_findings(first)

    assert len(second) == 1
    assert second[0]["evidence"] == ["Chapter 1", "Scene 2"]


def test_scene_order_uses_chapter_then_scene_order_not_ids(client):
    project = _project(client, "RC8 ordered long form")
    pid = ObjectId(project["id"])
    db = _database()
    try:
        arc_id = "arc-ordering"
        db.story_arcs.insert_one(
            {"project_id": pid, "arc_id": arc_id, "title": "Ordered Arc", "order": 1, "focus_role": "current"}
        )
        chapters = []
        scenes = []
        for chapter_number in range(11, 0, -1):
            # IDs intentionally sort in the opposite direction of narrative order.
            chapter_id = f"chapter-{100 - chapter_number:03d}"
            chapters.append(
                {
                    "project_id": pid,
                    "chapter_plan_id": chapter_id,
                    "arc_id": arc_id,
                    "chapter_number": chapter_number,
                    "title": f"Chapter {chapter_number}",
                    "status": "approved",
                }
            )
            for scene_order in range(5, 0, -1):
                scenes.append(
                    {
                        "project_id": pid,
                        "scene_id": f"scene-{100 - chapter_number:03d}-{10 - scene_order}",
                        "chapter_plan_id": chapter_id,
                        "arc_id": arc_id,
                        "title": f"Chapter {chapter_number} Scene {scene_order}",
                        "purpose": "Advance the ordered test.",
                        "conflict": "Ordering competes with identifier shape.",
                        "outcome": "Narrative order wins.",
                        "order": scene_order,
                        "status": "approved",
                    }
                )
        db.chapter_plans.insert_many(chapters)
        db.scene_plans.insert_many(list(reversed(scenes)))
    finally:
        db.client.close()

    response = client.get(
        f"/api/projects/{project['id']}/scene-plans-v2", params={"arc_id": "arc-ordering"}
    )
    assert response.status_code == 200, response.text
    ordered = response.json()
    assert len(ordered) == 55
    assert [item["title"] for item in ordered] == [
        f"Chapter {chapter_number} Scene {scene_order}"
        for chapter_number in range(1, 12)
        for scene_order in range(1, 6)
    ]
    dashboard = client.get(f"/api/projects/{project['id']}/writing-dashboard")
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["current_scene"]["title"] == "Chapter 1 Scene 1"


def test_provider_success_with_contract_failure_is_application_failure(client, monkeypatch):
    trace_ids = []

    async def structurally_empty(db, *args, **kwargs):
        trace = await execution_trace_service.record(
            db,
            provider="mock",
            model="provider-success-invalid-application",
            agent_name=kwargs.get("agent_name"),
            prompt_tokens=20,
            response_tokens=5,
            status="success",
            project_id=(kwargs.get("trace_context") or {}).get("project_id"),
        )
        trace_ids.append(trace["_id"])
        return {
            "content": '{"scene_draft":{"generated_text":""}}',
            "parsed": {"scene_draft": {"generated_text": ""}},
            "provider": "mock",
            "model": "provider-success-invalid-application",
            "tokens_used": 25,
            "latency_ms": 1,
            "execution_trace_id": trace["_id"],
        }

    monkeypatch.setattr(provider_gateway, "generate_with_failover", structurally_empty)
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = prepare_draftable_arc(client)
    _, scenes = create_chapter_and_scenes(
        client, project_id, arc_id, knowledge, artifact, foreshadow, timeline
    )
    response = client.post(
        f"/api/projects/{project_id}/scene-plans/{scenes[0]['scene_id']}/generate-draft",
        json={"request_id": "invalid-contract-outcome"},
    )
    assert response.status_code == 409, response.text
    db = _database()
    try:
        traces = list(db.execution_traces.find({"_id": {"$in": [ObjectId(value) for value in trace_ids]}}))
        assert len(traces) == 2
        assert traces[-1]["status"] == "success"
        assert traces[-1]["application_outcome"]["validation_success"] is False
        assert traces[-1]["application_outcome"]["final_outcome"] == "application_validation_failed"
        assert db.scene_drafts.count_documents(
            {"project_id": ObjectId(project_id), "scene_id": scenes[0]["scene_id"]}
        ) == 0
    finally:
        db.client.close()


def test_beginner_ai_intent_returns_story_content_for_all_seven_steps(client, monkeypatch):
    project = _project(client, "RC8 guided creativity")
    suggestions = {
        "story idea": "A clockmaker must steal one hour from a city that sells its citizens' memories.",
        "main character": "Nera Vale is a stubborn apprentice clockmaker who fears forgetting her brother.",
        "world": "In Bellhaven, every public clock stores one paid memory and stops during a lie.",
        "conflict": "Nera needs the stolen hour to save her brother, but taking it will erase a district's past.",
        "first decision": "The city has exactly seven memory clocks, and the seventh is forbidden.",
        "first arc": "Nera infiltrates the clock guild, discovers the hour was already stolen, and chooses an unlikely ally.",
        "first scene": "Goal: enter the guild archive. Trouble: her brother's memory appears in a seized clock. Outcome: she steals the wrong key.",
    }

    async def creative_generation(*args, **kwargs):
        prompt = kwargs["prompt"]
        assert prompt["intent"] == "narrative_creation"
        query = str(prompt["query"]).lower()
        label = next(label for label in suggestions if label in query)
        return {
            "parsed": {"answer": suggestions[label], "navigation_actions": [], "canon_proposals": []},
            "content": "",
            "metadata": {"provider": "test", "model": "guided-creation"},
        }

    monkeypatch.setattr(narrative_interaction_service, "_generate", creative_generation)
    for label, expected in suggestions.items():
        response = client.post(
            f"/api/projects/{project['id']}/assistant",
            json={
                "query": f"Help me define my {label} for this project.",
                "mode": "character_interviewer" if label == "main character" else "story_coach",
                "active_surface": "guide",
                "intent": "narrative_creation",
                "request_id": f"guided-{label.replace(' ', '-')}",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["answer"] == expected
        assert response.json()["reasoning_layer"] == "project"


def test_assistant_combines_page_help_next_action_and_deduplicates_retry(client):
    project = _project(client, "RC8 assistant application help")
    request = {
        "query": "What does this page do and what should I do next?",
        "mode": "story_coach",
        "active_surface": "canon",
        "request_id": "compound-help-once",
    }
    first = client.post(f"/api/projects/{project['id']}/assistant", json=request)
    second = client.post(f"/api/projects/{project['id']}/assistant", json=request)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    payload = first.json()
    assert payload["message_id"] == second.json()["message_id"]
    assert "canon" in payload["answer"].lower()
    assert "next useful step" in payload["answer"].lower()
    assert len(payload["navigation_actions"]) >= 1
    db = _database()
    try:
        assert db.narrative_assistant_messages.count_documents(
            {"project_id": ObjectId(project["id"]), "request_id": "compound-help-once"}
        ) == 1
    finally:
        db.client.close()


def test_publication_blockers_are_author_language_and_actionable(client):
    project = _project(client, "RC8 publication blockers")
    manuscript = post(
        client,
        f"/api/projects/{project['id']}/manuscripts",
        {"title": "Unfinished Manuscript"},
    )
    response = client.get(
        f"/api/projects/{project['id']}/manuscripts/{manuscript['manuscript_id']}/publication-preflight"
    )
    assert response.status_code == 200, response.text
    preflight = response.json()
    assert preflight["ready"] is False
    assert preflight["blockers"]
    assert len(preflight["blocker_details"]) == len(preflight["blockers"])
    assert all(item["explanation"] and item["why_it_matters"] for item in preflight["blocker_details"])
    assert all(item["action"] and item["destination"] for item in preflight["blocker_details"])
    assert all("_id" not in item["explanation"].lower() for item in preflight["blocker_details"])
