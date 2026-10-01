def test_user_message_promotes_to_locked_canon(client):
    response = client.post(
        "/api/projects",
        json={
            "title": "Canon Project",
            "premise": "A progression fantasy about self-made power.",
            "genre": "Fantasy",
            "tone": "Serious",
        },
    )
    project_id = response.json()["id"]

    client.post(
        f"/api/projects/{project_id}/messages",
        json={"content": "The transaction uses materials and the system is self-created."},
    )

    canon = client.get(f"/api/projects/{project_id}/canon").json()
    assert any("transaction uses materials" in fact.lower() for fact in canon["locked_facts"])
    assert any(decision["status"] == "approved" for decision in canon["decisions"])


def test_approved_discussion_proposal_promotes_to_canon(client):
    response = client.post(
        "/api/projects",
        json={
            "title": "Discussion Decision Project",
            "premise": "A court fantasy.",
            "genre": "Fantasy",
            "tone": "Political",
        },
    )
    project_id = response.json()["id"]
    client.post(
        f"/api/projects/{project_id}/messages",
        json={"content": "The academy is meritocratic but secretly faction-influenced."},
    )
    discussion = client.get(f"/api/projects/{project_id}/discussion").json()
    message_id = discussion[0]["id"]

    result = client.post(
        f"/api/projects/{project_id}/discussion/{message_id}/decision",
        json={"action": "approve", "note": "Lock academy meritocracy with hidden faction influence."},
    )
    assert result.status_code == 200

    canon = client.get(f"/api/projects/{project_id}/canon").json()
    assert any("academy meritocracy" in fact.lower() for fact in canon["locked_facts"])
