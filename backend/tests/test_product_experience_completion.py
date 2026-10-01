import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings as app_config


def _db():
    return MongoClient(app_config.mongodb_url)[app_config.database_name]


def _project(client, title="Product Experience"):
    response = client.post("/api/projects", json={
        "title": f"{title} {time.time_ns()}",
        "premise": "An heir must unite seven kingdoms before a vanished moon returns.",
        "genre": "Epic fantasy",
        "tone": "Hopeful",
        "themes": ["belonging"],
    })
    assert response.status_code in {200, 201}, response.text
    return response.json()


def test_shared_context_is_structured_deduplicated_and_proposal_governed(client):
    project = _project(client, "Shared Context")
    endpoint = f"/api/projects/{project['id']}/shared-narrative-context"
    payload = {
        "content": "The empire has seven kingdoms.",
        "domain": "world",
        "subject": "The empire",
        "field": "kingdom_count",
        "value": 7,
        "confidence": .99,
        "source_type": "explicit_author_input",
    }
    first = client.post(endpoint, json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["persisted"] is True
    assert first.json()["canon_proposal_id"]
    second = client.post(endpoint, json=payload)
    assert second.status_code == 200
    assert second.json()["deduplicated"] is True

    transient = client.post(endpoint, json={"content": "Open Chapter 12"})
    assert transient.status_code == 200
    assert transient.json()["persisted"] is False
    rows = client.get(endpoint).json()
    assert len(rows) == 1
    assert {"story_bible", "world", "canon"} <= set(rows[0]["routed_subsystems"])
    assert rows[0]["provenance"][0]["source_type"] == "explicit_author_input"


def test_critique_routes_findings_into_shared_story_health(client):
    project = _project(client, "Critique")
    pid = ObjectId(project["id"])
    db = _db()
    db.character_bibles.insert_one({
        "project_id": pid, "name": "Asha", "role": "protagonist", "current_status": "active",
        "motivations": [], "updated_at": datetime.utcnow(),
    })
    db.chapter_plans.insert_many([
        {"project_id": pid, "chapter_plan_id": f"chapter-{number}", "chapter_number": number,
         "title": f"Chapter {number}", "purpose": "Asha waits for news", "conflict": "", "updated_at": datetime.utcnow()}
        for number in range(1, 4)
    ])
    db.client.close()

    response = client.post(f"/api/projects/{project['id']}/narrative-critique/refresh", json={"include_latest_agent_audit": False})
    assert response.status_code == 200, response.text
    result = response.json()
    critique = [item for item in result["findings"] if item.get("finding_type") == "critique"]
    assert {item["category"] for item in critique} >= {"weak_motivation", "missing_conflict_escalation"}
    for item in critique:
        assert item["responsible_subsystem"]
        assert item["suggested_improvement"]
        assert item["evidence"]
        assert item["confidence"] > 0
    assert result["author_control"].startswith("Improvements are proposals only")
    health = client.get(f"/api/projects/{project['id']}/story-health").json()
    assert any(item.get("finding_type") == "critique" for item in health["findings"])


def test_completeness_milestones_guide_canon_explorer_and_companion(client):
    project = _project(client, "Production Pipeline")
    pid = ObjectId(project["id"])
    db = _db()
    now = datetime.utcnow()
    db.story_visions.insert_one({
        "project_id": pid, "premise": project["premise"], "genre": project["genre"],
        "themes": ["belonging"], "narrative_goals": ["Unite the kingdoms"], "updated_at": now,
    })
    db.character_bibles.insert_one({
        "project_id": pid, "name": "Asha", "role": "protagonist", "current_status": "active",
        "motivations": ["Unite the kingdoms"], "backstory": "Raised beyond the border", "updated_at": now,
    })
    db.world_bibles.insert_one({
        "project_id": pid, "locations": [{"name": "Sevenfold Empire"}],
        "world_rules": ["No crown may command two kingdoms"], "updated_at": now,
    })
    db.power_systems.insert_one({"project_id": pid, "not_applicable": True, "updated_at": now})
    db.canon_registry.insert_one({
        "project_id": pid, "canon_id": "canon-seven", "canon_type": "world", "active": True,
        "subject": "Sevenfold Empire", "field": "kingdom_count", "value": 7, "fact": "The empire has seven kingdoms.",
        "source_collection": "world_bibles", "source_id": "world-main", "source_version": 1,
        "authority_level": "approved", "evidence": ["World bible"], "updated_at": now, "created_at": now,
    })
    db.client.close()

    completeness = client.get(f"/api/projects/{project['id']}/narrative-completeness")
    assert completeness.status_code == 200, completeness.text
    data = completeness.json()
    assert set(data["dimensions"]) == {"story", "character", "world", "power", "relationship", "mystery", "timeline", "canon"}
    assert [item["label"] for item in data["milestones"]] == [
        "Concept Complete", "World Ready", "Draft Ready", "Revision Ready", "Publication Ready",
    ]
    assert all("criteria" in item and "blockers" in item for item in data["milestones"])

    guide = client.get(f"/api/projects/{project['id']}/novel-creation-guide")
    assert guide.status_code == 200, guide.text
    assert len(guide.json()["steps"]) == 16
    assert {step["label"] for step in guide.json()["steps"]} >= {"Genre", "Theme"}
    assert guide.json()["jump_freely"] is True
    assert all(step["why_it_matters"] and step["ai_systems"] for step in guide.json()["steps"])

    explorer = client.get(f"/api/projects/{project['id']}/canon-explorer?search=seven")
    assert explorer.status_code == 200, explorer.text
    assert explorer.json()["authority"] == "canon_registry"
    assert explorer.json()["records"][0]["canon_id"] == "canon-seven"
    detail = client.get(f"/api/projects/{project['id']}/canon-explorer/canon-seven")
    assert detail.status_code == 200, detail.text
    assert detail.json()["source"]["collection"] == "world_bibles"
    proposal = client.post(
        f"/api/projects/{project['id']}/canon-explorer/canon-seven/propose-edit",
        json={"value": 8, "evidence": ["Author requests an eighth kingdom"]},
    )
    assert proposal.status_code == 200, proposal.text
    assert proposal.json()["applied"] is False
    assert proposal.json()["requires_author_approval"] is True
    companion = client.get(f"/api/projects/{project['id']}/workspace-companion")
    assert companion.status_code == 200, companion.text
    assert companion.json()["messages"]
    assert any(item["target"] == "canon-queue" for item in companion.json()["messages"])
    assert companion.json()["behavior"]["respects_reduced_motion"] is True


def test_product_completion_migration_indexes(client):
    project = _project(client, "Migration")
    db = _db()
    settings = db.app_settings.find_one({"_id": "global_settings"})
    assert settings["migrations"]["product_completion_version"] == 1
    assert "shared_context_identity" in db.shared_narrative_context.index_information()
    assert "narrative_completeness_current" in db.narrative_completeness_snapshots.index_information()
    assert "workspace_companion_identity" in db.workspace_companion_messages.index_information()
    pid = ObjectId(project["id"])
    db.shared_narrative_context.insert_one({"project_id": pid, "context_id": "cleanup", "dedupe_fingerprint": "cleanup"})
    db.client.close()
    deleted = client.delete(f"/api/projects/{project['id']}")
    assert deleted.status_code == 200
    db = _db()
    assert db.shared_narrative_context.count_documents({"project_id": pid}) == 0
    db.client.close()


def test_concurrent_analysis_keeps_graph_edges_unique(client):
    project = _project(client, "Concurrent Narrative Graph")
    pid = ObjectId(project["id"])
    db = _db()
    now = datetime.utcnow()
    db.character_bibles.insert_one({
        "project_id": pid,
        "character_id": "character-asha",
        "name": "Asha",
        "role": "protagonist",
        "current_status": "active",
        "updated_at": now,
    })
    db.chapter_intelligence.insert_one({
        "project_id": pid,
        "intelligence_id": "chapter-one-intelligence",
        "chapter_number": 1,
        "title": "Asha Returns",
        "chapter_summary": "Asha returns to the Sevenfold Empire.",
        "characters_present": ["Asha"],
        "active": True,
        "updated_at": now,
    })
    db.client.close()

    endpoint = f"/api/projects/{project['id']}/narrative-analysis"

    def run_analysis(_):
        return client.post(endpoint, json={"force": True})

    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(run_analysis, range(4)))

    assert all(response.status_code == 200 for response in responses), [
        response.text for response in responses
    ]
    db = _db()
    edges = list(db.narrative_edges.find({"project_id": pid}))
    assert edges
    assert len(edges) == len({edge["edge_id"] for edge in edges})
    db.client.close()


def test_product_experience_large_novel_benchmark(client):
    project = _project(client, "Five Hundred Chapter Experience")
    pid = ObjectId(project["id"])
    db = _db()
    now = datetime.utcnow()
    db.chapter_intelligence.insert_many([
        {
            "project_id": pid, "intelligence_id": f"intelligence-{number}",
            "chapter_plan_id": f"plan-{number}", "chapter_draft_id": f"draft-{number}",
            "chapter_draft_version": 1, "chapter_number": number, "title": f"Chapter {number}",
            "chapter_summary": f"The expedition crosses district {number} and pays a new cost.",
            "important_events": [f"Crossing {number}"], "characters_present": ["Asha"],
            "future_obligations": [], "mysteries_resolved": [], "foreshadowing_resolved": [],
            "word_count": 1600, "active": True, "updated_at": now,
        }
        for number in range(1, 501)
    ])
    db.chapter_plans.insert_many([
        {"project_id": pid, "chapter_plan_id": f"plan-{number}", "chapter_number": number,
         "title": f"Chapter {number}", "purpose": f"Escalation step {number}",
         "conflict": f"Opposition increases at district {number}", "updated_at": now}
        for number in range(1, 501)
    ])
    db.client.close()

    started = time.perf_counter()
    analysis = client.post(f"/api/projects/{project['id']}/narrative-analysis", json={"force": True})
    completeness = client.get(f"/api/projects/{project['id']}/narrative-completeness")
    critique = client.post(f"/api/projects/{project['id']}/narrative-critique/refresh", json={"include_latest_agent_audit": False})
    companion = client.get(f"/api/projects/{project['id']}/workspace-companion")
    uncached_seconds = time.perf_counter() - started
    assert all(response.status_code == 200 for response in (analysis, completeness, critique, companion))
    assert analysis.json()["snapshot"]["stats"]["nodes"] >= 500

    cached_started = time.perf_counter()
    cached = client.post(f"/api/projects/{project['id']}/narrative-analysis", json={})
    cached_seconds = time.perf_counter() - cached_started
    assert cached.status_code == 200
    assert cached.json()["snapshot"]["stats"]["recomputed_nodes"] == 0
    assert cached.json()["snapshot"]["stats"]["cache_hit"] is True
    assert uncached_seconds < 30
    assert cached_seconds < 5
    print(f"\nPRODUCT_EXPERIENCE_BENCHMARK chapters=500 uncached_seconds={uncached_seconds:.3f} cached_analysis_seconds={cached_seconds:.3f}")
