import pytest
from fastapi.testclient import TestClient
from bson import ObjectId


def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_create_project(client: TestClient, sample_project):
    """Test creating a new project."""
    response = client.post("/api/projects", json=sample_project)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == sample_project["title"]
    assert data["premise"] == sample_project["premise"]
    assert data["genre"] == sample_project["genre"]
    assert data["tone"] == sample_project["tone"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_get_projects(client: TestClient, sample_project):
    """Test getting all projects."""
    # First create a project
    create_response = client.post("/api/projects", json=sample_project)
    assert create_response.status_code == 200
    
    # Then get all projects
    response = client.get("/api/projects")
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    assert len(projects) > 0


def test_get_project(client: TestClient, sample_project):
    """Test getting a specific project."""
    # Create a project first
    create_response = client.post("/api/projects", json=sample_project)
    assert create_response.status_code == 200
    project_id = create_response.json()["id"]
    
    # Get the project
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["title"] == sample_project["title"]


def test_update_project(client: TestClient, sample_project):
    """Test updating a project."""
    # Create a project first
    create_response = client.post("/api/projects", json=sample_project)
    assert create_response.status_code == 200
    project_id = create_response.json()["id"]
    
    # Update the project
    update_data = {"title": "Updated Title", "genre": "Science Fiction"}
    response = client.put(f"/api/projects/{project_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["genre"] == "Science Fiction"


def test_delete_project(client: TestClient, sample_project):
    """Test deleting a project."""
    # Create a project first
    create_response = client.post("/api/projects", json=sample_project)
    assert create_response.status_code == 200
    project_id = create_response.json()["id"]
    
    # Delete the project
    response = client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Project deleted"
    
    # Verify it's deleted
    get_response = client.get(f"/api/projects/{project_id}")
    assert get_response.status_code == 404


def test_run_workflow(client: TestClient, sample_project):
    """Test running a workflow for a project."""
    # Create a project first
    create_response = client.post("/api/projects", json=sample_project)
    assert create_response.status_code == 200
    project_id = create_response.json()["id"]
    
    # Run the workflow
    response = client.post(f"/api/projects/{project_id}/run")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "running"
    assert data["project_id"] == project_id


def test_get_runs(client: TestClient, sample_project):
    """Test getting workflow runs for a project."""
    # Create a project first
    create_response = client.post("/api/projects", json=sample_project)
    assert create_response.status_code == 200
    project_id = create_response.json()["id"]
    
    # Run the workflow
    run_response = client.post(f"/api/projects/{project_id}/run")
    assert run_response.status_code == 200
    
    # Get runs
    response = client.get(f"/api/projects/{project_id}/runs")
    assert response.status_code == 200
    runs = response.json()
    assert isinstance(runs, list)
    assert len(runs) > 0


def test_submit_answer(client: TestClient, sample_project):
    """Test submitting an answer to a question."""
    # Create a project first
    create_response = client.post("/api/projects", json=sample_project)
    assert create_response.status_code == 200
    project_id = create_response.json()["id"]
    
    # Submit an answer (this will fail if question doesn't exist, but we test the endpoint)
    answer_data = {"question_id": str(ObjectId()), "answer": "Test answer"}
    response = client.post(f"/api/projects/{project_id}/answers", json=answer_data)
    # May return 404 if question doesn't exist, but endpoint should be reachable
    assert response.status_code in [200, 404]


def test_get_outline(client: TestClient, sample_project):
    """Test getting the outline for a project."""
    # Create a project first
    create_response = client.post("/api/projects", json=sample_project)
    assert create_response.status_code == 200
    project_id = create_response.json()["id"]
    
    # Get outline (may return 404 if not generated yet)
    response = client.get(f"/api/projects/{project_id}/outline")
    assert response.status_code in [200, 404]


def test_get_questions(client: TestClient, sample_project):
    """Test getting questions for a project."""
    # Create a project first
    create_response = client.post("/api/projects", json=sample_project)
    assert create_response.status_code == 200
    project_id = create_response.json()["id"]
    
    # Get questions
    response = client.get(f"/api/projects/{project_id}/questions")
    assert response.status_code == 200
    questions = response.json()
    assert isinstance(questions, list)


def test_invalid_project_id(client: TestClient):
    """Test handling of invalid project IDs."""
    response = client.get("/api/projects/invalid-id")
    assert response.status_code == 400


def test_nonexistent_project(client: TestClient):
    """Test handling of nonexistent project."""
    fake_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but doesn't exist
    response = client.get(f"/api/projects/{fake_id}")
    assert response.status_code == 404
