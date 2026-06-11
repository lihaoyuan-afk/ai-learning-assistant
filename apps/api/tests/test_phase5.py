"""Tests for Phase 5 features: delete, summary stream, chat history, global search."""
import json


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_sse(text: str) -> list[dict]:
    events = []
    for part in text.split("\n\n"):
        part = part.strip()
        if part.startswith("data:"):
            try:
                events.append(json.loads(part[5:].strip()))
            except Exception:
                pass
    return events


# ── delete document ───────────────────────────────────────────────────────────

def test_delete_document_returns_ok(client, uploaded_doc_id):
    response = client.delete(f"/documents/{uploaded_doc_id}")
    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()


def test_delete_document_no_longer_accessible(client, uploaded_doc_id):
    client.delete(f"/documents/{uploaded_doc_id}")
    assert client.get(f"/documents/{uploaded_doc_id}").status_code == 404


def test_delete_document_removed_from_list(client, uploaded_doc_id):
    client.delete(f"/documents/{uploaded_doc_id}")
    ids = [d["id"] for d in client.get("/documents").json()["documents"]]
    assert uploaded_doc_id not in ids


def test_delete_nonexistent_document_returns_404(client):
    assert client.delete("/documents/nonexistent").status_code == 404


# ── summary stream ─────────────────────────────────────────────────────────────

def test_summary_stream_is_event_stream(client, uploaded_doc_id):
    response = client.post(f"/documents/{uploaded_doc_id}/summary/stream")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


def test_summary_stream_contains_token_and_done(client, uploaded_doc_id):
    response = client.post(f"/documents/{uploaded_doc_id}/summary/stream")
    types = [e.get("type") for e in _parse_sse(response.text)]
    assert "token" in types
    assert "done" in types


def test_summary_stream_nonexistent_returns_404(client):
    assert client.post("/documents/nonexistent/summary/stream").status_code == 404


def test_summary_stream_second_call_returns_cached(client, uploaded_doc_id):
    client.post(f"/documents/{uploaded_doc_id}/summary/stream")
    response = client.post(f"/documents/{uploaded_doc_id}/summary/stream")
    types = [e.get("type") for e in _parse_sse(response.text)]
    assert "cached" in types


# ── chat history ──────────────────────────────────────────────────────────────

def test_chat_accepts_history_field(client, uploaded_doc_id):
    response = client.post(
        f"/documents/{uploaded_doc_id}/chat",
        json={
            "question": "Can you elaborate?",
            "history": [
                {"role": "user", "content": "What is the main topic?"},
                {"role": "assistant", "content": "The main topic is machine learning."},
            ],
        },
    )
    assert response.status_code == 200
    assert isinstance(response.json()["answer"], str)


def test_chat_history_empty_list_is_valid(client, uploaded_doc_id):
    response = client.post(
        f"/documents/{uploaded_doc_id}/chat",
        json={"question": "Hello?", "history": []},
    )
    assert response.status_code == 200


# ── global search ─────────────────────────────────────────────────────────────

def test_global_search_stream_is_event_stream(client, uploaded_doc_id):
    response = client.post("/search/stream", json={"question": "What is in the documents?"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


def test_global_search_stream_contains_sources_and_done(client, uploaded_doc_id):
    response = client.post("/search/stream", json={"question": "test content"})
    types = [e.get("type") for e in _parse_sse(response.text)]
    assert "sources" in types
    assert "done" in types


def test_global_search_stream_accepts_history(client, uploaded_doc_id):
    response = client.post(
        "/search/stream",
        json={
            "question": "Tell me more",
            "history": [
                {"role": "user", "content": "What is supervised learning?"},
                {"role": "assistant", "content": "Supervised learning uses labeled data."},
            ],
        },
    )
    assert response.status_code == 200
    types = [e.get("type") for e in _parse_sse(response.text)]
    assert "done" in types


def test_global_search_empty_question_rejected(client):
    assert client.post("/search/stream", json={"question": ""}).status_code == 422
