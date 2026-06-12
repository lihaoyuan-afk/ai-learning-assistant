"""Tests for weekly report and schedule-review endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_weekly_report_returns_schema():
    r = client.get("/profile/weekly-report")
    assert r.status_code == 200
    data = r.json()
    assert "documents_added" in data
    assert "quizzes_taken" in data
    assert "questions_answered" in data
    assert "correct_rate" in data
    assert "average_mastery" in data
    assert "weakest_points" in data
    assert "strongest_points" in data
    assert "recommendations" in data
    assert "generated_at" in data


def test_weekly_report_custom_days():
    r = client.get("/profile/weekly-report?days=30")
    assert r.status_code == 200
    assert r.json()["period_days"] == 30


def test_weekly_report_invalid_days():
    r = client.get("/profile/weekly-report?days=0")
    assert r.status_code == 400

    r = client.get("/profile/weekly-report?days=100")
    assert r.status_code == 400


def test_weekly_report_empty_db_has_fallback_recommendations():
    r = client.get("/profile/weekly-report")
    assert r.status_code == 200
    data = r.json()
    # With no data, average_mastery is 0 and recommendations is a non-empty fallback
    assert isinstance(data["recommendations"], str)
    assert len(data["recommendations"]) > 0


def test_schedule_review_success():
    r = client.post(
        "/profile/mastery/schedule-review",
        json={"knowledge_point": "测试知识点"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["knowledge_point"] == "测试知识点"


def test_schedule_review_creates_mastery_record():
    kp = "新增知识点_schedule_test"
    r = client.post("/profile/mastery/schedule-review", json={"knowledge_point": kp})
    assert r.status_code == 200

    # Verify it appears in mastery
    mastery = client.get("/profile/mastery").json()
    kps = [item["knowledge_point"] for item in mastery["items"]]
    assert kp in kps
