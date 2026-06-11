def test_generate_summary_returns_text(client, uploaded_doc_id):
    response = client.post(f"/documents/{uploaded_doc_id}/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == uploaded_doc_id
    assert isinstance(data["summary"], str)
    assert len(data["summary"]) > 0


def test_summary_nonexistent_document_returns_404(client):
    response = client.post("/documents/nonexistent/summary")
    assert response.status_code == 404


def test_summary_is_persisted_on_document(client, uploaded_doc_id):
    client.post(f"/documents/{uploaded_doc_id}/summary")
    doc_resp = client.get(f"/documents/{uploaded_doc_id}")
    assert doc_resp.status_code == 200
    assert doc_resp.json()["summary"] is not None
