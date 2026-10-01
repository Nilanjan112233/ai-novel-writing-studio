import time
import zipfile
from datetime import datetime
from pathlib import Path

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config
from app.services.application_knowledge_service import application_knowledge_service


def _db():
    return MongoClient(app_config.mongodb_url)[app_config.database_name]


def _project(client, title: str):
    response = client.post("/api/projects", json={
        "title": f"{title} {time.time_ns()}",
        "idea_dump": "A cartographer discovers that erased roads remember their travelers.",
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_recoverable_project_lifecycle_and_guarded_purge(client):
    project = _project(client, "Lifecycle")
    project_id = project["id"]

    trashed = client.post(f"/api/projects/{project_id}/trash")
    assert trashed.status_code == 200
    assert trashed.json()["recoverable"] is True
    assert client.get(f"/api/projects/{project_id}").status_code == 404

    all_projects = client.get(
        "/api/projects?include_archived=true&include_trashed=true"
    ).json()
    assert next(item for item in all_projects if item["id"] == project_id)["status"] == "trashed"

    restored = client.post(f"/api/projects/{project_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["status"] == "draft"

    assert client.post(f"/api/projects/{project_id}/trash").status_code == 200
    mismatch = client.request(
        "DELETE",
        f"/api/projects/{project_id}/purge",
        json={"confirmation_title": "wrong title"},
    )
    assert mismatch.status_code == 400
    purged = client.request(
        "DELETE",
        f"/api/projects/{project_id}/purge",
        json={"confirmation_title": project["title"]},
    )
    assert purged.status_code == 200
    assert purged.json()["recoverable"] is False


def test_application_assistant_knows_publication_and_project_lifecycle():
    publication = application_knowledge_service.answer("How do I publish?")
    assert publication["surface"]["surface_id"] == "manuscript"
    assert "DOCX" in publication["answer"]
    lifecycle = application_knowledge_service.answer("How do I restore a deleted project?")
    assert "Trash" in lifecycle["answer"]


def test_workspace_context_reads_current_contracts_and_reports_no_fake_health(client):
    project = _project(client, "Workspace Context")
    project_id = project["id"]
    pid = ObjectId(project_id)
    db = _db()
    db.chapter_plans.insert_one({
        "project_id": pid,
        "chapter_plan_id": "chapter-1",
        "chapter_number": 1,
        "title": "The Remembering Road",
    })
    db.scene_plans.insert_one({
        "project_id": pid,
        "scene_id": "scene-1",
        "chapter_plan_id": "chapter-1",
        "scene_number": 1,
        "title": "A Map Changes",
    })
    # Legacy installations wrote paragraph ownership as a string.
    db.scene_paragraphs.insert_one({
        "project_id": project_id,
        "scene_id": "scene-1",
        "paragraph_id": "paragraph-1",
        "approval_state": "draft",
        "updated_at": datetime.utcnow(),
    })
    db.canon_proposals.insert_one({
        "project_id": pid,
        "proposal_id": "proposal-1",
        "status": "pending",
    })
    db.client.close()

    response = client.get(f"/api/projects/{project_id}/workspace-context")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["active_scene"]["scene_id"] == "scene-1"
    assert data["active_chapter"]["chapter_plan_id"] == "chapter-1"
    assert data["pending_approvals"] == {"paragraphs": 1, "canon": 1}
    assert data["story_health"]["score"] is None
    assert data["story_health"]["status"] == "not_analyzed"


def test_cached_analysis_does_not_create_fake_history(client):
    project = _project(client, "Cache History")
    project_id = project["id"]
    first = client.post(
        f"/api/projects/{project_id}/narrative-analysis", json={"force": True}
    )
    assert first.status_code == 200
    db = _db()
    before = db.narrative_analysis_history.count_documents(
        {"project_id": ObjectId(project_id)}
    )
    db.client.close()
    cached = client.post(f"/api/projects/{project_id}/narrative-analysis", json={})
    assert cached.status_code == 200
    assert cached.json()["snapshot"]["stats"]["cache_hit"] is True
    db = _db()
    after = db.narrative_analysis_history.count_documents(
        {"project_id": ObjectId(project_id)}
    )
    db.client.close()
    assert after == before


def test_companion_feed_marks_active_messages_read(client):
    project = _project(client, "Companion Read")
    project_id = project["id"]
    feed = client.get(f"/api/projects/{project_id}/workspace-companion")
    assert feed.status_code == 200
    assert any(not item["read"] for item in feed.json()["messages"])
    marked = client.post(f"/api/projects/{project_id}/workspace-companion/read")
    assert marked.status_code == 200
    assert marked.json()["updated"] >= 1
    db = _db()
    assert db.workspace_companion_messages.count_documents({
        "project_id": ObjectId(project_id),
        "active": True,
        "read": {"$ne": True},
    }) == 0
    db.client.close()
    refreshed = client.get(f"/api/projects/{project_id}/workspace-companion")
    assert refreshed.status_code == 200
    assert refreshed.json()["messages"]
    assert all(item["read"] for item in refreshed.json()["messages"])


def test_governed_publication_export_contains_all_formats(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_config, "publication_export_directory", str(tmp_path))
    project = _project(client, "Publication")
    project_id = project["id"]
    pid = ObjectId(project_id)
    manuscript_id = "manuscript-approved"
    version_id = "version-approved"
    db = _db()
    db.manuscripts.insert_one({
        "project_id": pid,
        "manuscript_id": manuscript_id,
        "title": "The Remembering Roads",
        "status": "approved",
        "active": True,
        "current_version_id": version_id,
        "version": 1,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })
    db.manuscript_versions.insert_one({
        "project_id": pid,
        "manuscript_id": manuscript_id,
        "version_id": version_id,
        "version_number": 1,
        "validation_result": "PASS",
        "chapter_count": 2,
        "source_chapters": [
            {"chapter_number": 1, "title": "The Missing Road", "text": "Mara unfolded the map."},
            {"chapter_number": 2, "title": "The Road Remembers", "text": "Ink moved beneath her hand."},
        ],
    })
    db.client.close()

    preflight = client.get(
        f"/api/projects/{project_id}/manuscripts/{manuscript_id}/publication-preflight"
    )
    assert preflight.status_code == 200
    assert preflight.json()["ready"] is True
    exported = client.post(
        f"/api/projects/{project_id}/manuscripts/{manuscript_id}/publication-exports"
    )
    assert exported.status_code == 200, exported.text
    manifest = exported.json()
    assert {"markdown", "text", "html", "docx", "epub", "pdf", "package"} <= set(manifest["artifacts"])
    package = client.get(
        f"/api/projects/{project_id}/publication-exports/{manifest['export_id']}/package"
    )
    assert package.status_code == 200
    package_path = Path(tmp_path) / "downloaded.zip"
    package_path.write_bytes(package.content)
    with zipfile.ZipFile(package_path) as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert any(name.endswith(".docx") for name in names)
        assert any(name.endswith(".epub") for name in names)
        assert any(name.endswith(".pdf") for name in names)
