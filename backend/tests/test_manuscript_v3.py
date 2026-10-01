import asyncio
import hashlib
import time

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config
from app.migrations.phase_3b import migrate_phase_3b
from tests.test_editorial_v3 import approved_scene_and_chapter


def post(client, path, payload=None):
    response = client.post(path, json=payload or {})
    assert response.status_code == 200, response.text
    return response.json()


def manuscript_fixture(client):
    project_id, arc_id, chapter, scenes, scene_drafts, chapter_draft = (
        approved_scene_and_chapter(client)
    )
    manuscript = post(
        client,
        f"/api/projects/{project_id}/manuscripts",
        {"title": "The Eternal Throne"},
    )
    assembled = post(
        client,
        f"/api/projects/{project_id}/manuscripts/{manuscript['manuscript_id']}/assemble",
        {"chapter_draft_ids": [chapter_draft["draft_id"]]},
    )
    return (
        project_id,
        arc_id,
        chapter,
        scenes,
        scene_drafts,
        chapter_draft,
        manuscript,
        assembled,
    )


def test_manuscript_assembly_versions_review_and_manual_approval(client):
    (
        project_id,
        _,
        _,
        _,
        _,
        chapter_draft,
        manuscript,
        assembled,
    ) = manuscript_fixture(client)
    version = assembled["version"]
    assert version["version_number"] == 1
    assert version["validation_result"] in {"PASS", "WARNING"}
    source = version["source_chapters"][0]
    assert source["text"] == chapter_draft["generated_text"]
    assert source["text_sha256"] == hashlib.sha256(
        chapter_draft["generated_text"].encode("utf-8")
    ).hexdigest()

    blocked = client.post(
        f"/api/projects/{project_id}/manuscripts/{manuscript['manuscript_id']}/approve",
        json={},
    )
    assert blocked.status_code == 409
    assert client.put(
        f"/api/projects/{project_id}/manuscripts/{manuscript['manuscript_id']}/status",
        json={"status": "review"},
    ).status_code == 200
    assert client.put(
        f"/api/projects/{project_id}/manuscripts/{manuscript['manuscript_id']}/status",
        json={"status": "validated"},
    ).status_code == 200

    review = post(
        client,
        f"/api/projects/{project_id}/manuscripts/{manuscript['manuscript_id']}/review",
    )
    assert review["generated_by"] == "ManuscriptAgent"
    plan = client.get(
        f"/api/projects/{project_id}/orchestration/latest"
    ).json()
    assert plan["selected_agents"] == ["ManuscriptAgent"]
    approved = post(
        client,
        f"/api/projects/{project_id}/manuscripts/{manuscript['manuscript_id']}/approve",
    )
    assert approved["status"] == "approved"

    mongo = MongoClient(app_config.mongodb_url)
    persisted = mongo[app_config.database_name].chapter_drafts.find_one(
        {
            "project_id": ObjectId(project_id),
            "draft_id": chapter_draft["draft_id"],
        }
    )
    mongo.close()
    assert persisted["generated_text"] == chapter_draft["generated_text"]


def test_manuscript_version_lineage_and_rollback(client):
    (
        project_id,
        _,
        _,
        _,
        _,
        chapter_draft,
        manuscript,
        first,
    ) = manuscript_fixture(client)
    second = post(
        client,
        f"/api/projects/{project_id}/manuscripts/{manuscript['manuscript_id']}/assemble",
        {"chapter_draft_ids": [chapter_draft["draft_id"]]},
    )
    assert second["version"]["version_number"] == 2
    assert second["version"]["parent_version_id"] == first["version"]["version_id"]
    versions = client.get(
        f"/api/projects/{project_id}/manuscripts/{manuscript['manuscript_id']}/versions"
    ).json()
    assert [item["version_number"] for item in versions[:2]] == [2, 1]
    rolled_back = post(
        client,
        (
            f"/api/projects/{project_id}/manuscripts/"
            f"{manuscript['manuscript_id']}/rollback/{first['version']['version_id']}"
        ),
    )
    assert rolled_back["current_version_id"] == first["version"]["version_id"]
    assert rolled_back["status"] == "draft"


def test_typed_canon_conflict_validation_and_review(client):
    (
        project_id,
        _,
        chapter,
        _,
        _,
        _,
        _,
        _,
    ) = manuscript_fixture(client)
    first = post(
        client,
        f"/api/projects/{project_id}/canon/promote",
        {
            "canon_type": "timeline",
            "source_collection": "chapter_plans",
            "source_id": chapter["chapter_plan_id"],
            "subject": "The coronation",
            "field": "chapter",
            "value": 1,
        },
    )
    second = post(
        client,
        f"/api/projects/{project_id}/canon/promote",
        {
            "canon_type": "timeline",
            "source_collection": "chapter_plans",
            "source_id": chapter["chapter_plan_id"],
            "source_version": 2,
            "subject": "The coronation",
            "field": "chapter",
            "value": 7,
        },
    )
    assert first["canon_id"] != second["canon_id"]
    validation = post(client, f"/api/projects/{project_id}/canon/validate")
    assert validation["result"] == "FAIL"
    assert any(
        item["conflict_type"] == "timeline_authority_conflict"
        for item in validation["conflicts"]
    )
    report = post(client, f"/api/projects/{project_id}/canon/review")
    assert report["generated_by"] == "CanonAgent"
    plan = client.get(
        f"/api/projects/{project_id}/orchestration/latest"
    ).json()
    assert plan["selected_agents"] == ["CanonAgent"]
    deactivated = client.put(
        (
            f"/api/projects/{project_id}/canon/registry/"
            f"{second['canon_id']}/active"
        ),
        json={"active": False},
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["active"] is False
    resolved = post(client, f"/api/projects/{project_id}/canon/validate")
    assert resolved["result"] == "PASS"
    legacy = client.get(f"/api/projects/{project_id}/canon").json()
    assert "locked_facts" in legacy


def test_phase_3b_ownership_and_approved_source_guards(client):
    (
        project_id,
        _,
        _,
        _,
        _,
        chapter_draft,
        manuscript,
        _,
    ) = manuscript_fixture(client)
    other = post(
        client,
        "/api/projects",
        {
            "title": f"Other Manuscript Project {time.time_ns()}",
            "premise": "Ownership boundary.",
        },
    )
    cross = client.post(
        f"/api/projects/{other['id']}/manuscripts/{manuscript['manuscript_id']}/assemble",
        json={"chapter_draft_ids": [chapter_draft["draft_id"]]},
    )
    assert cross.status_code == 409

    regenerated = post(
        client,
        f"/api/projects/{project_id}/chapter-drafts/{chapter_draft['draft_id']}/regenerate",
        {"change_reason": "Create an unapproved chapter alternative."},
    )["draft"]
    blocked = client.post(
        f"/api/projects/{project_id}/manuscripts/{manuscript['manuscript_id']}/assemble",
        json={"chapter_draft_ids": [regenerated["draft_id"]]},
    )
    assert blocked.status_code == 409


def test_phase_3b_migration_is_idempotent(client):
    async def run_twice():
        from motor.motor_asyncio import AsyncIOMotorClient

        async_client = AsyncIOMotorClient(app_config.mongodb_url)
        db = async_client[app_config.database_name]
        first = await migrate_phase_3b(db)
        second = await migrate_phase_3b(db)
        indexes = {
            name: {
                item["name"]
                for item in await db[name].list_indexes().to_list(length=100)
            }
            for name in (
                "manuscripts",
                "manuscript_versions",
                "manuscript_reports",
                "canon_registry",
                "canon_conflicts",
            )
        }
        async_client.close()
        return first, second, indexes

    first, second, indexes = asyncio.run(run_twice())
    assert first["indexes_installed"] is True
    assert second["indexes_installed"] is True
    assert "manuscripts_project_version" in indexes["manuscripts"]
    assert (
        "manuscript_versions_manuscript_version"
        in indexes["manuscript_versions"]
    )
    assert "manuscript_reports_subject" in indexes["manuscript_reports"]
    assert "canon_registry_project_type" in indexes["canon_registry"]
    assert "canon_registry_active" in indexes["canon_registry"]
    assert "canon_conflicts_project_status" in indexes["canon_conflicts"]
