import time

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config
from app.migrations.phase_3a import migrate_phase_3a
from app.services.editorial_service import _dimension_scores
from tests.test_drafting_v2 import (
    create_chapter_and_scenes,
    post,
    prepare_draftable_arc,
)


def approved_scene_and_chapter(client):
    project_id, arc_id, knowledge, artifact, foreshadow, timeline = (
        prepare_draftable_arc(client)
    )
    chapter, scenes = create_chapter_and_scenes(
        client,
        project_id,
        arc_id,
        knowledge,
        artifact,
        foreshadow,
        timeline,
    )
    scene_drafts = []
    for scene in scenes:
        draft = post(
            client,
            f"/api/projects/{project_id}/scene-plans/{scene['scene_id']}/generate-draft",
        )["draft"]
        assert client.put(
            f"/api/projects/{project_id}/scene-drafts/{draft['draft_id']}/status",
            json={"status": "review"},
        ).status_code == 200
        approved = client.put(
            f"/api/projects/{project_id}/scene-drafts/{draft['draft_id']}/status",
            json={"status": "approved"},
        )
        assert approved.status_code == 200, approved.text
        scene_drafts.append(approved.json()["draft"])
    chapter_draft = post(
        client,
        f"/api/projects/{project_id}/chapter-plans/{chapter['chapter_plan_id']}/generate-draft",
    )["draft"]
    assert client.put(
        f"/api/projects/{project_id}/chapter-drafts/{chapter_draft['draft_id']}/status",
        json={"status": "review"},
    ).status_code == 200
    approved_chapter = client.put(
        f"/api/projects/{project_id}/chapter-drafts/{chapter_draft['draft_id']}/status",
        json={"status": "approved"},
    )
    assert approved_chapter.status_code == 200, approved_chapter.text
    return project_id, arc_id, chapter, scenes, scene_drafts, approved_chapter.json()["draft"]


def test_editorial_dimension_scores_normalize_common_model_scales():
    assert _dimension_scores({"style": 9, "pacing": 8}) == {
        "style": 90,
        "pacing": 80,
    }
    assert _dimension_scores({"style": 82, "pacing": 76}) == {
        "style": 82,
        "pacing": 76,
    }
    assert _dimension_scores({"dialogue": 0}) == {"dialogue": 0}


def test_editorial_and_dialogue_reports_produce_deterministic_scores(client):
    project_id, arc_id, _, _, scene_drafts, chapter_draft = (
        approved_scene_and_chapter(client)
    )
    scene_id = scene_drafts[0]["draft_id"]
    editorial = post(
        client,
        f"/api/projects/{project_id}/editorial/review/scene/{scene_id}",
    )
    assert editorial["report"]["generated_by"] == "EditorAgent"
    assert editorial["report"]["score"] == 82
    assert editorial["scores"][0]["score_type"] == "scene_editorial"
    assert editorial["scores"][0]["dimensions"]["style"] == 82
    plan = client.get(
        f"/api/projects/{project_id}/orchestration/latest"
    ).json()
    assert plan["selected_agents"] == ["EditorAgent"]
    assert all(
        task["status"] == "skipped"
        for task in plan["tasks"]
        if task["agent_name"] != "EditorAgent"
    )

    dialogue = post(
        client,
        f"/api/projects/{project_id}/editorial/dialogue/scene/{scene_id}",
    )
    assert dialogue["report"]["generated_by"] == "DialogueAgent"
    assert dialogue["report"]["dimension_scores"]["dialogue"] == 76
    latest_scene_score = dialogue["scores"][0]
    assert latest_scene_score["dimensions"]["dialogue"] == 76
    assert latest_scene_score["score"] == 81

    chapter = post(
        client,
        f"/api/projects/{project_id}/editorial/review/chapter/{chapter_draft['draft_id']}",
    )
    assert chapter["report"]["subject_type"] == "chapter"
    assert chapter["scores"][0]["dimensions"]["continuity"] == 100

    arc = post(
        client,
        f"/api/projects/{project_id}/editorial/review/arc/{arc_id}",
    )
    assert arc["report"]["subject_type"] == "arc"
    assert arc["scores"][0]["score_type"] == "arc_editorial"

    dashboard = client.get(
        f"/api/projects/{project_id}/editorial/dashboard"
    ).json()
    assert len(dashboard["reports"]) == 4
    assert any(score["score_type"] == "arc_editorial" for score in dashboard["scores"])


def test_revision_branch_lineage_preserves_approved_source(client):
    project_id, _, _, _, scene_drafts, _ = approved_scene_and_chapter(client)
    source = scene_drafts[0]
    post(
        client,
        f"/api/projects/{project_id}/editorial/review/scene/{source['draft_id']}",
    )
    post(
        client,
        f"/api/projects/{project_id}/editorial/dialogue/scene/{source['draft_id']}",
    )
    branch = post(
        client,
        f"/api/projects/{project_id}/revision-branches",
        {
            "source_draft_type": "scene",
            "source_draft_id": source["draft_id"],
            "title": "Tighter dialogue",
        },
    )
    first = post(
        client,
        f"/api/projects/{project_id}/revision-branches/{branch['branch_id']}/generate",
        {"change_reason": "Tighten the exchange."},
    )
    second = post(
        client,
        f"/api/projects/{project_id}/revision-branches/{branch['branch_id']}/generate",
        {"change_reason": "Sharpen the final response."},
    )
    assert first["version_number"] == 1
    assert second["version_number"] == 2
    assert second["parent_revision_id"] == first["revision_id"]
    plan = client.get(
        f"/api/projects/{project_id}/orchestration/latest"
    ).json()
    assert plan["selected_agents"] == ["RevisionAgent"]

    mongo = MongoClient(app_config.mongodb_url)
    db = mongo[app_config.database_name]
    persisted_source = db.scene_drafts.find_one(
        {
            "project_id": ObjectId(project_id),
            "draft_id": source["draft_id"],
        }
    )
    assert persisted_source["generated_text"] == source["generated_text"]
    assert db.revision_versions.count_documents(
        {"project_id": ObjectId(project_id), "branch_id": branch["branch_id"]}
    ) == 2
    mongo.close()

    assert client.put(
        f"/api/projects/{project_id}/revision-branches/{branch['branch_id']}/status",
        json={"status": "review"},
    ).status_code == 200
    approved = client.put(
        f"/api/projects/{project_id}/revision-branches/{branch['branch_id']}/status",
        json={"status": "approved"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    lineage = client.get(
        f"/api/projects/{project_id}/revision-branches/{branch['branch_id']}/lineage"
    ).json()
    assert len(lineage["lineage"]) == 1
    assert len(lineage["lineage"][0]["versions"]) == 2
    comparison = client.get(
        f"/api/projects/{project_id}/revision-branches/{branch['branch_id']}/compare"
    ).json()
    assert comparison["source_text"] == source["generated_text"]
    assert comparison["revision_id"] == second["revision_id"]


def test_editorial_ownership_and_approval_guards(client):
    project_id, _, _, scenes, scene_drafts, _ = approved_scene_and_chapter(client)
    unapproved = post(
        client,
        f"/api/projects/{project_id}/scene-drafts/{scene_drafts[0]['draft_id']}/regenerate",
        {"change_reason": "Create an unapproved alternative."},
    )["draft"]
    blocked = client.post(
        f"/api/projects/{project_id}/editorial/review/scene/{unapproved['draft_id']}",
        json={},
    )
    assert blocked.status_code == 409

    other = post(
        client,
        "/api/projects",
        {
            "title": f"Other Editorial Project {time.time_ns()}",
            "premise": "Ownership boundary.",
        },
    )
    cross_project = client.post(
        f"/api/projects/{other['id']}/editorial/review/scene/{scene_drafts[0]['draft_id']}",
        json={},
    )
    assert cross_project.status_code == 409
    branch = client.post(
        f"/api/projects/{other['id']}/revision-branches",
        json={
            "source_draft_type": "scene",
            "source_draft_id": scene_drafts[0]["draft_id"],
        },
    )
    assert branch.status_code == 409
    assert scenes


def test_phase_3a_migration_is_idempotent(client):
    import asyncio

    mongo = MongoClient(app_config.mongodb_url)
    db_name = app_config.database_name
    mongo.close()

    async def run_twice():
        from motor.motor_asyncio import AsyncIOMotorClient

        async_client = AsyncIOMotorClient(app_config.mongodb_url)
        db = async_client[db_name]
        first = await migrate_phase_3a(db)
        second = await migrate_phase_3a(db)
        indexes = {
            name: {item["name"] for item in await db[name].list_indexes().to_list(length=100)}
            for name in (
                "editorial_reports",
                "revision_branches",
                "revision_versions",
                "editorial_scores",
            )
        }
        async_client.close()
        return first, second, indexes

    first, second, indexes = asyncio.run(run_twice())
    assert first["indexes_installed"] is True
    assert second["editorial_reports_normalized"] == 0
    assert "editorial_reports_project_subject" in indexes["editorial_reports"]
    assert "revision_versions_branch_version" in indexes["revision_versions"]
    assert "editorial_scores_project_type" in indexes["editorial_scores"]
