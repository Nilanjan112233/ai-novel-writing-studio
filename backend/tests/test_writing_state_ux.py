from fastapi.testclient import TestClient


def _project(client: TestClient, sample_project: dict) -> str:
    response = client.post('/api/projects', json=sample_project)
    assert response.status_code == 200
    return response.json()['id']


def _approve(client: TestClient, project_id: str, instruction: str) -> dict:
    generated = client.post(
        f'/api/projects/{project_id}/discovery-writing',
        json={'instruction': instruction, 'target_word_min': 20, 'target_word_count': 40, 'target_word_max': 80},
    )
    assert generated.status_code == 200, generated.text
    draft = generated.json()['draft']
    assert client.put(f"/api/projects/{project_id}/chapter-drafts/{draft['draft_id']}/status", json={'status': 'review'}).status_code == 200
    approved = client.put(
        f"/api/projects/{project_id}/chapter-drafts/{draft['draft_id']}/status",
        json={'status': 'approved', 'reason': 'Approved for writing-state coverage.'},
    )
    assert approved.status_code == 200, approved.text
    return approved.json()


def test_writing_state_projects_discovery_chapters_and_next_action(client: TestClient, sample_project):
    project_id = _project(client, sample_project)
    _approve(client, project_id, 'Mara finds a brass compass and promises to return to the river.')
    _approve(client, project_id, 'Mara returns to the river and the compass points toward a hidden path.')

    response = client.get(f'/api/projects/{project_id}/writing-state')
    assert response.status_code == 200
    body = response.json()
    assert body['workflow_mode'] == 'discovery'
    assert body['chapter_count'] == 2
    assert body['latest_approved_chapter']['chapter_number'] == 2
    assert body['next_action']['label'] == 'Continue with Chapter 3'
    assert [item['chapter_number'] for item in body['chapters']] == [1, 2]
    assert body['chapters'][0]['active_version'] == 1


def test_chapter_context_is_author_facing_and_provenance_bounded(client: TestClient, sample_project):
    project_id = _project(client, sample_project)
    _approve(client, project_id, 'Mara carries a brass compass and keeps a promise about the river.')
    response = client.get(f'/api/projects/{project_id}/writing-state/chapters/1/context')
    assert response.status_code == 200
    body = response.json()
    assert body['chapter_number'] == 1
    assert body['source']
    assert 'candidate_status' in body['learned_from_chapter']
    assert 'carried_into_generation' in body


def test_discovery_approval_keeps_core_approval_separate_from_enrichment(client: TestClient, sample_project):
    project_id = _project(client, sample_project)
    approved = _approve(client, project_id, 'Mara hears the third bell and chooses to trust Ivo.')
    assert approved['draft']['status'] == 'approved'
    assert approved['draft']['enrichment_status'] in {'completed', 'failed'}
    assert 'enrichment' in approved
