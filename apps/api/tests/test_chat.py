def test_chat_returns_answer_and_sources(client, uploaded_doc_id):
    response = client.post(
        f"/documents/{uploaded_doc_id}/chat",
        json={"question": "What is this document about?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0
    assert isinstance(data["sources"], list)


def test_chat_nonexistent_document_returns_404(client):
    response = client.post(
        "/documents/nonexistent/chat",
        json={"question": "What?"},
    )
    assert response.status_code == 404


def test_chat_empty_question_rejected(client, uploaded_doc_id):
    response = client.post(
        f"/documents/{uploaded_doc_id}/chat",
        json={"question": ""},
    )
    assert response.status_code == 422


def test_chat_sources_have_document_id(client, uploaded_doc_id):
    response = client.post(
        f"/documents/{uploaded_doc_id}/chat",
        json={"question": "test content"},
    )
    assert response.status_code == 200
    sources = response.json()["sources"]
    for source in sources:
        assert source["document_id"] == uploaded_doc_id
