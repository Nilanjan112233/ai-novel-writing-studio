import time
from datetime import datetime

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config
from tests.test_drafting_v2 import post
from tests.test_editorial_v3 import approved_scene_and_chapter


def _mongo():
    return MongoClient(app_config.mongodb_url)[app_config.database_name]


def _project(client, title):
    return post(
        client,
        "/api/projects",
        {
            "title": f"{title} {time.time_ns()}",
            "premise": "A city remembers every promise except the one that founded it.",
            "genre": "Literary fantasy",
            "tone": "Uncertain and intimate",
        },
    )


def test_approved_chapter_generates_intelligence_audit_and_impact_preview(client):
    project_id, _, chapter, _, _, approved = approved_scene_and_chapter(client)

    intelligence = client.get(
        f"/api/projects/{project_id}/chapter-intelligence"
    )
    assert intelligence.status_code == 200, intelligence.text
    rows = intelligence.json()
    assert len(rows) == 1
    assert rows[0]["chapter_draft_id"] == approved["draft_id"]
    assert rows[0]["chapter_plan_id"] == chapter["chapter_plan_id"]
    assert rows[0]["important_events"]
    assert "future_obligations" in rows[0]

    other = _project(client, "Isolated Salt Archive")
    assert client.get(
        f"/api/projects/{other['id']}/chapter-intelligence"
    ).json() == []

    impact = post(
        client,
        f"/api/projects/{project_id}/change-impact",
        {
            "change_type": "character_removal",
            "target": {"name": "Ilyra"},
            "proposed_change": {"reason": "Author requested removal"},
        },
    )
    assert impact["total_affected"] > 0
    assert impact["counts"]["chapters"] > 0
    decision = client.put(
        (
            f"/api/projects/{project_id}/change-impacts/"
            f"{impact['impact_id']}/status"
        ),
        json={"status": "rejected"},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "rejected"

    audit = post(
        client,
        f"/api/projects/{project_id}/story-audit",
        {"include_agent": True},
    )
    assert "StoryAuditorAgent" in audit["generated_by"]
    assert audit["agent_finding_count"] == 1
    latest_plan = client.get(
        f"/api/projects/{project_id}/orchestration/latest"
    ).json()
    assert latest_plan["selected_agents"] == ["StoryAuditorAgent"]

    db = _mongo()
    pid = ObjectId(project_id)
    assert db.discussion_messages.count_documents(
        {"project_id": pid, "author": "StoryAuditorAgent"}
    ) == 0
    assert db.agent_memories.count_documents(
        {"project_id": pid, "agent_name": "StoryAuditorAgent"}
    ) == 0
    db.client.close()

    health = client.get(f"/api/projects/{project_id}/story-health")
    assert health.status_code == 200, health.text
    assert health.json()["metrics"]["total_chapters"] == 1


def test_fifty_chapter_memory_health_and_project_isolation(client):
    project_a = _project(client, "The Bell Beneath Winter")
    project_b = _project(client, "The Orchard Beyond Noon")
    pid_a = ObjectId(project_a["id"])
    pid_b = ObjectId(project_b["id"])
    now = datetime.utcnow()
    chapters = []
    for number in range(1, 51):
        obligations = []
        if number == 4:
            obligations.append("Return the broken bell to Mara before the thaw")
        if number == 9:
            obligations.append("Tell Soren who erased the founding oath")
        chapters.append(
            {
                "project_id": pid_a,
                "intelligence_id": f"scale-a-{number}",
                "chapter_plan_id": f"plan-a-{number}",
                "chapter_draft_id": f"draft-a-{number}",
                "chapter_draft_version": 1,
                "chapter_number": number,
                "arc_id": "arc-a-1" if number <= 23 else "arc-a-2",
                "title": f"Chapter {number}",
                "active": True,
                "chapter_summary": (
                    f"Mara misreads the council's silence in chapter {number} "
                    "and chooses a costly partial answer."
                ),
                "important_events": [
                    f"Mara makes irreversible choice {number}",
                    f"The city reveals incomplete truth {number}",
                ],
                "characters_present": ["Mara", "Soren"],
                "character_changes": [
                    {"character": "Mara", "change": f"Doubts certainty {number}"}
                ],
                "knowledge_revealed": [],
                "mysteries_introduced": [],
                "mysteries_advanced": [],
                "mysteries_resolved": [],
                "foreshadowing_introduced": [],
                "foreshadowing_advanced": [],
                "foreshadowing_resolved": [],
                "artifact_usage": [],
                "relationship_changes": [],
                "timeline_impact": [],
                "canon_impact": [],
                "unresolved_questions": obligations,
                "future_obligations": obligations,
                "quality_findings": [],
                "word_count": 1700,
                "created_at": now,
                "updated_at": now,
            }
        )
    db = _mongo()
    db.chapter_intelligence.insert_many(chapters)
    db.chapter_intelligence.insert_one(
        {
            **chapters[0],
            "_id": ObjectId(),
            "project_id": pid_b,
            "intelligence_id": "scale-b-1",
            "chapter_plan_id": "plan-b-1",
            "chapter_draft_id": "draft-b-1",
            "chapter_number": 1,
            "chapter_summary": "The orchard project has unrelated memory.",
            "characters_present": ["Nia"],
            "future_obligations": ["Harvest the blue fruit"],
        }
    )
    db.story_arcs.insert_many(
        [
            {
                "project_id": pid_a,
                "arc_id": "arc-a-1",
                "title": "The Winter Bell",
                "order": 1,
                "development_status": "completed",
            },
            {
                "project_id": pid_a,
                "arc_id": "arc-a-2",
                "title": "The Erased Oath",
                "order": 2,
                "development_status": "approved",
            },
        ]
    )
    db.client.close()

    memory = client.get(
        f"/api/projects/{project_a['id']}/chapter-intelligence/memory",
        params={"recent_limit": 10, "obligation_limit": 10},
    )
    assert memory.status_code == 200, memory.text
    packet = memory.json()
    assert 45 in [item["chapter_number"] for item in packet["recent"]]
    assert 50 in [item["chapter_number"] for item in packet["recent"]]
    long_range = {
        item["chapter_number"]: item["future_obligations"]
        for item in packet["long_range_obligations"]
    }
    assert 4 in long_range
    assert 9 in long_range

    health = client.get(
        f"/api/projects/{project_a['id']}/story-health"
    ).json()
    assert health["metrics"]["total_chapters"] == 50
    assert health["metrics"]["total_words"] == 85000
    assert health["metrics"]["unresolved_promises"] == 2

    audit = post(
        client,
        f"/api/projects/{project_a['id']}/story-audit",
        {"include_agent": False},
    )
    categories = {item["category"] for item in audit["findings"]}
    assert "unresolved_promise" in categories
    assert "repetitive_chapter_structure" in categories

    impact = post(
        client,
        f"/api/projects/{project_a['id']}/change-impact",
        {
            "change_type": "character_removal",
            "target": {"name": "Mara"},
        },
    )
    assert impact["counts"]["chapters"] == 50
    assert all(
        item["id"] != "scale-b-1"
        for item in impact["affected"]["chapters"]
    )
    other_rows = client.get(
        f"/api/projects/{project_b['id']}/chapter-intelligence"
    ).json()
    assert len(other_rows) == 1
    assert other_rows[0]["characters_present"] == ["Nia"]
