"""JSON-shape handling found during a real-provider run (Gemini returns bare lists)."""
from fastapi.testclient import TestClient

from app.services.provider_gateway import _wrap_json_list, provider_gateway


def test_wrap_json_list_accepts_bare_and_fenced_lists():
    assert _wrap_json_list('[{"type": "character"}]', "candidates") == {"candidates": [{"type": "character"}]}
    assert _wrap_json_list('```json\n[1, 2]\n```', "items") == {"items": [1, 2]}
    assert _wrap_json_list('{"candidates": []}', "candidates") is None
    assert _wrap_json_list("not json", "candidates") is None


def test_extraction_accepts_a_bare_candidate_list(client: TestClient, sample_project: dict, monkeypatch):
    project_id = client.post("/api/projects", json=sample_project).json()["id"]
    generated = client.post(
        f"/api/projects/{project_id}/discovery-writing",
        json={"instruction": "Open at the harbour.", "target_word_min": 20, "target_word_count": 40, "target_word_max": 80},
    )
    assert generated.status_code == 200, generated.text
    draft = generated.json()["draft"]

    original_generate = provider_gateway.generate

    async def list_for_extraction(messages, **kwargs):
        result = await original_generate(messages, **kwargs)
        if kwargs.get("agent_name") == "DiscoveryExtractionAgent":
            result = {**result, "content": '[{"type": "mystery", "description": "Who rang the harbour bell?"}]', "parsed": None}
        return result

    monkeypatch.setattr(provider_gateway, "generate", list_for_extraction)
    assert client.put(f"/api/projects/{project_id}/chapter-drafts/{draft['draft_id']}/status", json={"status": "review"}).status_code == 200
    approved = client.put(
        f"/api/projects/{project_id}/chapter-drafts/{draft['draft_id']}/status",
        json={"status": "approved", "reason": "Approve for extraction."},
    )
    assert approved.status_code == 200, approved.text
    extractions = client.get(f"/api/projects/{project_id}/discovery-writing/extractions").json()
    candidates = next(item for item in extractions if item["source_draft_id"] == draft["draft_id"])["candidates"]
    assert {"type": "mystery", "description": "Who rang the harbour bell?"} in candidates
