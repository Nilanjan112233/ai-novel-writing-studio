from fastapi.testclient import TestClient


def _project(client: TestClient, sample_project: dict) -> str:
    response = client.post("/api/projects", json=sample_project)
    assert response.status_code == 200
    return response.json()["id"]


def test_story_studio_question_is_read_only(client: TestClient, sample_project):
    project_id = _project(client, sample_project)
    response = client.post(
        f"/api/projects/{project_id}/story-studio",
        json={"query": "Why does the protagonist behave this way?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mutation_applied"] is False
    assert body["author_decision_required"] is False
    assert body["intent"]["intent"] == "retrieve_explain"
    jobs = client.get(f"/api/projects/{project_id}/story-studio/jobs")
    assert jobs.status_code == 200
    assert jobs.json()[-1]["status"] == "completed"


def test_story_studio_humanization_request_is_a_protected_revision_not_an_answer(client: TestClient, sample_project):
    from app.services.story_studio_service import StoryStudioService
    from app.services.editorial_service import _humanization_quality_failure

    humanization = StoryStudioService.classify(
        "Make Chapter 1 feel more natural and human-written. Reduce repetitive rhythm.",
        allow_mutations=False,
    )
    explanation = StoryStudioService.classify(
        "Explain why Chapter 1 feels too dramatic.",
        allow_mutations=False,
    )
    assert humanization.intent.value == "modify"
    assert humanization.mutation_class.value == "proposal"
    assert explanation.intent.value == "retrieve_explain"
    assert explanation.mutation_class.value == "none"
    assert _humanization_quality_failure("word " * 1492, "word " * 532)
    assert _humanization_quality_failure("word " * 1492, "word " * 1392) is None


def test_story_studio_ambiguous_change_requires_author_decision(client: TestClient, sample_project):
    project_id = _project(client, sample_project)
    response = client.post(
        f"/api/projects/{project_id}/story-studio",
        json={"query": "Make this character darker"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["author_decision_required"] is True
    assert body["mutation_applied"] is False
    assert "Nothing has been changed" in body["answer"]
    assert body["clarification"]["status"] == "waiting"
    assert "darker" in body["clarification"]["question"]


def test_discovery_word_range_contract_rejects_inverted_range(client: TestClient, sample_project):
    project_id = _project(client, sample_project)
    response = client.post(
        f"/api/projects/{project_id}/discovery-writing",
        json={"instruction": "A courier reaches a locked city gate.", "target_word_min": 3000, "target_word_count": 2000, "target_word_max": 1000},
    )
    assert response.status_code in {409, 422}


def test_discovery_generation_creates_reviewable_draft(client: TestClient, sample_project):
    project_id = _project(client, sample_project)
    response = client.post(
        f"/api/projects/{project_id}/discovery-writing",
        json={"instruction": "A courier reaches a locked city gate.", "target_word_min": 20, "target_word_count": 40, "target_word_max": 80},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["workflow_mode"] == "discovery"
    assert body["draft"]["status"] == "draft"
    assert body["draft"]["chapter_plan_id"] is None
    assert body["draft"]["target_word_count"] == 40


def test_story_studio_deterministically_captures_directed_relationship_and_timeline(client: TestClient, sample_project):
    project_id = _project(client, sample_project)
    response = client.post(
        f"/api/projects/{project_id}/story-studio",
        json={"query": "Mara is the protagonist. Ivo distrusts Mara. The reveal that Elias is alive happens around Chapter 10."},
    )
    assert response.status_code == 200, response.text
    candidates = response.json().get("planning_capture", {}).get("candidates", [])
    descriptions = [str(item.get("description")) for item in candidates]
    assert any(item.get("type") == "relationship" and "Ivo distrusts Mara" in item.get("description", "") for item in candidates)
    assert any(item.get("type") == "timeline_event" and "Chapter 10" in item.get("description", "") for item in candidates)


def test_manual_chapter_edit_creates_reviewable_lineage_version(client: TestClient, sample_project):
    project_id = _project(client, sample_project)
    generated = client.post(
        f"/api/projects/{project_id}/discovery-writing",
        json={"instruction": "Mara opens the river gate.", "target_word_min": 20, "target_word_count": 40, "target_word_max": 80},
    )
    assert generated.status_code == 200, generated.text
    draft_id = generated.json()["draft"]["draft_id"]
    edited = client.put(
        f"/api/projects/{project_id}/chapter-drafts/{draft_id}/content",
        json={"edited_text": "Mara opens the river gate and hears the city answer."},
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()["draft"]
    assert body["version_number"] == 2
    assert body["status"] == "review"
    assert body["active"] is True
    assert body["generated_text"].startswith("Mara opens")


def test_approved_discovery_draft_extracts_candidate_knowledge(client: TestClient, sample_project):
    project_id = _project(client, sample_project)
    generated = client.post(
        f"/api/projects/{project_id}/discovery-writing",
        json={"instruction": "Mara reaches the locked city gate and hears the river speaking.", "target_word_min": 20, "target_word_count": 40, "target_word_max": 80},
    )
    assert generated.status_code == 200, generated.text
    draft_id = generated.json()["draft"]["draft_id"]
    review = client.put(
        f"/api/projects/{project_id}/chapter-drafts/{draft_id}/status",
        json={"status": "review", "reason": "The author is reviewing this discovery passage."},
    )
    assert review.status_code == 200, review.text
    approved = client.put(
        f"/api/projects/{project_id}/chapter-drafts/{draft_id}/status",
        json={"status": "approved", "reason": "The author approved this discovery passage."},
    )
    assert approved.status_code == 200, approved.text
    extractions = client.get(f"/api/projects/{project_id}/discovery-writing/extractions")
    assert extractions.status_code == 200
    assert extractions.json()[0]["status"] == "candidate"
    assert approved.json()["chapter_intelligence"]["workflow_mode"] == "discovery"


def test_discovery_long_form_chain_keeps_chapters_connected(client: TestClient, sample_project):
    project_id = _project(client, sample_project)
    for chapter in range(1, 11):
        generated = client.post(
            f"/api/projects/{project_id}/discovery-writing",
            json={"instruction": f"Chapter {chapter}: Mara crosses the river and faces a consequence from the previous choice.", "target_word_min": 20, "target_word_count": 40, "target_word_max": 80},
        )
        assert generated.status_code == 200, generated.text
        draft = generated.json()["draft"]
        assert draft["chapter_number"] == chapter
        draft_id = draft["draft_id"]
        assert client.put(f"/api/projects/{project_id}/chapter-drafts/{draft_id}/status", json={"status": "review"}).status_code == 200
        approved = client.put(f"/api/projects/{project_id}/chapter-drafts/{draft_id}/status", json={"status": "approved", "reason": "Approved after review."})
        assert approved.status_code == 200, approved.text

    extractions = client.get(f"/api/projects/{project_id}/discovery-writing/extractions").json()
    assert len(extractions) == 10
    assert all(item["status"] == "candidate" for item in extractions)
