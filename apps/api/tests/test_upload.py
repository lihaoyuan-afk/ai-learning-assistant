import pytest


def _wait_for_final_status(client, doc_id: str) -> str:
    """Poll until document status leaves 'uploaded'/'processing'."""
    for _ in range(20):
        status = client.get(f"/documents/{doc_id}").json()["status"]
        if status in ("ready", "failed"):
            return status
    return status


def test_upload_valid_pdf(client, valid_pdf_bytes):
    response = client.post(
        "/documents/upload",
        files={"file": ("lecture.pdf", valid_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["document"]["title"] == "lecture.pdf"
    assert data["document"]["status"] in ("uploaded", "processing", "ready", "failed")


def test_upload_returns_ready_status(client, valid_pdf_bytes):
    response = client.post(
        "/documents/upload",
        files={"file": ("test.pdf", valid_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    doc_id = response.json()["document"]["id"]
    # Background tasks run synchronously inside TestClient
    assert _wait_for_final_status(client, doc_id) == "ready"


def test_upload_non_pdf_rejected(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_upload_empty_file_rejected(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_oversized_file_rejected(client, monkeypatch):
    import app.workers.ingest_document as worker
    monkeypatch.setattr(worker.settings, "max_upload_size_mb", 0)
    response = client.post(
        "/documents/upload",
        files={"file": ("big.pdf", b"x" * 10, "application/pdf")},
    )
    assert response.status_code == 400
    assert "size" in response.json()["detail"].lower()


def test_upload_corrupt_pdf_returns_failed_status(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("corrupt.pdf", b"not a real pdf", "application/pdf")},
    )
    assert response.status_code == 200
    doc_id = response.json()["document"]["id"]
    assert _wait_for_final_status(client, doc_id) == "failed"


def test_upload_document_appears_in_list(client, valid_pdf_bytes):
    client.post(
        "/documents/upload",
        files={"file": ("list_test.pdf", valid_pdf_bytes, "application/pdf")},
    )
    response = client.get("/documents")
    assert response.status_code == 200
    titles = [d["title"] for d in response.json()["documents"]]
    assert "list_test.pdf" in titles
