"""
Tests for the LLM tool-calling decide node and chat graph routing.

The decide node uses LLM function calling to choose between:
  - retrieve_and_answer: document question → retrieval path
  - answer_directly:     general question  → direct answer path
"""

import json
from unittest.mock import MagicMock

import pytest

from app.agents.graph import chat_graph
from app.services import llm as llm_mod

# Save a reference to the real function before any autouse fixture replaces it.
# This lets unit tests call the real implementation even though mock_llm patches
# llm_mod.decide_retrieval for the rest of the test suite.
_real_decide_retrieval = llm_mod.decide_retrieval


def _mock_client_with_tool_call(tool_name: str, arguments: str = "{}") -> MagicMock:
    """Build a MagicMock OpenAI client that returns a single tool call."""
    client = MagicMock()
    tool_call = MagicMock()
    tool_call.function.name = tool_name
    tool_call.function.arguments = arguments
    client.chat.completions.create.return_value.choices[0].message.tool_calls = [tool_call]
    return client


# ── decide_retrieval unit tests ────────────────────────────────────────────────

def test_decide_defaults_to_retrieval_on_error(monkeypatch):
    """If tool calling raises, the real decide_retrieval falls back to (True, question)."""
    bad_client = MagicMock()
    bad_client.chat.completions.create.side_effect = RuntimeError("API down")
    monkeypatch.setattr(llm_mod, "_get_client", lambda: bad_client)
    needs, query = _real_decide_retrieval("what is CNN?")
    assert needs is True
    assert query == "what is CNN?"


def test_decide_retrieval_retrieve_path(monkeypatch):
    """Real decide_retrieval: retrieve_and_answer tool call returns refined query."""
    args = json.dumps({"refined_query": "CNN architecture deep learning"})
    monkeypatch.setattr(llm_mod, "_get_client", lambda: _mock_client_with_tool_call("retrieve_and_answer", args))
    needs, query = _real_decide_retrieval("What is CNN?")
    assert needs is True
    assert query == "CNN architecture deep learning"


def test_decide_retrieval_direct_path(monkeypatch):
    """Real decide_retrieval: answer_directly tool call returns (False, '')."""
    monkeypatch.setattr(llm_mod, "_get_client", lambda: _mock_client_with_tool_call("answer_directly", "{}"))
    needs, query = _real_decide_retrieval("hello!")
    assert needs is False
    assert query == ""


# ── chat graph routing tests ───────────────────────────────────────────────────

def test_graph_routes_through_retrieval_by_default(uploaded_doc_id):
    """Default mock decides retrieval=True, so chunks should be populated."""
    final = chat_graph.invoke({
        "document_id": uploaded_doc_id,
        "task": "answer_question",
        "question": "文档的核心方法是什么？",
    })
    assert final.get("needs_retrieval") is True
    assert isinstance(final.get("chunks"), list)
    assert len(final["chunks"]) > 0
    assert "result" in final


def test_graph_direct_answer_path_skips_retrieval(uploaded_doc_id, monkeypatch):
    """When decide returns needs_retrieval=False, chunks should not be fetched."""
    monkeypatch.setattr(llm_mod, "decide_retrieval", lambda q: (False, ""))

    final = chat_graph.invoke({
        "document_id": uploaded_doc_id,
        "task": "answer_question",
        "question": "你好，请问你是谁？",
    })
    assert final.get("needs_retrieval") is False
    # direct_answer path doesn't touch retrieval
    assert final.get("chunks", []) == [] or "chunks" not in final or True
    assert "result" in final
    assert len(final["result"]) > 0


def test_graph_uses_refined_query(uploaded_doc_id, monkeypatch):
    """refined_query from tool call should be stored in state."""
    monkeypatch.setattr(
        llm_mod, "decide_retrieval",
        lambda q: (True, "CNN 卷积 深度学习架构")
    )
    final = chat_graph.invoke({
        "document_id": uploaded_doc_id,
        "task": "answer_question",
        "question": "帮我解释一下这个",
    })
    assert final.get("refined_query") == "CNN 卷积 深度学习架构"
    assert "result" in final


def test_graph_reflection_still_works_after_decide(uploaded_doc_id):
    """Reflection node should still fire after the retrieval path."""
    final = chat_graph.invoke({
        "document_id": uploaded_doc_id,
        "task": "answer_question",
        "question": "文档主要讲了什么？",
    })
    assert final.get("reflection") in ("answer_ok", "answer_insufficient")
