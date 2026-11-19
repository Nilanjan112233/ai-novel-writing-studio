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


def test_selection_revision_keeps_the_rest_of_the_chapter(client: TestClient, sample_project: dict, monkeypatch):
    """A focused edit of one passage must not replace the whole chapter (found in a real-AI run)."""
    from app.services.editorial_service import editorial_service

    project_id = _project(client, sample_project)
    first = _approve(client, project_id, 'Open in the lighthouse.')['draft']
    second = _approve(client, project_id, 'Continue at the harbour.')['draft']
    chapter_text = 'Ada climbed the stairs.\n\nThe lamp room smelled of salt and old oil.\n\nShe opened the log.'
    edited = client.put(
        f"/api/projects/{project_id}/chapter-drafts/{first['draft_id']}/content",
        json={'edited_text': chapter_text},
    )
    assert edited.status_code == 200, edited.text
    source = edited.json()['draft']
    if source['status'] != 'review':
        assert client.put(f"/api/projects/{project_id}/chapter-drafts/{source['draft_id']}/status", json={'status': 'review'}).status_code == 200

    original_execute = editorial_service._execute

    async def fake_execute(db, **kwargs):
        if kwargs.get('agent_name') != 'RevisionAgent':
            return await original_execute(db, **kwargs)
        # Like the real model: only the revised passage comes back.
        return {'revision_proposal': {'generated_text': 'The lamp room reeked of brine and burnt wick.'}}, {}

    monkeypatch.setattr(editorial_service, '_execute', fake_execute)
    missing = client.post(
        f"/api/projects/{project_id}/chapter-drafts/{source['draft_id']}/selection-revision",
        json={'selected_text': 'Not in this chapter.', 'instruction': 'Sharpen it.'},
    )
    assert missing.status_code == 409
    response = client.post(
        f"/api/projects/{project_id}/chapter-drafts/{source['draft_id']}/selection-revision",
        json={'selected_text': 'The lamp room smelled of salt and old oil.', 'instruction': 'Make it sharper.'},
    )
    assert response.status_code == 200, response.text
    branch_id = response.json()['branch']['branch_id']
    assert response.json()['revision']['generated_text'] == (
        'Ada climbed the stairs.\n\nThe lamp room reeked of brine and burnt wick.\n\nShe opened the log.'
    )

    compared = client.get(f"/api/projects/{project_id}/revision-branches/{branch_id}/compare")
    assert compared.status_code == 200, compared.text
    for status in ('review', 'approved'):
        assert client.put(f"/api/projects/{project_id}/revision-branches/{branch_id}/status", json={'status': status}).status_code == 200
    applied = client.post(f"/api/projects/{project_id}/revision-branches/{branch_id}/apply")
    assert applied.status_code == 200, applied.text
    promoted = applied.json()['draft']
    assert promoted['chapter_number'] == source['chapter_number']
    assert promoted['word_count'] == len(promoted['generated_text'].split())
    assert 'Ada climbed the stairs.' in promoted['generated_text']

    # Applying a revision to chapter 1 must leave the other chapter active.
    drafts = client.get(f'/api/projects/{project_id}/chapter-drafts').json()
    other = next(item for item in drafts if item['draft_id'] == second['draft_id'])
    assert other['active'] is True
