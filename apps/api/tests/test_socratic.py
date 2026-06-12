"""Tests for B2 — Socratic mode."""


def _collect_sse_tokens(response) -> str:
    """Parse SSE stream and concatenate token content."""
    tokens = []
    for line in response.text.splitlines():
        if line.startswith("data:"):
            import json
            try:
                event = json.loads(line[5:].strip())
                if event.get("type") == "token":
                    tokens.append(event["content"])
            except json.JSONDecodeError:
                pass
    return "".join(tokens)


def test_socratic_opening_question(client, uploaded_doc_id):
    resp = client.post(
        f"/documents/{uploaded_doc_id}/chat/socratic/stream",
        json={"topic": "主要概念"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    text = _collect_sse_tokens(resp)
    assert len(text) > 10


def test_socratic_follow_up_with_answer(client, uploaded_doc_id):
    resp = client.post(
        f"/documents/{uploaded_doc_id}/chat/socratic/stream",
        json={
            "user_answer": "我认为文档主要讲了机器学习的基础概念。",
            "history": [
                {"role": "assistant", "content": "请问你认为这篇文档的核心主题是什么？"},
            ],
            "topic": "机器学习",
        },
    )
    assert resp.status_code == 200
    text = _collect_sse_tokens(resp)
    assert len(text) > 5


def test_socratic_document_not_found(client):
    resp = client.post(
        "/documents/nonexistent/chat/socratic/stream",
        json={"topic": "test"},
    )
    assert resp.status_code == 404


def test_socratic_sse_contains_done(client, uploaded_doc_id):
    resp = client.post(
        f"/documents/{uploaded_doc_id}/chat/socratic/stream",
        json={},
    )
    assert resp.status_code == 200
    assert '"type":"done"' in resp.text or '"type": "done"' in resp.text
