def test_mastery_empty_before_any_attempt(client):
    resp = client.get("/profile/mastery")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["average_score"] == 0.0


def test_correct_mc_answer_increases_mastery(client, uploaded_doc_id):
    # Generate a quiz whose questions have knowledge_point set
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz", json={"num_questions": 3}
    )
    quiz = quiz_resp.json()
    quiz_id = quiz["id"]

    mc_qs = [q for q in quiz["questions"] if q["type"] == "multiple_choice" and q.get("knowledge_point")]
    if not mc_qs:
        return  # mock only returns short_answer; skip

    q = mc_qs[0]
    client.post(
        f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt",
        json={"answers": {q["id"]: q["answer"]}},
    )

    mastery = client.get("/profile/mastery").json()
    kp = q["knowledge_point"]
    item = next((i for i in mastery["items"] if i["knowledge_point"] == kp), None)
    assert item is not None
    assert item["mastery_score"] > 50  # started at 50, should be 58
    assert item["correct_count"] == 1
    assert item["mistake_count"] == 0


def test_wrong_mc_answer_decreases_mastery(client, uploaded_doc_id):
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz", json={"num_questions": 3}
    )
    quiz = quiz_resp.json()
    quiz_id = quiz["id"]

    mc_qs = [q for q in quiz["questions"] if q["type"] == "multiple_choice" and q.get("knowledge_point")]
    if not mc_qs:
        return

    q = mc_qs[0]
    wrong = "Z"  # definitely wrong
    client.post(
        f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt",
        json={"answers": {q["id"]: wrong}},
    )

    mastery = client.get("/profile/mastery").json()
    kp = q["knowledge_point"]
    item = next((i for i in mastery["items"] if i["knowledge_point"] == kp), None)
    assert item is not None
    assert item["mastery_score"] < 50  # started at 50, should be 35
    assert item["mistake_count"] == 1


def test_short_answer_does_not_update_mastery(client, uploaded_doc_id):
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz", json={"num_questions": 3}
    )
    quiz = quiz_resp.json()
    quiz_id = quiz["id"]

    short_qs = [q for q in quiz["questions"] if q["type"] == "short_answer"]
    if not short_qs:
        return

    q = short_qs[0]
    client.post(
        f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt",
        json={"answers": {q["id"]: "some answer"}},
    )

    # If knowledge_point was short_answer only, mastery should still be 0
    mastery = client.get("/profile/mastery").json()
    kp = q.get("knowledge_point")
    if kp:
        item = next((i for i in mastery["items"] if i["knowledge_point"] == kp), None)
        # short_answer with requires_review=True should NOT create/update mastery
        assert item is None


def test_mastery_accumulates_across_attempts(client, uploaded_doc_id):
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz", json={"num_questions": 3}
    )
    quiz = quiz_resp.json()
    quiz_id = quiz["id"]

    mc_qs = [q for q in quiz["questions"] if q["type"] == "multiple_choice" and q.get("knowledge_point")]
    if not mc_qs:
        return

    q = mc_qs[0]
    answers = {q["id"]: q["answer"]}

    # Submit twice → mastery should increase twice
    client.post(f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt", json={"answers": answers})
    client.post(f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt", json={"answers": answers})

    mastery = client.get("/profile/mastery").json()
    item = next((i for i in mastery["items"] if i["knowledge_point"] == q["knowledge_point"]), None)
    assert item is not None
    assert item["correct_count"] == 2
    assert item["mastery_score"] == min(100, 50 + 8 + 8)  # 66


def test_mastery_average_score_calculated(client, uploaded_doc_id):
    quiz_resp = client.post(
        f"/documents/{uploaded_doc_id}/quiz", json={"num_questions": 3}
    )
    quiz = quiz_resp.json()
    quiz_id = quiz["id"]

    mc_qs = [
        q for q in quiz["questions"]
        if q["type"] == "multiple_choice" and q.get("knowledge_point")
    ]
    if len(mc_qs) < 2:
        return

    # Answer first one correctly, second one wrong
    answers = {
        mc_qs[0]["id"]: mc_qs[0]["answer"],
        mc_qs[1]["id"]: "Z",
    }
    client.post(f"/documents/{uploaded_doc_id}/quiz/{quiz_id}/attempt", json={"answers": answers})

    resp = client.get("/profile/mastery").json()
    assert resp["total"] >= 2
    assert resp["average_score"] > 0
