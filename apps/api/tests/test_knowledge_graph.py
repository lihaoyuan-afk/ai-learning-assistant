"""Tests for B1 — Knowledge Graph extraction."""

import json


def test_knowledge_graph_returns_nodes_and_edges(client, uploaded_doc_id, monkeypatch):
    import app.services.llm as llm

    mock_graph = {
        "nodes": [
            {"id": "ml", "label": "机器学习", "type": "concept"},
            {"id": "dl", "label": "深度学习", "type": "concept"},
            {"id": "nn", "label": "神经网络", "type": "term"},
        ],
        "edges": [
            {"source": "dl", "target": "nn", "label": "使用"},
            {"source": "ml", "target": "dl", "label": "包含"},
        ],
    }
    monkeypatch.setattr(llm, "call_chat_json", lambda *a, **kw: json.dumps(mock_graph))

    resp = client.get(f"/documents/{uploaded_doc_id}/knowledge-graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == 3
    assert len(data["edges"]) == 2


def test_knowledge_graph_document_not_found(client):
    resp = client.get("/documents/nonexistent/knowledge-graph")
    assert resp.status_code == 404


def test_knowledge_graph_filters_invalid_edges(client, uploaded_doc_id, monkeypatch):
    import app.services.llm as llm

    mock_graph = {
        "nodes": [
            {"id": "nodeA", "label": "概念A", "type": "concept"},
        ],
        "edges": [
            {"source": "nodeA", "target": "nodeB", "label": "关联"},  # nodeB doesn't exist
        ],
    }
    monkeypatch.setattr(llm, "call_chat_json", lambda *a, **kw: json.dumps(mock_graph))

    resp = client.get(f"/documents/{uploaded_doc_id}/knowledge-graph")
    assert resp.status_code == 200
    data = resp.json()
    # Invalid edge (nodeB not in nodes) should be filtered out
    assert len(data["edges"]) == 0


def test_knowledge_graph_invalid_llm_json(client, uploaded_doc_id, monkeypatch):
    import app.services.llm as llm

    monkeypatch.setattr(llm, "call_chat_json", lambda *a, **kw: "not valid json")

    resp = client.get(f"/documents/{uploaded_doc_id}/knowledge-graph")
    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"] == []
    assert data["edges"] == []


def test_knowledge_graph_document_id_in_response(client, uploaded_doc_id, monkeypatch):
    import app.services.llm as llm

    monkeypatch.setattr(
        llm,
        "call_chat_json",
        lambda *a, **kw: json.dumps({"nodes": [], "edges": []}),
    )

    resp = client.get(f"/documents/{uploaded_doc_id}/knowledge-graph")
    assert resp.status_code == 200
    assert resp.json()["document_id"] == uploaded_doc_id
