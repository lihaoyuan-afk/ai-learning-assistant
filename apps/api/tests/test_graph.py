"""
Tests that verify the three LangGraph flows produce the expected state transitions.
All LLM and embedding calls are already mocked by conftest autouse fixtures.
"""

from app.agents.graph import chat_graph, quiz_graph, summary_graph


def test_chat_graph_returns_result_and_chunks(uploaded_doc_id):
    final = chat_graph.invoke(
        {
            "document_id": uploaded_doc_id,
            "task": "answer_question",
            "question": "What is this document about?",
        }
    )
    assert "result" in final
    assert isinstance(final["result"], str)
    assert len(final["result"]) > 0
    assert "chunks" in final
    assert isinstance(final["chunks"], list)


def test_chat_graph_chunks_belong_to_document(uploaded_doc_id):
    final = chat_graph.invoke(
        {
            "document_id": uploaded_doc_id,
            "task": "answer_question",
            "question": "summarize the content",
        }
    )
    for chunk in final["chunks"]:
        assert chunk.document_id == uploaded_doc_id


def test_summary_graph_returns_result(uploaded_doc_id):
    final = summary_graph.invoke(
        {"document_id": uploaded_doc_id, "task": "generate_summary"}
    )
    assert "result" in final
    assert isinstance(final["result"], str)
    assert len(final["result"]) > 0


def test_summary_graph_fetches_all_chunks(uploaded_doc_id):
    final = summary_graph.invoke(
        {"document_id": uploaded_doc_id, "task": "generate_summary"}
    )
    # All chunks for the document should be present
    assert isinstance(final["chunks"], list)
    assert len(final["chunks"]) >= 1


def test_quiz_graph_returns_quiz_result(uploaded_doc_id):
    final = quiz_graph.invoke(
        {
            "document_id": uploaded_doc_id,
            "task": "generate_quiz",
            "num_questions": 3,
        }
    )
    assert "quiz_result" in final
    quiz = final["quiz_result"]
    assert quiz.document_id == uploaded_doc_id
    assert isinstance(quiz.questions, list)


def test_quiz_graph_respects_num_questions(uploaded_doc_id):
    final = quiz_graph.invoke(
        {
            "document_id": uploaded_doc_id,
            "task": "generate_quiz",
            "num_questions": 2,
        }
    )
    quiz = final["quiz_result"]
    # Mock LLM returns 1 question; result should be ≤ requested count
    assert len(quiz.questions) <= 2


def test_chat_endpoint_uses_graph(client, uploaded_doc_id):
    """Integration: HTTP endpoint must still work after routing through the graph."""
    resp = client.post(
        f"/documents/{uploaded_doc_id}/chat",
        json={"question": "What is the main topic?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data


def test_summary_endpoint_uses_graph(client, uploaded_doc_id):
    resp = client.post(f"/documents/{uploaded_doc_id}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert len(data["summary"]) > 0


def test_quiz_endpoint_uses_graph(client, uploaded_doc_id):
    resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz",
        json={"num_questions": 3},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "questions" in data
    assert "id" in data


# ── reflection node tests ──────────────────────────────────────────────────────

def test_chat_graph_has_reflection_state(uploaded_doc_id):
    """After a normal answer the reflection field should be 'answer_ok'."""
    final = chat_graph.invoke(
        {
            "document_id": uploaded_doc_id,
            "task": "answer_question",
            "question": "What is the main topic?",
        }
    )
    assert final.get("reflection") == "answer_ok"
    assert final.get("retry_count", 0) == 0


def test_chat_graph_reflection_retry_increments(uploaded_doc_id, monkeypatch):
    """If LLM returns a short fallback answer, reflect should trigger one retry."""
    from app.services import llm as llm_mod
    call_count = {"n": 0}

    def _short_answer(*args, **kwargs):
        call_count["n"] += 1
        return "没有找到"  # triggers retry heuristic

    monkeypatch.setattr(llm_mod, "answer_question", _short_answer)

    final = chat_graph.invoke(
        {
            "document_id": uploaded_doc_id,
            "task": "answer_question",
            "question": "obscure query",
        }
    )
    # Should have retried once (MAX_RETRIES=1), then settled
    assert call_count["n"] == 2
    assert final.get("retry_count", 0) == 1


def test_chat_graph_no_infinite_retry(uploaded_doc_id, monkeypatch):
    """Even with persistent fallback answers, graph must terminate."""
    from app.services import llm as llm_mod
    monkeypatch.setattr(llm_mod, "answer_question", lambda *a, **kw: "没有找到")
    # Should complete without hanging
    final = chat_graph.invoke(
        {
            "document_id": uploaded_doc_id,
            "task": "answer_question",
            "question": "anything",
        }
    )
    assert "result" in final
