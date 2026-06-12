"""Tests for JWT auth: register, login, /auth/me, token validation, document isolation."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register(email: str, password: str = "pass123") -> str:
    """Register and return the access token."""
    res = client.post("/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── register ──────────────────────────────────────────────────────────────────

def test_register_returns_token():
    token = _register("new@example.com")
    assert token and len(token) > 10


def test_register_duplicate_email_409():
    _register("dup@example.com")
    res = client.post("/auth/register", json={"email": "dup@example.com", "password": "pass123"})
    assert res.status_code == 409


def test_register_short_password_422():
    res = client.post("/auth/register", json={"email": "short@example.com", "password": "abc"})
    assert res.status_code == 422


# ── login ─────────────────────────────────────────────────────────────────────

def test_login_returns_token():
    _register("logintest@example.com")
    res = client.post("/auth/login", json={"email": "logintest@example.com", "password": "pass123"})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password_401():
    _register("badpw@example.com")
    res = client.post("/auth/login", json={"email": "badpw@example.com", "password": "wrongpass"})
    assert res.status_code == 401


def test_login_unknown_email_401():
    res = client.post("/auth/login", json={"email": "ghost@example.com", "password": "pass123"})
    assert res.status_code == 401


# ── /auth/me ──────────────────────────────────────────────────────────────────

def test_me_returns_user():
    token = _register("me@example.com")
    res = client.get("/auth/me", headers=_headers(token))
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "me@example.com"
    assert "id" in data
    assert "created_at" in data


def test_me_invalid_token_401():
    res = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert res.status_code == 401


def test_me_no_token_401():
    res = client.get("/auth/me")
    assert res.status_code in (401, 403)


# ── document isolation ────────────────────────────────────────────────────────

def _upload_txt(token: str, content: str = "hello world") -> str:
    """Upload a tiny text document and return its document_id."""
    res = client.post(
        "/documents/upload",
        files={"file": ("test.txt", content.encode(), "text/plain")},
        headers=_headers(token),
    )
    assert res.status_code == 200, res.text
    return res.json()["document"]["id"]


def test_users_see_only_their_documents():
    token_a = _register("alice@example.com")
    token_b = _register("bob@example.com")

    _upload_txt(token_a, "alice's note")
    _upload_txt(token_b, "bob's note")

    docs_a = client.get("/documents", headers=_headers(token_a)).json()["documents"]
    docs_b = client.get("/documents", headers=_headers(token_b)).json()["documents"]

    ids_a = {d["id"] for d in docs_a}
    ids_b = {d["id"] for d in docs_b}
    assert ids_a.isdisjoint(ids_b), "Users should not see each other's documents"


def test_user_cannot_access_other_users_document():
    token_a = _register("owner@example.com")
    token_b = _register("thief@example.com")

    doc_id = _upload_txt(token_a, "owner's private doc")

    res = client.get(f"/documents/{doc_id}", headers=_headers(token_b))
    assert res.status_code == 404
