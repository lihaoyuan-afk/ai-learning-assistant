"""Tests for URL import and text/markdown upload (A1 + A3)."""

import pytest


# ── A3: text/markdown upload ──────────────────────────────────────────────────

def test_upload_txt_file(client):
    content = b"This is a plain text learning note.\n\nSection two content here."
    resp = client.post(
        "/documents/upload",
        files={"file": ("notes.txt", content, "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["document"]["title"] == "notes.txt"
    assert data["document"]["file_type"] == "text"


def test_upload_txt_reaches_ready(client):
    content = b"Learning content.\n\nMore content."
    resp = client.post(
        "/documents/upload",
        files={"file": ("notes.txt", content, "text/plain")},
    )
    doc_id = resp.json()["document"]["id"]
    for _ in range(20):
        status = client.get(f"/documents/{doc_id}").json()["status"]
        if status in ("ready", "failed"):
            break
    assert status == "ready"


def test_upload_md_file(client):
    content = b"# Chapter 1\n\nSome content.\n\n## Section\n\nMore text."
    resp = client.post(
        "/documents/upload",
        files={"file": ("lecture.md", content, "text/markdown")},
    )
    assert resp.status_code == 200
    assert resp.json()["document"]["file_type"] == "text"


def test_upload_md_reaches_ready(client):
    content = b"# Title\n\nParagraph one.\n\nParagraph two."
    resp = client.post(
        "/documents/upload",
        files={"file": ("doc.md", content, "text/markdown")},
    )
    doc_id = resp.json()["document"]["id"]
    for _ in range(20):
        status = client.get(f"/documents/{doc_id}").json()["status"]
        if status in ("ready", "failed"):
            break
    assert status == "ready"


def test_upload_empty_txt_rejected(client):
    resp = client.post(
        "/documents/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_unsupported_type_rejected(client):
    resp = client.post(
        "/documents/upload",
        files={"file": ("data.csv", b"a,b,c", "text/csv")},
    )
    assert resp.status_code == 400
    assert "Unsupported" in resp.json()["detail"]


# ── A1: URL import ────────────────────────────────────────────────────────────

def test_import_url_creates_document(client, monkeypatch):
    import app.workers.ingest_document as worker
    from app.services.document_parser import parse_text_bytes

    def _mock_parse_url(url: str):
        return parse_text_bytes(
            title="Mock Page Title",
            contents=b"Mocked web page content.\n\nSecond paragraph.",
        )

    monkeypatch.setattr(worker, "parse_url", _mock_parse_url)

    resp = client.post(
        "/documents/import-url",
        json={"url": "https://example.com/article"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["document"]["file_type"] == "url"


def test_import_url_reaches_ready(client, monkeypatch):
    import app.workers.ingest_document as worker
    from app.services.document_parser import parse_text_bytes

    def _mock_parse_url(url: str):
        return parse_text_bytes(
            title="Mock Article",
            contents=b"Article body.\n\nMore content here.",
        )

    monkeypatch.setattr(worker, "parse_url", _mock_parse_url)

    resp = client.post(
        "/documents/import-url",
        json={"url": "https://example.com/learn"},
    )
    doc_id = resp.json()["document"]["id"]
    for _ in range(20):
        status = client.get(f"/documents/{doc_id}").json()["status"]
        if status in ("ready", "failed"):
            break
    assert status == "ready"


def test_import_url_fetch_failure_sets_failed(client, monkeypatch):
    import app.workers.ingest_document as worker
    from app.services.document_parser import DocumentParseError

    def _mock_parse_url_fail(url: str):
        raise DocumentParseError("Fetch failed")

    monkeypatch.setattr(worker, "parse_url", _mock_parse_url_fail)

    resp = client.post(
        "/documents/import-url",
        json={"url": "https://example.com/bad"},
    )
    doc_id = resp.json()["document"]["id"]
    for _ in range(20):
        status = client.get(f"/documents/{doc_id}").json()["status"]
        if status in ("ready", "failed"):
            break
    assert status == "failed"


def test_import_url_invalid_url_rejected(client):
    resp = client.post(
        "/documents/import-url",
        json={"url": "not-a-url"},
    )
    assert resp.status_code == 422


def test_import_video_url_routes_to_youtube_parser(client, monkeypatch):
    import app.workers.ingest_document as worker
    from app.services.document_parser import parse_text_bytes

    called_with: list[str] = []

    def _mock_parse_youtube(url: str):
        called_with.append(url)
        return parse_text_bytes(
            title="Video Title",
            contents=b"Chapter 1\n\nDescription text.",
        )

    monkeypatch.setattr(worker, "parse_youtube_url", _mock_parse_youtube)

    resp = client.post(
        "/documents/import-url",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    doc_id = resp.json()["document"]["id"]
    for _ in range(20):
        status = client.get(f"/documents/{doc_id}").json()["status"]
        if status in ("ready", "failed"):
            break
    assert status == "ready"
    assert len(called_with) == 1
