import time
from datetime import datetime

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config
from app.services.story_auditor_service import AUDIT_CONTEXT_BUDGET, _compact_audit_context


def _db():
    return MongoClient(app_config.mongodb_url)[app_config.database_name]


def _project(client, title="Phase 6 Intelligence"):
    response = client.post("/api/projects", json={
        "title": f"{title} {time.time_ns()}",
        "premise": "A courier must repay a promise before the calendar repeats.",
        "genre": "Fantasy",
        "tone": "Tense",
    })
    assert response.status_code in {200, 201}, response.text
    return response.json()


def _chapter(pid, number, *, obligation=None):
    return {
        "project_id": pid,
        "intelligence_id": f"intelligence-{number}",
        "chapter_plan_id": f"plan-{number}",
        "chapter_draft_id": f"draft-{number}",
        "chapter_draft_version": 1,
        "chapter_number": number,
        "title": f"Chapter {number}",
        "chapter_summary": f"Mara crosses district {number} and weighs the old promise.",
        "important_events": [f"Crossing {number}"],
        "characters_present": ["Mara"],
        "character_changes": [],
        "future_obligations": [obligation] if obligation else [],
        "mysteries_resolved": [],
        "foreshadowing_resolved": [],
        "word_count": 1600,
        "active": True,
        "updated_at": datetime.utcnow(),
    }


def test_story_auditor_context_is_bounded_for_large_novels():
    findings = [
        {
            "finding_id": f"finding-{number}",
            "category": "continuity",
            "severity": "high" if number < 20 else "medium",
            "message": "Inconsistent event evidence " + ("x" * 1200),
            "evidence": ["source " + ("y" * 900)] * 8,
            "affected_chapters": list(range(1, 80)),
            "affected_scenes": [f"scene-{index}" for index in range(80)],
            "recommended_actions": ["Review the sequence " + ("z" * 600)] * 5,
        }
        for number in range(500)
    ]
    chapter_memory = {
        "recent": [
            {
                "chapter_number": number,
                "title": f"Chapter {number}",
                "chapter_summary": "summary " + ("s" * 1800),
                "important_events": ["event " + ("e" * 600)] * 10,
                "characters_present": [f"Character {index}" for index in range(30)],
                "unresolved_questions": ["question " + ("q" * 500)] * 10,
                "future_obligations": ["obligation " + ("o" * 500)] * 10,
            }
            for number in range(1, 501)
        ],
        "long_range_obligations": [],
    }
    context = _compact_audit_context(
        {
            "snapshot": {
                "analysis_id": "analysis-large",
                "graph_version": 1,
                "scores": {"overall": 72},
                "finding_counts": {"continuity": 500},
                "stats": {"nodes": 5000, "edges": 7000},
            }
        },
        chapter_memory,
        findings,
        [],
    )
    import json

    assert len(json.dumps(context, default=str, ensure_ascii=True)) <= AUDIT_CONTEXT_BUDGET
    assert context["finding_coverage"]["available"] == 500
    assert context["finding_coverage"]["included"] >= 4
    assert context["deterministic_findings"][0]["severity"] == "high"


def test_unified_graph_evidence_domains_and_incremental_recomputation(client):
    project = _project(client)
    pid = ObjectId(project["id"])
    db = _db()
    db.chapter_intelligence.insert_many([
        _chapter(pid, number, obligation="Return the brass key" if number == 1 else None)
        for number in range(1, 13)
    ])
    db.character_bibles.insert_one({
        "project_id": pid, "name": "Soren", "current_status": "active",
        "personality": ["patient"], "updated_at": datetime.utcnow(),
    })
    db.timeline_entries.insert_many([
        {"project_id": pid, "entry_id": "event-1", "event": "Departure", "order": 1, "dependencies": []},
        {"project_id": pid, "entry_id": "event-3", "event": "Arrival", "order": 3, "dependencies": ["missing-event"]},
    ])
    db.canon_registry.insert_many([
        {"project_id": pid, "canon_id": "canon-a", "active": True, "subject": "Mara", "field": "age", "value": 20, "source_collection": "chapter_drafts", "source_id": "draft-1"},
        {"project_id": pid, "canon_id": "canon-b", "active": True, "subject": "Mara", "field": "age", "value": 30, "source_collection": "chapter_drafts", "source_id": "draft-12"},
    ])
    db.canon_conflicts.insert_one({
        "project_id": pid, "conflict_id": "conflict-1", "conflict_type": "character_authority_conflict",
        "severity": "high", "status": "open", "message": "Mara has two active ages.",
        "canon_ids": ["canon-a", "canon-b"], "evidence": [20, 30],
    })
    db.client.close()

    first = client.post(f"/api/projects/{project['id']}/narrative-analysis", json={}).json()
    assert first["snapshot"]["stats"]["recomputed_nodes"] >= 17
    assert first["snapshot"]["scores"]["canon"] < 100
    assert first["snapshot"]["scores"]["timeline"] < 100
    assert first["snapshot"]["scores"]["plot"] < 100
    assert {item["domain"] for item in first["findings"]} >= {"canon", "timeline", "plot", "character"}
    for finding in first["findings"]:
        assert finding["severity"]
        assert finding["explanation"]
        assert isinstance(finding["affected_chapters"], list)
        assert isinstance(finding["affected_scenes"], list)
        assert finding["recommended_actions"]
        assert finding["evidence"]

    second = client.post(f"/api/projects/{project['id']}/narrative-analysis", json={}).json()
    assert second["snapshot"]["stats"]["recomputed_nodes"] == 0
    assert second["snapshot"]["stats"]["reused_nodes"] == second["snapshot"]["stats"]["nodes"]

    db = _db()
    db.chapter_intelligence.update_one(
        {"project_id": pid, "intelligence_id": "intelligence-12"},
        {"$set": {"chapter_summary": "Mara returns the key.", "updated_at": datetime.utcnow()}},
    )
    db.client.close()
    third = client.post(f"/api/projects/{project['id']}/narrative-analysis", json={}).json()
    assert third["snapshot"]["stats"]["recomputed_nodes"] == 1

    domain = client.get(f"/api/projects/{project['id']}/narrative-intelligence/canon").json()
    assert domain["score"] < 100
    assert domain["findings"][0]["evidence"][0]["source"] == "chapter_drafts:draft-1"
    health = client.get(f"/api/projects/{project['id']}/story-health").json()
    assert health["story_health_score"] == health["dimension_scores"]["overall"]
    assert health["findings"]

    finding_id = first["findings"][0]["finding_id"]
    acknowledged = client.put(
        f"/api/projects/{project['id']}/narrative-findings/{finding_id}/status",
        json={"status": "acknowledged"},
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "acknowledged"
    client.post(f"/api/projects/{project['id']}/narrative-analysis", json={})
    current = client.get(f"/api/projects/{project['id']}/narrative-intelligence").json()
    assert next(item for item in current["findings"] if item["finding_id"] == finding_id)["status"] == "acknowledged"


def test_five_hundred_chapter_analysis_cache_benchmark(client):
    project = _project(client, "Five Hundred Chapters")
    pid = ObjectId(project["id"])
    db = _db()
    db.chapter_intelligence.insert_many([_chapter(pid, number) for number in range(1, 501)])
    db.client.close()

    started = time.perf_counter()
    first = client.post(f"/api/projects/{project['id']}/narrative-analysis", json={"force": True})
    elapsed = time.perf_counter() - started
    assert first.status_code == 200, first.text
    stats = first.json()["snapshot"]["stats"]
    assert stats["nodes"] == 500
    assert stats["recomputed_nodes"] == 500
    assert elapsed < 15

    cached = client.post(f"/api/projects/{project['id']}/narrative-analysis", json={})
    assert cached.status_code == 200
    cached_stats = cached.json()["snapshot"]["stats"]
    assert cached_stats["recomputed_nodes"] == 0
    assert cached_stats["reused_nodes"] == 500
    assert cached_stats["cache_hit"] is True


def test_phase6_migration_and_background_analysis_job(client):
    project = _project(client, "Background Analysis")
    db = _db()
    settings = db.app_settings.find_one({"_id": "global_settings"})
    assert settings["migrations"]["phase_6_version"] == 1
    assert "narrative_node_identity" in db.narrative_nodes.index_information()
    assert "narrative_finding_identity" in db.narrative_findings.index_information()
    db.client.close()

    response = client.post(
        f"/api/projects/{project['id']}/narrative-analysis",
        json={"background": True},
    )
    assert response.status_code == 200, response.text
    job = response.json()
    status = client.get(
        f"/api/projects/{project['id']}/narrative-analysis/jobs/{job['job_id']}"
    )
    assert status.status_code == 200, status.text
    assert status.json()["status"] == "complete"
    assert status.json()["analysis_id"]
