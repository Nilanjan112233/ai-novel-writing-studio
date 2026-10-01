import pytest
from bson import ObjectId
from tests.test_drafting_v2 import prepare_draftable_arc, create_chapter_and_scenes, post


def test_scene_paragraphs_lifecycle_and_apis(client):
    # 1. Prepare drafting project and scenes
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = prepare_draftable_arc(client)
    chapter, scenes = create_chapter_and_scenes(
        client, project_id, arc_id, knowledge, artifact, foreshadow, timeline
    )
    scene_id = scenes[0]["scene_id"]

    # 2. Trigger skeletons generation
    generated_res = post(
        client,
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/generate",
        {"change_reason": "First plan"}
    )
    assert generated_res["status"] == "success"
    assert "draft" in generated_res
    assert len(generated_res["paragraphs"]) > 0

    paragraphs = generated_res["paragraphs"]
    p_id = paragraphs[0]["paragraph_id"]
    assert paragraphs[0]["order"] == 1
    assert paragraphs[0]["pov"] == "Ilyra"
    assert paragraphs[0]["is_locked"] is False
    assert paragraphs[0]["approval_state"] == "pending"

    # 3. Retrieve paragraphs list
    get_res = client.get(f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs")
    assert get_res.status_code == 200
    p_list = get_res.json()
    assert len(p_list) == len(paragraphs)

    # 4. Lock paragraph
    lock_res = post(
        client,
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/lock",
        {"is_locked": True}
    )
    assert lock_res["is_locked"] is True

    # Unlock it back
    lock_res_2 = post(
        client,
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/lock",
        {"is_locked": False}
    )
    assert lock_res_2["is_locked"] is False

    # 5. Update paragraph metadata
    update_res = client.put(
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}",
        json={
            "updates": {
                "pov": "Rowan",
                "location": "The Broken Tower",
                "purpose": "Show visual conflict",
                "dependencies": {
                    "characters": ["Rowan", "Ilyra"],
                    "canon_facts": [knowledge["entry_id"]]
                }
            },
            "change_reason": "Change POV to Rowan",
            "create_version": True
        }
    )
    assert update_res.status_code == 200, update_res.text
    p_updated = update_res.json()
    assert p_updated["pov"] == "Rowan"
    assert p_updated["location"] == "The Broken Tower"
    assert p_updated["version"] == 2

    # 6. Retrieve history
    history_res = client.get(f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/history")
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 1
    assert history[0]["snapshot"]["pov"] == "Ilyra"
    assert history[0]["change_reason"] == "Change POV to Rowan"

    # 7. Approve paragraph
    approve_res = post(
        client,
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/approve",
        {"approval_state": "approved"}
    )
    assert approve_res["approval_state"] == "approved"
    assert approve_res["processing_pipeline"]["approval"]["status"] == "completed"

    # 8. Duplicate paragraph
    dup_res = post(
        client,
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/duplicate"
    )
    assert dup_res["order"] == 2
    assert dup_res["pov"] == "Rowan"
    assert dup_res["version"] == 1
    assert dup_res["approval_state"] == "pending"

    # Check paragraphs count increased
    list_after_dup = client.get(f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs").json()
    assert len(list_after_dup) == len(paragraphs) + 1

    # 9. Reorder paragraphs
    p_id_new = dup_res["paragraph_id"]
    reorder_res = post(
        client,
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/reorder",
        {
            "reorder_payload": [
                {"paragraph_id": p_id_new, "order": 1},
                {"paragraph_id": p_id, "order": 2}
            ]
        }
    )
    assert reorder_res[0]["paragraph_id"] == p_id_new
    assert reorder_res[1]["paragraph_id"] == p_id

    # 10. Regenerate paragraph
    regen_res = post(
        client,
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/regenerate",
        {"change_reason": "Add details"}
    )
    assert regen_res["version"] == 3
    assert regen_res["regeneration_count"] == 1

    # 11. Delete paragraph
    del_res = client.delete(f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id_new}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # Check list went back to original count
    final_list = client.get(f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs").json()
    assert len(final_list) == len(paragraphs)

    # Active review threads must use the status consumed by the frozen editor.
    comment_res = client.post(
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/comments",
        json={"author": "Author", "content": "Review this transition."},
    )
    assert comment_res.status_code == 200, comment_res.text
    comment = comment_res.json()
    assert comment["status"] == "open"
    comments = client.get(
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/comments"
    ).json()
    assert comments[0]["comment_id"] == comment["comment_id"]


def test_paragraph_versioning_and_suggestions_regression(client):
    # 1. Prepare drafting project and scenes
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = prepare_draftable_arc(client)
    chapter, scenes = create_chapter_and_scenes(
        client, project_id, arc_id, knowledge, artifact, foreshadow, timeline
    )
    scene_id = scenes[0]["scene_id"]

    # 2. Generate skeletons
    gen_res = post(
        client,
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/generate",
        {"change_reason": "Setup plan"}
    )
    p_id = gen_res["paragraphs"][0]["paragraph_id"]

    # 3. Verify Autosave behavior (create_version=False)
    for i in range(1, 4):
        autosave_res = client.put(
            f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}",
            json={
                "updates": {"prose": f"Autosaved text draft {i}"},
                "create_version": False
            }
        )
        assert autosave_res.status_code == 200
        p_data = autosave_res.json()
        assert p_data["prose"] == f"Autosaved text draft {i}"
        assert p_data["autosave_version"] == i
        assert p_data["version"] == 1

    # Verify history size is 0
    history_res = client.get(f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/history")
    assert len(history_res.json()) == 0

    # 4. Verify Manual Save behavior (create_version=True)
    manual_res = client.put(
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}",
        json={
            "updates": {"prose": "Manually committed final draft text"},
            "create_version": True,
            "change_reason": "Author final commit"
        }
    )
    assert manual_res.status_code == 200
    p_data = manual_res.json()
    assert p_data["prose"] == "Manually committed final draft text"
    assert p_data["autosave_version"] == 0
    assert p_data["version"] == 2

    # Verify history size is 1, containing the autosaved text draft 3
    history_res = client.get(f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/history")
    history = history_res.json()
    assert len(history) == 1
    assert history[0]["snapshot"]["prose"] == "Autosaved text draft 3"
    assert history[0]["change_reason"] == "Author final commit"
    version_id_to_restore = history[0]["version_id"]

    # 5. Lock and Approve should NOT create history or version increments
    lock_res = post(client, f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/lock", {"is_locked": True})
    assert lock_res["is_locked"] is True
    assert lock_res["version"] == 2

    approve_res = post(client, f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/approve", {"approval_state": "approved"})
    assert approve_res["approval_state"] == "approved"
    assert approve_res["version"] == 2

    # Verify history is still 1
    history_res = client.get(f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/history")
    assert len(history_res.json()) == 1

    # 6. Verify Restore Version
    restore_res = client.post(f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/restore/{version_id_to_restore}")
    assert restore_res.status_code == 200
    p_data = restore_res.json()
    assert p_data["prose"] == "Autosaved text draft 3"
    assert p_data["version"] == 3

    # History size should now be 2, with the second containing the pre-restore state
    history_res2 = client.get(f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/history")
    history2 = history_res2.json()
    assert len(history2) == 2
    assert history2[0]["snapshot"]["prose"] == "Manually committed final draft text"

    # 7. AI suggestion lifecycle
    ai_res = post(
        client,
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/ai-edit",
        {"mode": "expand", "prompt": "Make it more descriptive"}
    )
    assert ai_res["status"] == "pending"
    assert ai_res["proposed_prose"] != ""
    sug_id = ai_res["suggestion_id"]

    # Verify suggestions list contains our new suggestion
    sug_list_res = client.get(f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/suggestions")
    assert sug_list_res.status_code == 200
    sug_list = sug_list_res.json()
    assert len(sug_list) >= 1
    assert sug_list[0]["suggestion_id"] == sug_id

    # Verify reject suggestion route works
    reject_res = post(
        client,
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/suggestions/{sug_id}/reject"
    )
    assert reject_res["status"] == "success"

    # Check suggestion is marked rejected in database
    sug_list_res_2 = client.get(f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/suggestions")
    assert sug_list_res_2.json()[0]["status"] == "rejected"

    # Create another suggestion to test accept
    ai_res_2 = post(
        client,
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/ai-edit",
        {"mode": "rewrite", "prompt": "Rewrite with higher tension"}
    )
    sug_id_2 = ai_res_2["suggestion_id"]

    # Accept the suggestion
    accept_res = post(
        client,
        f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/suggestions/{sug_id_2}/accept"
    )
    assert accept_res["prose"] == ai_res_2["proposed_prose"]
    assert accept_res["version"] == 4

    # Check suggestion status is now accepted
    sug_list_res_3 = client.get(f"/api/projects/{project_id}/scenes/{scene_id}/paragraphs/{p_id}/suggestions")
    assert sug_list_res_3.json()[0]["status"] == "accepted"
