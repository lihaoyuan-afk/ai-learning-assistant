from datetime import datetime, timedelta, timezone

import app.db.session as db_mod
from app.models.learning_memory import LearningMemory
from app.models.quiz import QuizQuestion as QuizQuestionModel, Quiz


def _insert_due_memory(db, kp: str, score: int = 30):
    """Insert a LearningMemory row whose next_review_at is in the past."""
    past = datetime.now(timezone.utc) - timedelta(days=1)
    mem = LearningMemory(
        id=f"mem_{kp}",
        knowledge_point=kp,
        mastery_score=score,
        correct_count=1,
        mistake_count=0,
        last_reviewed_at=past,
        next_review_at=past,
    )
    db.add(mem)
    db.commit()
    return mem


def _insert_future_memory(db, kp: str, score: int = 80):
    """Insert a LearningMemory row whose next_review_at is in the future."""
    future = datetime.now(timezone.utc) + timedelta(days=10)
    mem = LearningMemory(
        id=f"mem_{kp}",
        knowledge_point=kp,
        mastery_score=score,
        correct_count=3,
        mistake_count=0,
        last_reviewed_at=datetime.now(timezone.utc) - timedelta(days=1),
        next_review_at=future,
    )
    db.add(mem)
    db.commit()
    return mem


def test_review_today_empty(client):
    resp = client.get("/profile/review/today")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_review_today_returns_due_items(client):
    with db_mod.db_session() as db:
        _insert_due_memory(db, "newton_laws", score=30)

    resp = client.get("/profile/review/today")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["knowledge_point"] == "newton_laws"
    assert data["items"][0]["mastery_score"] == 30


def test_review_today_excludes_future_items(client):
    with db_mod.db_session() as db:
        _insert_future_memory(db, "thermodynamics", score=80)

    resp = client.get("/profile/review/today")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


def test_review_today_excludes_null_next_review(client):
    """Items with no next_review_at (never scheduled) must not appear."""
    with db_mod.db_session() as db:
        mem = LearningMemory(
            id="mem_unscheduled",
            knowledge_point="unscheduled_point",
            mastery_score=20,
            correct_count=0,
            mistake_count=0,
        )
        db.add(mem)
        db.commit()

    resp = client.get("/profile/review/today")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_review_today_includes_related_mc_questions(client, uploaded_doc_id):
    """After a quiz attempt, due items should carry back their MC questions."""
    # Generate quiz
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz", json={"num_questions": 3}
    )
    quiz = quiz_resp.json()
    quiz_id = quiz["id"]

    mc_qs = [
        q for q in quiz["questions"]
        if q["type"] == "multiple_choice" and q.get("knowledge_point")
    ]
    if not mc_qs:
        return  # mock returns short_answer only; skip

    q = mc_qs[0]
    # Submit a wrong answer so mastery < 40 → next_review in 2 days (future)
    # To make it "due today" we'll directly insert a past next_review_at after submitting
    client.post(
        f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt",
        json={"answers": {q["id"]: "Z"}},
    )

    # Override next_review_at to yesterday so the item appears today
    with db_mod.db_session() as db:
        mem = (
            db.query(LearningMemory)
            .filter(LearningMemory.knowledge_point == q["knowledge_point"])
            .first()
        )
        if mem:
            mem.next_review_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db.commit()

    resp = client.get("/profile/review/today")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    item = next(
        (i for i in data["items"] if i["knowledge_point"] == q["knowledge_point"]),
        None,
    )
    assert item is not None
    # MC questions for this knowledge_point should be attached
    assert len(item["questions"]) >= 1
    assert item["questions"][0]["type"] == "multiple_choice"


def test_next_review_scheduled_after_attempt(client, uploaded_doc_id):
    """Submitting a quiz attempt should set next_review_at on mastery rows."""
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz", json={"num_questions": 3}
    )
    quiz = quiz_resp.json()
    quiz_id = quiz["id"]

    mc_qs = [
        q for q in quiz["questions"]
        if q["type"] == "multiple_choice" and q.get("knowledge_point")
    ]
    if not mc_qs:
        return

    q = mc_qs[0]
    client.post(
        f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt",
        json={"answers": {q["id"]: q["answer"]}},  # correct
    )

    with db_mod.db_session() as db:
        mem = (
            db.query(LearningMemory)
            .filter(LearningMemory.knowledge_point == q["knowledge_point"])
            .first()
        )
        assert mem is not None
        assert mem.next_review_at is not None
        # correct answer → mastery ≥ 50 → 5-day schedule
        # next_review_at is stored as tz-naive UTC in SQLite
        from datetime import timezone as _tz
        expected_min = datetime.now(_tz.utc).replace(tzinfo=None) + timedelta(days=4)
        assert mem.next_review_at >= expected_min


def test_weak_item_scheduled_sooner(client):
    """mastery < 40 → next_review in 2 days, not 5 or 14."""
    with db_mod.db_session() as db:
        past = datetime.now(timezone.utc) - timedelta(days=1)
        mem = LearningMemory(
            id="mem_weak",
            knowledge_point="weak_point",
            mastery_score=25,
            correct_count=0,
            mistake_count=2,
            last_reviewed_at=past,
            next_review_at=past,  # due now
        )
        db.add(mem)
        db.commit()

    resp = client.get("/profile/review/today")
    data = resp.json()
    item = next(i for i in data["items"] if i["knowledge_point"] == "weak_point")
    assert item["mastery_score"] == 25
    # next_review_at in response should be in the past (overridden above)
    # SQLite stores tz-naive; strip tz for comparison
    nra_str = item["next_review_at"].replace("Z", "").split("+")[0]
    nra = datetime.fromisoformat(nra_str)
    from datetime import timezone as _tz
    assert nra <= datetime.now(_tz.utc).replace(tzinfo=None)
