"""Tests for the study-plan endpoint and planning service."""

import json


def test_study_plan_returns_200(client):
    resp = client.post("/profile/study-plan")
    assert resp.status_code == 200


def test_study_plan_schema(client):
    resp = client.post("/profile/study-plan")
    data = resp.json()
    assert "items" in data
    assert "generated_at" in data
    assert isinstance(data["items"], list)


def test_study_plan_empty_when_no_documents(client):
    resp = client.post("/profile/study-plan")
    data = resp.json()
    # No documents uploaded → items should be empty list
    assert data["items"] == []


def test_study_plan_with_document(client, uploaded_doc_id, monkeypatch):
    import app.services.llm as llm_mod

    def _mock_json(*args, **kwargs):
        return json.dumps({
            "items": [
                {
                    "document_id": uploaded_doc_id,
                    "document_title": "Test Doc",
                    "reason": "薄弱知识点相关",
                    "priority": 1,
                }
            ]
        })

    monkeypatch.setattr(llm_mod, "call_chat_json", _mock_json)

    resp = client.post("/profile/study-plan")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["document_id"] == uploaded_doc_id
    assert item["priority"] == 1
    assert "reason" in item


def test_study_plan_fallback_on_bad_json(client, uploaded_doc_id, monkeypatch):
    import app.services.llm as llm_mod

    # Return invalid JSON → service should fall back to heuristic plan
    monkeypatch.setattr(llm_mod, "call_chat_json", lambda *a, **kw: "not json at all")

    resp = client.post("/profile/study-plan")
    assert resp.status_code == 200
    data = resp.json()
    # Fallback should still list documents
    assert len(data["items"]) >= 1
