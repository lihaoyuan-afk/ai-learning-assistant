"""Tests for B3 — Smart Error Notebook."""


def test_error_notebook_empty_initially(client):
    resp = client.get("/profile/error-notebook")
    assert resp.status_code == 200
    data = resp.json()
    assert data["groups"] == []
    assert data["total_mistakes"] == 0


def test_error_notebook_shows_wrong_answers(client, uploaded_doc_id):
    # Create quiz
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz",
        json={"num_questions": 2},
    )
    assert quiz_resp.status_code == 200
    quiz = quiz_resp.json()
    quiz_id = quiz["id"]

    # Find a MC question
    mc_q = next((q for q in quiz["questions"] if q["type"] == "multiple_choice"), None)
    if mc_q is None:
        return  # no MC question generated; skip

    # Submit a wrong answer (pick an option that's not the correct one)
    correct = mc_q["answer"][:1].upper()
    wrong_choice = next(
        (c for c in ["A", "B", "C", "D"] if c != correct),
        "B",
    )
    answers = {mc_q["id"]: wrong_choice}
    attempt_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt",
        json={"answers": answers},
    )
    assert attempt_resp.status_code == 200

    # Check error notebook
    resp = client.get("/profile/error-notebook")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_mistakes"] >= 1
    assert len(data["groups"]) >= 1

    # Find the entry
    all_entries = [e for g in data["groups"] for e in g["entries"]]
    entry_ids = [e["question_id"] for e in all_entries]
    assert mc_q["id"] in entry_ids


def test_error_notebook_groups_by_knowledge_point(client, uploaded_doc_id):
    # Create quiz and submit two wrong answers for the same knowledge point
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz",
        json={"num_questions": 2},
    )
    quiz = quiz_resp.json()
    quiz_id = quiz["id"]

    mc_questions = [q for q in quiz["questions"] if q["type"] == "multiple_choice"]
    if not mc_questions:
        return

    mc_q = mc_questions[0]
    correct = mc_q["answer"][:1].upper()
    wrong = next((c for c in ["A", "B", "C", "D"] if c != correct), "B")

    # Two attempts, both wrong
    for _ in range(2):
        client.post(
            f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt",
            json={"answers": {mc_q["id"]: wrong}},
        )

    resp = client.get("/profile/error-notebook")
    data = resp.json()
    all_entries = [e for g in data["groups"] for e in g["entries"]]
    target = next((e for e in all_entries if e["question_id"] == mc_q["id"]), None)
    assert target is not None
    assert target["mistake_count"] == 2


def test_error_notebook_entry_has_required_fields(client, uploaded_doc_id):
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz",
        json={"num_questions": 2},
    )
    quiz = quiz_resp.json()
    quiz_id = quiz["id"]

    mc_q = next((q for q in quiz["questions"] if q["type"] == "multiple_choice"), None)
    if mc_q is None:
        return

    correct = mc_q["answer"][:1].upper()
    wrong = next((c for c in ["A", "B", "C", "D"] if c != correct), "B")
    client.post(
        f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt",
        json={"answers": {mc_q["id"]: wrong}},
    )

    resp = client.get("/profile/error-notebook")
    data = resp.json()
    entry = next(
        (e for g in data["groups"] for e in g["entries"] if e["question_id"] == mc_q["id"]),
        None,
    )
    assert entry is not None
    assert "question_text" in entry
    assert "correct_answer" in entry
    assert "options" in entry
    assert "explanation" in entry
    assert entry["document_id"] == uploaded_doc_id
