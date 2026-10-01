import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient
from app.core.config import settings as app_config

def test_regression_settings_invalid_negative_budget(client: TestClient):
    """Verify that negative budget values are rejected with 400 Bad Request."""
    response = client.put("/api/settings/execution", json={
        "max_cycle_cost_usd": -1.0,
    })
    assert response.status_code == 400
    assert "cannot be negative" in response.json()["detail"]

def test_regression_settings_zero_budget_skip_validation(client: TestClient):
    """Verify that setting cycle cost to 0.0 persists and is accepted (meaning zero budget, skip all)."""
    response = client.put("/api/settings/execution", json={
        "max_cycle_cost_usd": 0.0,
    })
    assert response.status_code == 200
    data = response.json()
    assert float(data["max_cycle_cost_usd"]) == 0.0

def test_regression_mongo_indexes_exist():
    """Verify that all database indexes specified in migrations are properly created on connection."""
    client = MongoClient(app_config.mongodb_url)
    db = client[app_config.database_name]
    
    # Check chapter_intelligence index
    chapter_intel_indexes = db.chapter_intelligence.index_information()
    assert "chapter_intelligence_project_id" in chapter_intel_indexes
    assert chapter_intel_indexes["chapter_intelligence_project_id"]["unique"] is True
    
    # Check story_audit_reports index
    audit_indexes = db.story_audit_reports.index_information()
    assert "story_audits_project_created" in audit_indexes
    
    # Check change_impacts index
    change_indexes = db.change_impacts.index_information()
    assert "change_impacts_project_status" in change_indexes
    assert "change_impacts_project_id" in change_indexes
    assert change_indexes["change_impacts_project_id"]["unique"] is True
    
    client.close()
