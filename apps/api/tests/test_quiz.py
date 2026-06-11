def test_create_quiz_returns_questions(client, uploaded_doc_id):
    response = client.post(
        f"/documents/{uploaded_doc_id}/quiz",
        json={"num_questions": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == uploaded_doc_id
    assert isinstance(data["questions"], list)
    assert len(data["questions"]) >= 1


def test_create_quiz_questions_have_required_fields(client, uploaded_doc_id):
    response = client.post(
        f"/documents/{uploaded_doc_id}/quiz",
        json={"num_questions": 3},
    )
    assert response.status_code == 200
    for q in response.json()["questions"]:
        assert q["question"]
        assert q["answer"]
        assert q["explanation"] is not None
        assert isinstance(q["options"], list)


def test_quiz_is_retrievable_by_id(client, uploaded_doc_id):
    create_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz",
        json={"num_questions": 3},
    )
    quiz_id = create_resp.json()["id"]

    get_resp = client.get(f"/documents/{uploaded_doc_id}/quiz/{quiz_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == quiz_id


def test_quiz_nonexistent_document_returns_404(client):
    response = client.post("/documents/nonexistent/quiz", json={"num_questions": 3})
    assert response.status_code == 404


def test_quiz_nonexistent_id_returns_404(client, uploaded_doc_id):
    response = client.get(f"/documents/{uploaded_doc_id}/quiz/badid")
    assert response.status_code == 404


def test_quiz_num_questions_out_of_range_rejected(client, uploaded_doc_id):
    response = client.post(
        f"/documents/{uploaded_doc_id}/quiz",
        json={"num_questions": 0},
    )
    assert response.status_code == 422


# ── attempt tests ─────────────────────────────────────────────────────────────

def test_submit_attempt_returns_score(client, uploaded_doc_id):
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz",
        json={"num_questions": 3},
    )
    quiz = quiz_resp.json()
    quiz_id = quiz["id"]
    # Build answers: for each question use the correct answer
    answers = {q["id"]: q["answer"] for q in quiz["questions"]}

    resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt",
        json={"answers": answers},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["quiz_id"] == quiz_id
    assert "score" in data
    assert "total" in data
    assert "results" in data
    assert len(data["results"]) == len(quiz["questions"])


def test_submit_attempt_correct_mc_answer(client, uploaded_doc_id):
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz",
        json={"num_questions": 3},
    )
    quiz = quiz_resp.json()
    quiz_id = quiz["id"]

    # Find any multiple_choice question
    mc_questions = [q for q in quiz["questions"] if q["type"] == "multiple_choice"]
    if not mc_questions:
        return  # skip if no MC questions in mock

    answers = {mc_questions[0]["id"]: mc_questions[0]["answer"]}
    resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt",
        json={"answers": answers},
    )
    assert resp.status_code == 200
    result = next(r for r in resp.json()["results"] if r["question_id"] == mc_questions[0]["id"])
    assert result["is_correct"] is True


def test_submit_attempt_short_answer_requires_review(client, uploaded_doc_id):
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz",
        json={"num_questions": 3},
    )
    quiz = quiz_resp.json()
    quiz_id = quiz["id"]

    short_qs = [q for q in quiz["questions"] if q["type"] == "short_answer"]
    if not short_qs:
        return

    answers = {short_qs[0]["id"]: "some answer text"}
    resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt",
        json={"answers": answers},
    )
    assert resp.status_code == 200
    result = next(r for r in resp.json()["results"] if r["question_id"] == short_qs[0]["id"])
    assert result["requires_review"] is True


def test_submit_attempt_wrong_quiz_id_returns_404(client, uploaded_doc_id):
    resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz/nonexistent/attempt",
        json={"answers": {}},
    )
    assert resp.status_code == 404


def test_submit_attempt_wrong_doc_id_returns_404(client, uploaded_doc_id):
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz",
        json={"num_questions": 3},
    )
    quiz_id = quiz_resp.json()["id"]
    resp = client.post(
        f"/documents/nonexistent/quiz/{quiz_id}/attempt",
        json={"answers": {}},
    )
    assert resp.status_code == 404
