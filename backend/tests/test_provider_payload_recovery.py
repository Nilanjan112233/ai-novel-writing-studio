from app.services.narrative_studio import _recover_required_text_payload


def test_recovers_scene_prose_from_malformed_structured_envelope():
    payload = _recover_required_text_payload(
        "SceneWriterAgent",
        '{"scene_draft":{"generated_text":"Rain struck the bus. Mira looked up."}, broken',
    )

    assert payload == {
        "scene_draft": {"generated_text": "Rain struck the bus. Mira looked up."}
    }


def test_accepts_unstructured_scene_prose_without_promoting_metadata():
    prose = "Rain struck the bus windows. " * 20
    payload = _recover_required_text_payload("SceneWriterAgent", prose)

    assert payload["scene_draft"]["generated_text"] == prose.strip()
    assert set(payload["scene_draft"]) == {"generated_text"}


def test_does_not_treat_malformed_json_as_reader_facing_prose():
    payload = _recover_required_text_payload(
        "SceneWriterAgent",
        '{"scene_draft":{"summary":"missing prose"}}' + (" " * 400),
    )

    assert payload == {}
