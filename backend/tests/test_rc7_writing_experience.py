import time

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config
from tests.test_drafting_v2 import (
    create_chapter_and_scenes,
    post,
    prepare_draftable_arc,
)


def test_exploratory_first_draft_unblocks_writing_without_bypassing_approval(client):
    project = post(
        client,
        "/api/projects",
        {
            "title": f"River of Borrowed Names {time.time_ns()}",
            "premise": "A ferryman must save his daughter without surrendering a stranger's memory.",
            "genre": "Fantasy",
            "tone": "Intimate and tense",
            "themes": ["Memory", "Parental love"],
        },
    )
    project_id = project["id"]
    arc = post(
        client,
        f"/api/projects/{project_id}/arcs",
        {
            "title": "The Last Crossing",
            "purpose": "Force Tomas to choose between family and an innocent life.",
            "goal": "Cross the sealed river before dawn.",
            "conflict": "The toll collector demands a living memory.",
            "stakes": "His daughter dies if he waits; a stranger loses herself if he pays.",
            "approval_status": "draft",
            "development_status": "idea",
            "chapter_range": [1, 1],
            "order": 1,
        },
    )
    chapter = post(
        client,
        f"/api/projects/{project_id}/chapter-plans",
        {
            "arc_id": arc["arc_id"],
            "chapter_number": 1,
            "title": "The Toll",
            "purpose": "Present the impossible cost.",
            "conflict": "Tomas cannot pay without harming someone.",
            "character_focus": ["Tomas"],
            "status": "planned",
        },
    )
    scene = post(
        client,
        f"/api/projects/{project_id}/scene-plans-v2",
        {
            "arc_id": arc["arc_id"],
            "chapter_plan_id": chapter["chapter_plan_id"],
            "title": "A Hand on the Rope",
            "purpose": "Make Tomas face the toll.",
            "conflict": "The ferryman refuses to name an innocent memory.",
            "outcome": "He lies about whose memory he will surrender.",
            "character_focus": ["Tomas"],
            "character_change": "Resolve becomes compromised resolve.",
            "status": "planned",
            "order": 1,
        },
    )

    blocked = client.post(
        f"/api/projects/{project_id}/scene-plans/{scene['scene_id']}/generate-draft",
        json={},
    )
    assert blocked.status_code == 409

    generated = post(
        client,
        f"/api/projects/{project_id}/scene-plans/{scene['scene_id']}/generate-draft",
        {
            "allow_exploratory": True,
            "request_id": "first-exploratory-attempt",
        },
    )
    draft = generated["draft"]
    assert draft["exploratory"] is True
    assert draft["planning_gate_result"] == "FAIL"
    assert draft["planning_gate_blockers"]
    assert draft["generated_text"]
    assert "[Paragraph " not in draft["generated_text"]
    assert draft["why"]
    assert draft["expected_impact"]
    assert draft["version_label"] == "Version A"

    review = client.put(
        f"/api/projects/{project_id}/scene-drafts/{draft['draft_id']}/status",
        json={"status": "review"},
    )
    assert review.status_code == 200
    approval = client.put(
        f"/api/projects/{project_id}/scene-drafts/{draft['draft_id']}/status",
        json={"status": "approved"},
    )
    assert approval.status_code == 409

    dashboard = client.get(
        f"/api/projects/{project_id}/writing-dashboard"
    )
    assert dashboard.status_code == 200, dashboard.text
    payload = dashboard.json()
    assert payload["current_scene"]["scene_id"] == scene["scene_id"]
    assert payload["current_draft"]["exploratory"] is True
    assert payload["workflow"]["active_stage"] in {"Review draft", "Revise"}
    assert payload["scene_health"]["blockers"]


def test_scene_versions_are_idempotent_comparable_and_preserve_paragraph_work(client):
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = (
        prepare_draftable_arc(client)
    )
    _, scenes = create_chapter_and_scenes(
        client, project_id, arc_id, knowledge, artifact, foreshadow, timeline
    )
    scene_id = scenes[0]["scene_id"]
    first = post(
        client,
        f"/api/projects/{project_id}/scene-plans/{scene_id}/generate-draft",
        {"request_id": "stable-generation-request"},
    )
    duplicate = post(
        client,
        f"/api/projects/{project_id}/scene-plans/{scene_id}/generate-draft",
        {"request_id": "stable-generation-request"},
    )
    assert duplicate["deduplicated"] is True
    assert duplicate["draft"]["draft_id"] == first["draft"]["draft_id"]

    mongo = MongoClient(app_config.mongodb_url)
    db = mongo[app_config.database_name]
    pid = ObjectId(project_id)
    paragraph = db.scene_paragraphs.find_one(
        {"project_id": pid, "scene_id": scene_id},
        sort=[("order", 1)],
    )
    assert paragraph
    db.scene_paragraphs.update_one(
        {"_id": paragraph["_id"]},
        {"$set": {"prose": "Tomas tightened the wet rope and did not look at his daughter."}},
    )
    paragraph_id = paragraph["paragraph_id"]

    second = post(
        client,
        f"/api/projects/{project_id}/scene-drafts/{first['draft']['draft_id']}/regenerate",
        {
            "change_reason": "Increase emotional subtext without stating Tomas is afraid.",
            "operation": "emotion",
            "request_id": "emotion-alternative",
        },
    )["draft"]
    preserved = db.scene_paragraphs.find_one(
        {"project_id": pid, "scene_id": scene_id, "paragraph_id": paragraph_id}
    )
    assert preserved
    assert preserved["prose"].startswith("Tomas tightened")
    assert second["version_label"] == "Version B"
    assert second["operation"] == "emotion"
    assert db.scene_drafts.count_documents(
        {"project_id": pid, "scene_id": scene_id}
    ) == 2

    favorite = client.put(
        f"/api/projects/{project_id}/scene-drafts/{second['draft_id']}/favorite",
        json={"favorite": True},
    )
    assert favorite.status_code == 200, favorite.text
    assert favorite.json()["favorite"] is True

    comparison = client.get(
        f"/api/projects/{project_id}/scene-drafts/compare",
        params={
            "left_draft_id": first["draft"]["draft_id"],
            "right_draft_id": second["draft_id"],
        },
    )
    assert comparison.status_code == 200, comparison.text
    compared = comparison.json()
    assert compared["left"]["label"] == "Version A"
    assert compared["right"]["label"] == "Version B"
    assert isinstance(compared["similarity_percent"], int)
    assert compared["summary"]
    merged = post(
        client,
        f"/api/projects/{project_id}/scene-drafts/merge",
        {
            "left_draft_id": first["draft"]["draft_id"],
            "right_draft_id": second["draft_id"],
            "merged_text": (
                first["draft"]["generated_text"]
                + "\n\n"
                + second["generated_text"].split("\n\n")[-1]
            ),
            "reason": "Keep the first opening and the stronger final beat.",
        },
    )["draft"]
    assert merged["version_label"] == "Version C"
    assert merged["status"] == "review"
    assert merged["generated_by"] == "author_merge"
    assert merged["merged_from_draft_ids"] == [
        first["draft"]["draft_id"],
        second["draft_id"],
    ]
    mongo.close()


def test_review_stage_revision_pass_promotes_only_after_author_approval(client):
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = (
        prepare_draftable_arc(client)
    )
    _, scenes = create_chapter_and_scenes(
        client, project_id, arc_id, knowledge, artifact, foreshadow, timeline
    )
    original = post(
        client,
        f"/api/projects/{project_id}/scene-plans/{scenes[0]['scene_id']}/generate-draft",
        {"request_id": "revision-source"},
    )["draft"]
    assert client.put(
        f"/api/projects/{project_id}/scene-drafts/{original['draft_id']}/status",
        json={"status": "review"},
    ).status_code == 200

    review = post(
        client,
        f"/api/projects/{project_id}/editorial/review/scene/{original['draft_id']}",
    )
    branch = post(
        client,
        f"/api/projects/{project_id}/revision-branches",
        {
            "source_draft_type": "scene",
            "source_draft_id": original["draft_id"],
            "title": "Let the reader feel Tomas hesitate",
            "revision_pass": "emotion",
        },
    )
    assert branch["revision_pass"] == "emotion"
    proposal = post(
        client,
        f"/api/projects/{project_id}/revision-branches/{branch['branch_id']}/generate",
        {
            "change_reason": "Replace named emotions with physical hesitation and subtext.",
            "revision_pass": "emotion",
            "report_ids": [review["report"]["report_id"]],
            "request_id": "emotion-pass-one",
        },
    )
    assert proposal["revision_pass"] == "emotion"
    assert proposal["generated_text"]
    assert proposal["reason"]
    assert proposal["estimated_improvement"]
    assert proposal["what_stays_unchanged"]

    # The author compares before applying, while the source is still in review.
    comparison = client.get(
        f"/api/projects/{project_id}/revision-branches/{branch['branch_id']}/compare"
    )
    assert comparison.status_code == 200, comparison.text
    assert comparison.json()["source_text"] == original["generated_text"]

    assert client.put(
        f"/api/projects/{project_id}/revision-branches/{branch['branch_id']}/status",
        json={"status": "review"},
    ).status_code == 200
    assert client.put(
        f"/api/projects/{project_id}/revision-branches/{branch['branch_id']}/status",
        json={"status": "approved"},
    ).status_code == 200
    applied = post(
        client,
        f"/api/projects/{project_id}/revision-branches/{branch['branch_id']}/apply",
    )
    promoted = applied["draft"]
    assert promoted["version_label"] == "Version B"
    assert promoted["status"] == "review"
    assert promoted["parent_version_id"] == original["draft_id"]
    assert promoted["generated_text"] == proposal["generated_text"]
    assert promoted["generated_by"] == "RevisionAgent"

    history = client.get(
        f"/api/projects/{project_id}/scene-drafts",
        params={"scene_id": scenes[0]["scene_id"]},
    ).json()
    assert len(history) == 2
    source = next(item for item in history if item["draft_id"] == original["draft_id"])
    assert source["generated_text"] == original["generated_text"]


def test_adjacent_scene_generation_exposes_momentum_handoff(client):
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = (
        prepare_draftable_arc(client)
    )
    _, scenes = create_chapter_and_scenes(
        client, project_id, arc_id, knowledge, artifact, foreshadow, timeline
    )
    first = post(
        client,
        f"/api/projects/{project_id}/scene-plans/{scenes[0]['scene_id']}/generate-draft",
        {"request_id": "momentum-first"},
    )["draft"]
    assert client.put(
        f"/api/projects/{project_id}/scene-drafts/{first['draft_id']}/status",
        json={"status": "review"},
    ).status_code == 200
    assert client.put(
        f"/api/projects/{project_id}/scene-drafts/{first['draft_id']}/status",
        json={"status": "approved"},
    ).status_code == 200

    second = post(
        client,
        f"/api/projects/{project_id}/scene-plans/{scenes[1]['scene_id']}/generate-draft",
        {"request_id": "momentum-second"},
    )["draft"]
    assert second["scene_goal"]
    assert second["scene_trouble"]
    assert second["scene_stakes"]
    assert second["distinct_progression"]
    assert second["connection_from_previous"]
    assert second["handoff_to_next"]
    assert second["connection_from_previous"] != second["handoff_to_next"]
