import time


def create_project(client, title="The Last Kingdom of Aether"):
    response = client.post(
        "/api/projects",
        json={
            "title": f"{title} {time.time_ns()}",
            "premise": "Aether's last cartographer must restore a kingdom erased from shared memory.",
            "idea_dump": "The crown, maps, and inherited power reveal different truths by arc.",
            "genre": "Fantasy",
            "tone": "Mythic and intimate",
            "themes": ["Memory", "Stewardship"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_arc(client, project_id, title, order, **overrides):
    payload = {
        "title": title,
        "purpose": f"Develop {title}.",
        "goal": "Restore one lost road.",
        "conflict": "The crown demands control of the map.",
        "stakes": "A province may vanish from collective memory.",
        "resolution_direction": "The road returns under shared stewardship.",
        "approval_status": "approved" if order == 1 else "discussed",
        "development_status": "approved" if order == 1 else "development",
        "chapter_range": [1 + (order - 1) * 6, order * 6],
        "mysteries": ["Who erased the kingdom?"],
        "order": order,
        **overrides,
    }
    response = client.post(f"/api/projects/{project_id}/arcs", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def approve_checklist(client, project_id, arc_id):
    items = client.get(
        f"/api/projects/{project_id}/arc-checklists", params={"arc_id": arc_id}
    ).json()
    assert items
    for item in items:
        response = client.put(
            f"/api/projects/{project_id}/arc-checklists/{item['item_id']}",
            json={"status": "approved", "evidence": ["Author approved"]},
        )
        assert response.status_code == 200, response.text


def add_readiness(client, project_id, arc_id):
    for title in ["Protagonist", "Arc Goal", "Major Conflict"]:
        response = client.post(
            f"/api/projects/{project_id}/readiness",
            json={
                "arc_id": arc_id,
                "category": "Arc Foundation",
                "title": title,
                "priority": "required",
                "status": "approved",
                "evidence": ["Approved"],
                "blocking": True,
            },
        )
        assert response.status_code == 200, response.text


def test_arc_maturity_and_future_arc_isolation(client):
    project_id = create_project(client)["id"]
    arc1 = create_arc(client, project_id, "Arc 1: The Aether Crown", 1)
    arc2 = create_arc(client, project_id, "Arc 2: The Broken Meridian", 2)
    arc3 = create_arc(
        client,
        project_id,
        "Arc 3: Beyond the Last Road",
        3,
        goal="",
        conflict="",
        stakes="",
        resolution_direction="",
        mysteries=[],
        approval_status="draft",
        development_status="idea",
    )

    assert client.post(
        f"/api/projects/{project_id}/arcs/{arc1['arc_id']}/activate"
    ).status_code == 200
    add_readiness(client, project_id, arc1["arc_id"])
    approve_checklist(client, project_id, arc1["arc_id"])

    timeline_ids = []
    for order, title in enumerate(
        ["The map wakes", "The crown seizes the road", "Aether chooses stewardship"],
        start=1,
    ):
        response = client.post(
            f"/api/projects/{project_id}/timeline-v2",
            json={
                "arc_id": arc1["arc_id"],
                "title": title,
                "summary": title,
                "importance": "major",
                "status": "approved",
                "certainty": "known",
                "dependencies": [],
                "chapter_range": [],
                "order": order,
            },
        )
        assert response.status_code == 200
        timeline_ids.append(response.json()["entry_id"])

    progression = client.post(
        f"/api/projects/{project_id}/character-progressions",
        json={
            "arc_id": arc1["arc_id"],
            "character": "Mara",
            "current_state": "Guards the map alone",
            "desired_state": "Shares stewardship",
            "arc_start_state": "Guards the map alone",
            "arc_midpoint_state": "Trusts one witness",
            "arc_end_state": "Shares stewardship",
            "emotional_growth": "Fear becomes accountable trust",
            "maturity_growth": "Accepts limits",
            "power_growth": ["Reads one restored road"],
            "relationship_growth": ["Accepts Cael as a witness"],
            "belief_changes": ["Control is not safety"],
            "goal_changes": ["Restore the road for everyone"],
            "skills": [],
            "powers": [],
            "beliefs": [],
            "relationships": [],
            "maturity": "",
            "trauma": [],
            "goals": [],
        },
    )
    assert progression.status_code == 200, progression.text
    power = client.post(
        f"/api/projects/{project_id}/power-progressions",
        json={
            "arc_id": arc1["arc_id"],
            "character": "Mara",
            "starting_power": "Sees erased borders",
            "ending_power": "Restores one witnessed road",
            "new_abilities": ["Witness-bound restoration"],
            "mastered_abilities": [],
            "limitations": ["Requires a living witness"],
            "costs": ["Loses one private route"],
            "future_evolution": "Restore a network, not a kingdom",
        },
    )
    assert power.status_code == 200, power.text

    knowledge = client.post(
        f"/api/projects/{project_id}/knowledge",
        json={
            "arc_id": arc1["arc_id"],
            "title": "The crown erased Aether",
            "content": "The crown erased the kingdom to monopolize its roads.",
            "knowledge_type": "WORLD_TRUTH",
            "known_by": [],
            "not_known_by": ["Mara"],
            "confidence": 1,
        },
    ).json()
    assert client.post(
        f"/api/projects/{project_id}/knowledge-evolutions",
        json={
            "arc_id": arc1["arc_id"],
            "knowledge_entry_id": knowledge["entry_id"],
            "event_type": "reveal",
            "summary": "Mara learns who erased Aether.",
            "order": 3,
            "evidence": ["Climax reveal"],
        },
    ).status_code == 200

    foreshadow = client.post(
        f"/api/projects/{project_id}/foreshadowing-v2",
        json={
            "arc_planted": arc1["arc_id"],
            "seed": "The crown's map has one deliberate blank.",
            "payoff_target": "The blank names Aether.",
            "status": "seeded",
            "timeline_entry_ids": [timeline_ids[0]],
        },
    ).json()
    for order, event_type in enumerate(["seed", "payoff"], start=1):
        assert client.post(
            f"/api/projects/{project_id}/foreshadow-chains",
            json={
                "arc_id": arc1["arc_id"],
                "foreshadow_id": foreshadow["entry_id"],
                "event_type": event_type,
                "summary": f"{event_type} the blank map",
                "order": order,
                "evidence": [event_type],
            },
        ).status_code == 200

    artifact = client.post(
        f"/api/projects/{project_id}/artifacts",
        json={
            "item": "The Aether Crown",
            "owner": "Mara",
            "power": "Stores erased roads",
            "hidden_power": "Can return one road",
            "cost": "A private memory",
            "limitations": ["Requires a witness"],
            "history": "Made before the erasure",
            "future_relevance": "Connects Arc 2",
            "status": "active",
            "arc_ids": [arc1["arc_id"]],
            "character_ids": ["Mara"],
            "timeline_entry_ids": [timeline_ids[0]],
            "knowledge_entry_ids": [knowledge["entry_id"]],
        },
    ).json()
    assert client.post(
        f"/api/projects/{project_id}/artifact-evolutions",
        json={
            "arc_id": arc1["arc_id"],
            "artifact_id": artifact["artifact_id"],
            "event_type": "awakening",
            "summary": "The crown restores its first road.",
            "from_state": "Dormant",
            "to_state": "Witness-bound",
            "order": 3,
            "evidence": ["Climax use"],
        },
    ).status_code == 200

    chapter = client.post(
        f"/api/projects/{project_id}/chapter-plans",
        json={
            "arc_id": arc1["arc_id"],
            "chapter_number": 1,
            "title": "The Blank Road",
            "purpose": "Introduce Mara and the erased border.",
            "conflict": "The crown's agents close the archive.",
            "character_focus": ["Mara"],
            "knowledge_changes": [knowledge["entry_id"]],
            "artifact_ids": [artifact["artifact_id"]],
            "foreshadow_ids": [foreshadow["entry_id"]],
            "timeline_entry_ids": [timeline_ids[0]],
            "status": "approved",
        },
    )
    assert chapter.status_code == 200, chapter.text
    chapter_id = chapter.json()["chapter_plan_id"]
    scene = client.post(
        f"/api/projects/{project_id}/scene-plans-v2",
        json={
            "arc_id": arc1["arc_id"],
            "chapter_plan_id": chapter_id,
            "title": "At the erased border",
            "purpose": "Make the erasure personal.",
            "conflict": "Mara cannot prove the road existed.",
            "outcome": "The crown reacts to her touch.",
            "character_focus": ["Mara"],
            "character_change": "Isolation becomes suspicion.",
            "knowledge_changes": [knowledge["entry_id"]],
            "foreshadow_links": [foreshadow["entry_id"]],
            "artifact_interactions": [artifact["artifact_id"]],
            "timeline_impacts": [timeline_ids[0]],
            "status": "approved",
            "order": 1,
        },
    )
    assert scene.status_code == 200, scene.text

    report = client.get(
        f"/api/projects/{project_id}/arcs/{arc1['arc_id']}/development"
    ).json()
    assert report["maturity_score"] > 85
    assert report["draftable"] is True
    assert report["development_status"] == "draftable"

    arc2_report = client.get(
        f"/api/projects/{project_id}/arcs/{arc2['arc_id']}/development"
    ).json()
    arc3_report = client.get(
        f"/api/projects/{project_id}/arcs/{arc3['arc_id']}/development"
    ).json()
    assert 20 <= arc2_report["maturity_score"] <= 70
    assert arc2_report["draftable"] is False
    assert arc3_report["maturity_score"] < 30
    assert arc3_report["draftable"] is False

    arcs = client.get(f"/api/projects/{project_id}/arcs").json()
    assert sum(1 for arc in arcs if arc.get("focus_role") == "current") == 1
    assert sum(1 for arc in arcs if arc.get("drafting_eligible")) == 1


def test_dependencies_power_guard_and_no_prose_contract(client):
    project_id = create_project(client, "Aether Contracts")["id"]
    arc1 = create_arc(client, project_id, "Arc 1", 1)
    arc2 = create_arc(client, project_id, "Arc 2", 2)
    dependency = client.post(
        f"/api/projects/{project_id}/arc-dependencies",
        json={
            "arc_id": arc2["arc_id"],
            "dependency_type": "follows_arc",
            "target_id": arc1["arc_id"],
            "required_state": "completed",
            "blocking": True,
        },
    )
    assert dependency.status_code == 200
    blocked = client.post(
        f"/api/projects/{project_id}/arcs/{arc2['arc_id']}/activate"
    )
    assert blocked.status_code == 409

    power_jump = client.post(
        f"/api/projects/{project_id}/power-progressions",
        json={
            "arc_id": arc1["arc_id"],
            "character": "Mara",
            "starting_power": "Novice",
            "ending_power": "Master",
            "new_abilities": [],
            "mastered_abilities": [],
        },
    )
    assert power_jump.status_code == 400

    prose = client.post(
        f"/api/projects/{project_id}/chapter-plans",
        json={
            "arc_id": arc1["arc_id"],
            "chapter_number": 1,
            "purpose": "Plan only",
            "chapter_text": "Once upon a time",
        },
    )
    assert prose.status_code == 400


def test_story_room_and_story_development_agent_are_demand_driven(client):
    project_id = create_project(client, "Aether Story Room")["id"]
    client.post(f"/api/projects/{project_id}/cycle")
    arc = create_arc(client, project_id, "Arc 1: The Story Room", 1)
    client.put(
        f"/api/projects/{project_id}/arc-checklists/"
        + client.get(
            f"/api/projects/{project_id}/arc-checklists",
            params={"arc_id": arc["arc_id"]},
        ).json()[0]["item_id"],
        json={"status": "discussed"},
    )
    cycle = client.post(f"/api/projects/{project_id}/cycle")
    assert cycle.status_code == 200
    plan = client.get(
        f"/api/projects/{project_id}/orchestration/latest"
    ).json()
    assert "StoryDevelopmentAgent" in plan["selected_agents"]

    room = client.get(f"/api/projects/{project_id}/story-room")
    assert room.status_code == 200
    assert room.json()["open_planning_items"]

    client.put(
        f"/api/projects/{project_id}",
        json={"world_notes": "The kingdom floats above a storm sea."},
    )
    client.post(f"/api/projects/{project_id}/cycle")
    world_plan = client.get(
        f"/api/projects/{project_id}/orchestration/latest"
    ).json()
    assert "StoryDevelopmentAgent" in world_plan["skipped_agents"]
