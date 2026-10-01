import time


def create_project(client):
    response = client.post("/api/projects", json={
        "title": f"Production Integrity {time.time_ns()}",
        "premise": "A reincarnated gardener cultivates living concepts.",
        "idea_dump": "Power transactions use living materials. The System is self-created. The sister becomes politically important later.",
        "genre": "Progression fantasy",
        "tone": "Mysterious",
    })
    assert response.status_code == 200
    return response.json()["id"]


def wait_for_run(client, project_id):
    for _ in range(160):
        runs = client.get(f"/api/projects/{project_id}/runs").json()
        if runs and runs[0]["status"] in {"completed", "waiting_for_user", "failed"}:
            assert runs[0]["status"] != "failed"
            return runs[0]
        time.sleep(0.25)
    raise AssertionError("run did not finish")


def proposal_for(messages, author):
    return next(message for message in messages if message.get("author") == author)


def test_story_bible_actions_questions_and_cycles_are_consistent(client):
    project_id = create_project(client)
    client.post(f"/api/projects/{project_id}/cycle")
    first_run = wait_for_run(client, project_id)
    assert first_run["cycle_number"] == 1

    client.post(
        f"/api/projects/{project_id}/messages",
        json={
            "content": (
                "Develop the protagonist and sister relationship, the world and "
                "its factions, the living-material power system, the central "
                "theme, the mystery clues, and the next story arc."
            )
        },
    )
    client.post(f"/api/projects/{project_id}/cycle")
    second_run = wait_for_run(client, project_id)
    assert second_run["cycle_number"] == 2

    bible = client.get(f"/api/projects/{project_id}/story-bible").json()
    assert bible["cycle_number"] == 2
    assert bible["sections"]["characters"]
    assert bible["sections"]["world"]
    assert bible["sections"]["power_system"]
    assert bible["sections"]["relationships"]
    assert bible["sections"]["timeline"]
    assert bible["sections"]["arcs"]

    proposals = [
        message for message in bible["sections"]["discussion"]
        if message.get("role") == "agent"
    ]
    approve = client.post(
        f"/api/projects/{project_id}/discussion/{proposal_for(proposals, 'NarrativeDirectorAgent')['id']}/decision",
        json={"action": "approve"},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    reject = client.post(
        f"/api/projects/{project_id}/discussion/{proposal_for(proposals, 'PowerSystemAgent')['id']}/decision",
        json={"action": "reject", "note": "The cost should be tied more directly to living materials."},
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"

    modify = client.post(
        f"/api/projects/{project_id}/discussion/{proposal_for(proposals, 'FactionAgent')['id']}/decision",
        json={"action": "modify", "note": "Make the faction protect concept gardens while exploiting gardeners."},
    )
    assert modify.status_code == 200
    assert modify.json()["revision_proposal_id"]

    discuss = client.post(
        f"/api/projects/{project_id}/discussion/{proposal_for(proposals, 'RelationshipAgent')['id']}/decision",
        json={"action": "discuss", "note": "Explore how trust changes when the sister gains political leverage."},
    )
    assert discuss.status_code == 200
    assert discuss.json()["discussion_thread_id"]
    assert discuss.json()["cycle_task_id"]

    expand = client.post(
        f"/api/projects/{project_id}/discussion/{proposal_for(proposals, 'ThemeAgent')['id']}/decision",
        json={"action": "expand", "note": "Expand stewardship into a recurring moral test."},
    )
    assert expand.status_code == 200
    assert expand.json()["cycle_task_id"]

    questions = bible["sections"]["active_questions"]
    original_texts = {question["text"] for question in questions}
    for question in questions:
        answer = client.post(
            f"/api/projects/{project_id}/answers",
            json={
                "question_id": question["id"],
                "answer": "Use living materials, preserve the self-created System, and develop the sister's political agency.",
            },
        )
        assert answer.status_code == 200
        assert answer.json()["canon_updated"] is True

    resolved_bible = client.get(f"/api/projects/{project_id}/story-bible").json()
    assert not resolved_bible["sections"]["active_questions"]
    assert len(resolved_bible["sections"]["resolved_questions"]) == len(questions)
    assert resolved_bible["sections"]["canon_registry"]
    assert any(item["status"] == "approved" for item in resolved_bible["sections"]["discussion_decisions"])

    client.post(f"/api/projects/{project_id}/cycle")
    third_run = wait_for_run(client, project_id)
    assert third_run["cycle_number"] == 3
    third_bible = client.get(f"/api/projects/{project_id}/story-bible").json()
    assert third_bible["cycle_number"] == 3
    active_texts = {question["text"] for question in third_bible["sections"]["active_questions"]}
    assert original_texts.isdisjoint(active_texts)

    latest_outputs = [
        output for output in third_bible["sections"]["workflow"]["agents"]
        if output["metadata"].get("cycle_number") == 3
    ]
    latest_plan = client.get(
        f"/api/projects/{project_id}/orchestration/latest"
    ).json()
    assert len(latest_outputs) == latest_plan["actual_agent_calls"]
    assert len(latest_outputs) <= 10
    assert all(output["metadata"].get("cycle_number") == 3 for output in latest_outputs)


def test_database_audit_detects_test_mock_artifacts(client):
    project_id = create_project(client)
    client.post(f"/api/projects/{project_id}/cycle")
    wait_for_run(client, project_id)
    audit = client.get(f"/api/projects/{project_id}/audit")
    assert audit.status_code == 200
    body = audit.json()
    assert body["status"] == "fail"
    assert any(finding["type"] == "mock_data" for finding in body["findings"])
