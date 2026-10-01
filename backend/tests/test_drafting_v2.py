import time

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config
from app.services.provider_gateway import provider_gateway


def post(client, url, payload=None):
    response = client.post(url, json=payload or {})
    assert response.status_code == 200, response.text
    return response.json()


def prepare_draftable_arc(client):
    project = post(
        client,
        "/api/projects",
        {
            "title": f"The Crown of Emberfall {time.time_ns()}",
            "premise": "An ember-crowned heir must restore a city whose fires remember betrayal.",
            "genre": "Fantasy",
            "tone": "Intimate and mythic",
            "themes": ["Memory", "Stewardship"],
        },
    )
    project_id = project["id"]
    arc = post(
        client,
        f"/api/projects/{project_id}/arcs",
        {
            "title": "Arc 1: The Remembering Flame",
            "purpose": "Restore Emberfall's first civic flame.",
            "goal": "Relight the witness flame.",
            "conflict": "The regent wants the flame to remember only royal history.",
            "stakes": "The city loses its shared past.",
            "resolution_direction": "The flame becomes a public trust.",
            "approval_status": "approved",
            "development_status": "approved",
            "chapter_range": [1, 3],
            "mysteries": ["Who changed the flame's memory?"],
            "order": 1,
        },
    )
    arc_id = arc["arc_id"]
    post(client, f"/api/projects/{project_id}/arcs/{arc_id}/activate")
    for title in ["Protagonist", "Arc Goal", "Major Conflict"]:
        post(
            client,
            f"/api/projects/{project_id}/readiness",
            {
                "arc_id": arc_id,
                "category": "Arc Foundation",
                "title": title,
                "priority": "required",
                "status": "approved",
                "evidence": ["Approved"],
                "blocking": True,
            },
        )
    checklist = client.get(
        f"/api/projects/{project_id}/arc-checklists",
        params={"arc_id": arc_id},
    ).json()
    for item in checklist:
        response = client.put(
            f"/api/projects/{project_id}/arc-checklists/{item['item_id']}",
            json={"status": "approved", "evidence": ["Approved"]},
        )
        assert response.status_code == 200, response.text

    timeline = []
    for order, title in enumerate(
        ["The ash gate opens", "The regent claims the flame", "The city witnesses together"],
        start=1,
    ):
        timeline.append(
            post(
                client,
                f"/api/projects/{project_id}/timeline-v2",
                {
                    "arc_id": arc_id,
                    "title": title,
                    "summary": title,
                    "importance": "major",
                    "status": "approved",
                    "certainty": "known",
                    "dependencies": [],
                    "chapter_range": [order, order],
                    "order": order,
                },
            )
        )
    post(
        client,
        f"/api/projects/{project_id}/character-progressions",
        {
            "arc_id": arc_id,
            "character": "Ilyra",
            "current_state": "Guards memory alone",
            "desired_state": "Shares public stewardship",
            "arc_start_state": "Guards memory alone",
            "arc_midpoint_state": "Trusts one witness",
            "arc_end_state": "Shares public stewardship",
            "emotional_growth": "Control becomes trust",
            "maturity_growth": "Accepts limits",
            "power_growth": ["Reads the witness flame"],
            "relationship_growth": ["Trusts Rowan"],
            "belief_changes": ["Truth survives participation"],
            "goal_changes": ["Restore the flame for everyone"],
            "skills": [],
            "powers": [],
            "beliefs": [],
            "relationships": [],
            "maturity": "",
            "trauma": [],
            "goals": [],
        },
    )
    post(
        client,
        f"/api/projects/{project_id}/power-progressions",
        {
            "arc_id": arc_id,
            "character": "Ilyra",
            "starting_power": "Sees ember memories",
            "ending_power": "Shares one witnessed memory",
            "new_abilities": ["Witness sharing"],
            "mastered_abilities": [],
            "limitations": ["Requires consent"],
            "costs": ["Loses warmth"],
            "future_evolution": "A civic memory network",
        },
    )
    knowledge = post(
        client,
        f"/api/projects/{project_id}/knowledge",
        {
            "arc_id": arc_id,
            "title": "The regent altered the flame",
            "content": "The regent removed the rebellion from public memory.",
            "knowledge_type": "WORLD_TRUTH",
            "known_by": [],
            "not_known_by": ["Ilyra"],
            "confidence": 1,
        },
    )
    post(
        client,
        f"/api/projects/{project_id}/knowledge-evolutions",
        {
            "arc_id": arc_id,
            "knowledge_entry_id": knowledge["entry_id"],
            "event_type": "reveal",
            "summary": "Ilyra confirms the alteration.",
            "order": 3,
            "evidence": ["Flame memory"],
        },
    )
    foreshadow = post(
        client,
        f"/api/projects/{project_id}/foreshadowing-v2",
        {
            "arc_planted": arc_id,
            "seed": "One ember burns cold.",
            "payoff_target": "The cold ember holds the erased rebellion.",
            "payoff_arc_id": arc_id,
            "status": "seeded",
            "timeline_entry_ids": [timeline[0]["entry_id"]],
        },
    )
    for order, event_type in enumerate(["seed", "payoff"], start=1):
        post(
            client,
            f"/api/projects/{project_id}/foreshadow-chains",
            {
                "arc_id": arc_id,
                "foreshadow_id": foreshadow["entry_id"],
                "event_type": event_type,
                "summary": event_type,
                "order": order,
                "evidence": [event_type],
            },
        )
    artifact = post(
        client,
        f"/api/projects/{project_id}/artifacts",
        {
            "item": "The Ember Crown",
            "owner": "Ilyra",
            "power": "Reads civic flame memories",
            "hidden_power": "Shares a memory with witnesses",
            "cost": "Warmth",
            "limitations": ["Requires consent"],
            "history": "Forged at the city's founding",
            "future_relevance": "Arc 2",
            "status": "active",
            "arc_ids": [arc_id],
            "character_ids": ["Ilyra"],
            "timeline_entry_ids": [timeline[0]["entry_id"]],
            "knowledge_entry_ids": [knowledge["entry_id"]],
        },
    )
    post(
        client,
        f"/api/projects/{project_id}/artifact-evolutions",
        {
            "arc_id": arc_id,
            "artifact_id": artifact["artifact_id"],
            "event_type": "awakening",
            "summary": "The crown shares its first memory.",
            "from_state": "Private",
            "to_state": "Witness-bound",
            "order": 3,
            "evidence": ["Climax"],
        },
    )
    report = client.get(
        f"/api/projects/{project_id}/arcs/{arc_id}/development"
    ).json()
    assert report["draftable"] is True
    return project_id, arc_id, knowledge, artifact, foreshadow, timeline


def create_chapter_and_scenes(
    client, project_id, arc_id, knowledge, artifact, foreshadow, timeline
):
    chapter = post(
        client,
        f"/api/projects/{project_id}/chapter-plans",
        {
            "arc_id": arc_id,
            "chapter_number": 1,
            "title": "The Cold Ember",
            "purpose": "Discover the altered memory.",
            "conflict": "The regent seals the ash gate.",
            "character_focus": ["Ilyra"],
            "knowledge_changes": [knowledge["entry_id"]],
            "artifact_ids": [artifact["artifact_id"]],
            "foreshadow_ids": [foreshadow["entry_id"]],
            "timeline_entry_ids": [timeline[0]["entry_id"]],
            "status": "approved",
        },
    )
    scenes = []
    for order, title in enumerate(["At the Ash Gate", "The Cold Ember Answers"], start=1):
        scenes.append(
            post(
                client,
                f"/api/projects/{project_id}/scene-plans-v2",
                {
                    "arc_id": arc_id,
                    "chapter_plan_id": chapter["chapter_plan_id"],
                    "title": title,
                    "purpose": title,
                    "conflict": "The regent's guards deny the public record.",
                    "outcome": "Ilyra gains one approved piece of evidence.",
                    "character_focus": ["Ilyra"],
                    "character_change": "Isolation becomes cautious trust.",
                    "knowledge_changes": [knowledge["entry_id"]],
                    "foreshadow_links": [foreshadow["entry_id"]],
                    "artifact_interactions": [artifact["artifact_id"]],
                    "timeline_impacts": [timeline[0]["entry_id"]],
                    "status": "approved",
                    "order": order,
                },
            )
        )
    return chapter, scenes


def test_scene_versioning_review_regeneration_and_rollback(client):
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = (
        prepare_draftable_arc(client)
    )
    _, scenes = create_chapter_and_scenes(
        client, project_id, arc_id, knowledge, artifact, foreshadow, timeline
    )
    generated = post(
        client,
        f"/api/projects/{project_id}/scene-plans/{scenes[0]['scene_id']}/generate-draft",
    )
    first = generated["draft"]
    assert first["version_number"] == 1
    assert first["status"] == "draft"
    assert first["active"] is True
    assert generated["continuity_report"]["result"] == "PASS"
    assert first["continuity_claims"]["knowledge_entry_ids"] == [
        knowledge["entry_id"]
    ]
    assert first["continuity_claims"]["artifact_ids"] == [artifact["artifact_id"]]
    plan = client.get(
        f"/api/projects/{project_id}/orchestration/latest"
    ).json()
    assert plan["selected_agents"] == ["SceneWriterAgent"]
    assert all(
        task["status"] == "skipped"
        for task in plan["tasks"]
        if task["agent_name"] != "SceneWriterAgent"
    )

    response = client.put(
        f"/api/projects/{project_id}/scene-drafts/{first['draft_id']}/status",
        json={"status": "approved"},
    )
    assert response.status_code == 409
    assert client.put(
        f"/api/projects/{project_id}/scene-drafts/{first['draft_id']}/status",
        json={"status": "review"},
    ).status_code == 200
    approved = client.put(
        f"/api/projects/{project_id}/scene-drafts/{first['draft_id']}/status",
        json={"status": "approved"},
    )
    assert approved.status_code == 200, approved.text

    regenerated = post(
        client,
        f"/api/projects/{project_id}/scene-drafts/{first['draft_id']}/regenerate",
        {"change_reason": "Increase the pressure at the gate."},
    )["draft"]
    assert regenerated["version_number"] == 2
    assert regenerated["parent_version_id"] == first["draft_id"]
    history = client.get(
        f"/api/projects/{project_id}/scene-drafts",
        params={"scene_id": scenes[0]["scene_id"]},
    ).json()
    assert len(history) == 2
    assert sum(1 for item in history if item["active"]) == 1
    rollback = post(
        client,
        f"/api/projects/{project_id}/scene-drafts/{first['draft_id']}/rollback",
    )
    assert rollback["active"] is True


def test_scene_generation_repairs_empty_required_prose(client, monkeypatch):
    original = provider_gateway.generate_with_failover
    scene_writer_calls = 0

    async def empty_then_valid(*args, **kwargs):
        nonlocal scene_writer_calls
        if kwargs.get("agent_name") == "SceneWriterAgent":
            scene_writer_calls += 1
            if scene_writer_calls == 1:
                return {
                    "content": '{"scene_draft":{"generated_text":""}}',
                    "parsed": {"scene_draft": {"generated_text": ""}},
                    "provider": "mock",
                    "model": "test-empty-first-response",
                    "tokens_used": 20,
                    "latency_ms": 1,
                    "fallback_used": False,
                }
        return await original(*args, **kwargs)

    monkeypatch.setattr(
        provider_gateway,
        "generate_with_failover",
        empty_then_valid,
    )
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = (
        prepare_draftable_arc(client)
    )
    _, scenes = create_chapter_and_scenes(
        client, project_id, arc_id, knowledge, artifact, foreshadow, timeline
    )

    generated = post(
        client,
        f"/api/projects/{project_id}/scene-plans/{scenes[0]['scene_id']}/generate-draft",
    )

    assert scene_writer_calls == 2
    assert generated["draft"]["generated_text"]
    assert generated["draft"]["generation_metadata"]["corrective_retry_count"] == 1
    assert generated["draft"]["generation_metadata"]["tokens_used"] == 140


def test_chapter_assembly_preserves_approved_scene_text(client):
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = (
        prepare_draftable_arc(client)
    )
    chapter, scenes = create_chapter_and_scenes(
        client, project_id, arc_id, knowledge, artifact, foreshadow, timeline
    )
    approved_scene_drafts = []
    for scene in scenes:
        draft = post(
            client,
            f"/api/projects/{project_id}/scene-plans/{scene['scene_id']}/generate-draft",
        )["draft"]
        client.put(
            f"/api/projects/{project_id}/scene-drafts/{draft['draft_id']}/status",
            json={"status": "review"},
        )
        response = client.put(
            f"/api/projects/{project_id}/scene-drafts/{draft['draft_id']}/status",
            json={"status": "approved"},
        )
        assert response.status_code == 200, response.text
        approved_scene_drafts.append(response.json()["draft"])
    assembled = post(
        client,
        f"/api/projects/{project_id}/chapter-plans/{chapter['chapter_plan_id']}/generate-draft",
    )
    chapter_draft = assembled["draft"]
    assert assembled["continuity_report"]["result"] == "PASS"
    plan = client.get(
        f"/api/projects/{project_id}/orchestration/latest"
    ).json()
    assert plan["selected_agents"] == ["ChapterAssemblerAgent"]
    assert chapter_draft["source_scene_draft_ids"] == [
        item["draft_id"] for item in approved_scene_drafts
    ]
    positions = [
        chapter_draft["generated_text"].index(item["generated_text"])
        for item in approved_scene_drafts
    ]
    assert positions == sorted(positions)
    assert client.put(
        f"/api/projects/{project_id}/chapter-drafts/{chapter_draft['draft_id']}/status",
        json={"status": "review"},
    ).status_code == 200
    assert client.put(
        f"/api/projects/{project_id}/chapter-drafts/{chapter_draft['draft_id']}/status",
        json={"status": "approved"},
    ).status_code == 200


def test_fail_validation_blocks_approval_and_partial_arc_blocks_generation(client):
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = (
        prepare_draftable_arc(client)
    )
    _, scenes = create_chapter_and_scenes(
        client, project_id, arc_id, knowledge, artifact, foreshadow, timeline
    )
    draft = post(
        client,
        f"/api/projects/{project_id}/scene-plans/{scenes[0]['scene_id']}/generate-draft",
    )["draft"]
    mongo = MongoClient(app_config.mongodb_url)
    db = mongo[app_config.database_name]
    db.scene_drafts.update_one(
        {"project_id": ObjectId(project_id), "draft_id": draft["draft_id"]},
        {"$set": {"continuity_claims.artifact_ids": ["cross-project-artifact"]}},
    )
    assert client.put(
        f"/api/projects/{project_id}/scene-drafts/{draft['draft_id']}/status",
        json={"status": "review"},
    ).status_code == 200
    failed = client.put(
        f"/api/projects/{project_id}/scene-drafts/{draft['draft_id']}/status",
        json={"status": "approved"},
    )
    assert failed.status_code == 409
    mongo.close()

    arc2 = post(
        client,
        f"/api/projects/{project_id}/arcs",
        {
            "title": "Arc 2: The Unlit District",
            "purpose": "Reserve partial future planning.",
            "goal": "Reach the district.",
            "conflict": "Unknown opposition.",
            "stakes": "The fire may spread.",
            "approval_status": "discussed",
            "development_status": "development",
            "chapter_range": [4, 6],
            "order": 2,
        },
    )
    chapter2 = post(
        client,
        f"/api/projects/{project_id}/chapter-plans",
        {
            "arc_id": arc2["arc_id"],
            "chapter_number": 4,
            "title": "Future Chapter",
            "purpose": "Partial plan.",
            "conflict": "Open.",
            "character_focus": ["Ilyra"],
            "knowledge_changes": [],
            "artifact_ids": [],
            "foreshadow_ids": [],
            "timeline_entry_ids": [],
            "status": "approved",
        },
    )
    scene2 = post(
        client,
        f"/api/projects/{project_id}/scene-plans-v2",
        {
            "arc_id": arc2["arc_id"],
            "chapter_plan_id": chapter2["chapter_plan_id"],
            "title": "Future Scene",
            "purpose": "Placeholder.",
            "conflict": "Open.",
            "outcome": "Open.",
            "character_focus": ["Ilyra"],
            "knowledge_changes": [],
            "foreshadow_links": [],
            "artifact_interactions": [],
            "timeline_impacts": [],
            "status": "approved",
            "order": 1,
        },
    )
    blocked = client.post(
        f"/api/projects/{project_id}/scene-plans/{scene2['scene_id']}/generate-draft",
        json={},
    )
    assert blocked.status_code == 409


def test_crown_of_emberfall_three_chapter_six_scene_simulation(client):
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = (
        prepare_draftable_arc(client)
    )
    chapters = []
    scenes = []
    for chapter_number in range(1, 4):
        chapter = post(
            client,
            f"/api/projects/{project_id}/chapter-plans",
            {
                "arc_id": arc_id,
                "chapter_number": chapter_number,
                "title": f"Emberfall Chapter {chapter_number}",
                "purpose": f"Advance the approved Arc 1 movement {chapter_number}.",
                "conflict": "The regent contests the public memory.",
                "character_focus": ["Ilyra"],
                "knowledge_changes": [knowledge["entry_id"]],
                "artifact_ids": [artifact["artifact_id"]],
                "foreshadow_ids": [foreshadow["entry_id"]],
                "timeline_entry_ids": [timeline[chapter_number - 1]["entry_id"]],
                "status": "approved",
            },
        )
        chapters.append(chapter)
        for scene_offset in range(1, 3):
            scenes.append(
                post(
                    client,
                    f"/api/projects/{project_id}/scene-plans-v2",
                    {
                        "arc_id": arc_id,
                        "chapter_plan_id": chapter["chapter_plan_id"],
                        "title": f"Chapter {chapter_number} Scene {scene_offset}",
                        "purpose": "Execute one approved beat without changing planning truth.",
                        "conflict": "The public record and royal record disagree.",
                        "outcome": "Ilyra preserves the planned evidence.",
                        "character_focus": ["Ilyra"],
                        "character_change": "Control becomes shared stewardship.",
                        "knowledge_changes": [knowledge["entry_id"]],
                        "foreshadow_links": [foreshadow["entry_id"]],
                        "artifact_interactions": [artifact["artifact_id"]],
                        "timeline_impacts": [timeline[chapter_number - 1]["entry_id"]],
                        "status": "approved",
                        "order": scene_offset,
                    },
                )
            )

    for scene in scenes:
        generated = post(
            client,
            f"/api/projects/{project_id}/scene-plans/{scene['scene_id']}/generate-draft",
        )
        assert generated["continuity_report"]["result"] == "PASS"
        draft_id = generated["draft"]["draft_id"]
        assert client.put(
            f"/api/projects/{project_id}/scene-drafts/{draft_id}/status",
            json={"status": "review"},
        ).status_code == 200
        assert client.put(
            f"/api/projects/{project_id}/scene-drafts/{draft_id}/status",
            json={"status": "approved"},
        ).status_code == 200

    chapter_drafts = []
    for chapter in chapters:
        assembled = post(
            client,
            f"/api/projects/{project_id}/chapter-plans/{chapter['chapter_plan_id']}/generate-draft",
        )
        assert assembled["continuity_report"]["result"] == "PASS"
        chapter_drafts.append(assembled["draft"])

    assert len(client.get(f"/api/projects/{project_id}/scene-drafts").json()) == 6
    assert len(client.get(f"/api/projects/{project_id}/chapter-drafts").json()) == 3
    assert all(len(item["source_scene_draft_ids"]) == 2 for item in chapter_drafts)
    review_queue = client.get(
        f"/api/projects/{project_id}/draft-review-queue"
    ).json()
    assert review_queue["generation_history"] == {
        "scene_versions": 6,
        "chapter_versions": 3,
    }

    for order, status in [(2, "development"), (3, "idea")]:
        blocked_arc = post(
            client,
            f"/api/projects/{project_id}/arcs",
            {
                "title": f"Arc {order}: Future Ember",
                "purpose": "Remain intentionally incomplete.",
                "goal": "Unknown",
                "conflict": "Unknown",
                "stakes": "Unknown",
                "approval_status": "draft",
                "development_status": status,
                "chapter_range": [order * 3 + 1, order * 3 + 3],
                "order": order,
            },
        )
        blocked_chapter = post(
            client,
            f"/api/projects/{project_id}/chapter-plans",
            {
                "arc_id": blocked_arc["arc_id"],
                "chapter_number": order * 3 + 1,
                "title": "Blocked Future Chapter",
                "purpose": "Placeholder",
                "conflict": "Unknown",
                "character_focus": ["Ilyra"],
                "knowledge_changes": [],
                "artifact_ids": [],
                "foreshadow_ids": [],
                "timeline_entry_ids": [],
                "status": "approved",
            },
        )
        blocked_scene = post(
            client,
            f"/api/projects/{project_id}/scene-plans-v2",
            {
                "arc_id": blocked_arc["arc_id"],
                "chapter_plan_id": blocked_chapter["chapter_plan_id"],
                "title": "Blocked Future Scene",
                "purpose": "Placeholder",
                "conflict": "Unknown",
                "outcome": "Unknown",
                "character_focus": ["Ilyra"],
                "knowledge_changes": [],
                "foreshadow_links": [],
                "artifact_interactions": [],
                "timeline_impacts": [],
                "status": "approved",
                "order": 1,
            },
        )
        denied = client.post(
            f"/api/projects/{project_id}/scene-plans/{blocked_scene['scene_id']}/generate-draft",
            json={},
        )
        assert denied.status_code == 409
