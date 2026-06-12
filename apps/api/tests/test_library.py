"""Tests for Phase C2: public document library and fork."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register(email: str) -> str:
    res = client.post("/auth/register", json={"email": email, "password": "pass123"})
    assert res.status_code == 201
    return res.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _upload_txt(token: str, content: str = "hello world") -> str:
    res = client.post(
        "/documents/upload",
        files={"file": ("note.txt", content.encode(), "text/plain")},
        headers=_headers(token),
    )
    assert res.status_code == 200
    return res.json()["document"]["id"]


# ── list public ───────────────────────────────────────────────────────────────

def test_public_library_empty_by_default():
    token = _register("alice_lib@example.com")
    _upload_txt(token)
    res = client.get("/documents/public", headers=_headers(token))
    assert res.status_code == 200
    assert res.json()["documents"] == []


# ── set visibility ────────────────────────────────────────────────────────────

def test_set_document_public():
    token = _register("pub_owner@example.com")
    doc_id = _upload_txt(token)

    res = client.patch(
        f"/documents/{doc_id}/visibility",
        json={"is_public": True},
        headers=_headers(token),
    )
    assert res.status_code == 200
    assert res.json()["is_public"] is True


def test_public_doc_appears_in_library():
    token = _register("visible@example.com")
    doc_id = _upload_txt(token)
    client.patch(f"/documents/{doc_id}/visibility", json={"is_public": True}, headers=_headers(token))

    res = client.get("/documents/public", headers=_headers(token))
    ids = [d["id"] for d in res.json()["documents"]]
    assert doc_id in ids


def test_set_document_private_removes_from_library():
    token = _register("toggle@example.com")
    doc_id = _upload_txt(token)
    client.patch(f"/documents/{doc_id}/visibility", json={"is_public": True}, headers=_headers(token))
    client.patch(f"/documents/{doc_id}/visibility", json={"is_public": False}, headers=_headers(token))

    res = client.get("/documents/public", headers=_headers(token))
    ids = [d["id"] for d in res.json()["documents"]]
    assert doc_id not in ids


def test_cannot_change_visibility_of_others_doc():
    token_a = _register("owner_vis@example.com")
    token_b = _register("other_vis@example.com")
    doc_id = _upload_txt(token_a)

    res = client.patch(
        f"/documents/{doc_id}/visibility",
        json={"is_public": True},
        headers=_headers(token_b),
    )
    assert res.status_code == 404


# ── fork ──────────────────────────────────────────────────────────────────────

def test_fork_creates_copy_in_user_library():
    token_owner = _register("fork_owner@example.com")
    token_user = _register("fork_user@example.com")

    doc_id = _upload_txt(token_owner, "original content")
    client.patch(f"/documents/{doc_id}/visibility", json={"is_public": True}, headers=_headers(token_owner))

    res = client.post(f"/documents/public/{doc_id}/fork", headers=_headers(token_user))
    assert res.status_code == 200
    forked = res.json()
    assert forked["forked_from"] == doc_id
    assert forked["is_public"] is False
    assert "副本" in forked["title"]


def test_forked_doc_appears_in_user_documents():
    token_owner = _register("fork_owner2@example.com")
    token_user = _register("fork_user2@example.com")

    doc_id = _upload_txt(token_owner)
    client.patch(f"/documents/{doc_id}/visibility", json={"is_public": True}, headers=_headers(token_owner))

    fork_res = client.post(f"/documents/public/{doc_id}/fork", headers=_headers(token_user))
    fork_id = fork_res.json()["id"]

    my_docs = client.get("/documents", headers=_headers(token_user)).json()["documents"]
    ids = [d["id"] for d in my_docs]
    assert fork_id in ids


def test_cannot_fork_private_document():
    token_owner = _register("priv_owner@example.com")
    token_user = _register("priv_user@example.com")

    doc_id = _upload_txt(token_owner)
    # NOT making it public

    res = client.post(f"/documents/public/{doc_id}/fork", headers=_headers(token_user))
    assert res.status_code == 404


def test_fork_requires_account_not_demo():
    token_owner = _register("demo_fork_owner@example.com")
    doc_id = _upload_txt(token_owner)
    client.patch(f"/documents/{doc_id}/visibility", json={"is_public": True}, headers=_headers(token_owner))

    # No auth header → demo mode
    res = client.post(f"/documents/public/{doc_id}/fork")
    assert res.status_code == 401
