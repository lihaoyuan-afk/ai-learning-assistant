"""
LangGraph graphs for the three main agent flows.

chat_graph:    decide(tool calling) → route
                 ↓ needs_retrieval=True    ↓ needs_retrieval=False
               retrieve                direct_answer → END
                 ↓
               answer → reflect → [retry→retrieve | END]

summary_graph: retrieve_all → summarize → END
quiz_graph:    retrieve_all → generate_quiz → END

Each node receives the full AgentState dict and returns a partial dict
of keys to merge back into state.  Errors are caught per-node and stored
in state["error"] so routes can surface them cleanly.
"""

from langgraph.graph import END, StateGraph

from app.agents.state import AgentState

_MAX_RETRIES = 1

# ── node functions ─────────────────────────────────────────────────────────────

def _decide(state: AgentState) -> dict:
    """Use LLM tool calling to decide if retrieval is needed and refine the query."""
    try:
        from app.services.llm import decide_retrieval
        needs_retrieval, refined_query = decide_retrieval(state.get("question", ""))
        return {
            "needs_retrieval": needs_retrieval,
            "refined_query": refined_query or state.get("question", ""),
        }
    except Exception:
        return {"needs_retrieval": True, "refined_query": state.get("question", "")}


def _route_after_decide(state: AgentState) -> str:
    if state.get("needs_retrieval", True):
        return "retrieve"
    return "direct_answer"


def _direct_answer(state: AgentState) -> dict:
    """Answer general/conversational questions without document retrieval."""
    try:
        from app.services.llm import call_chat
        question = state.get("question", "")
        messages: list[dict] = [
            {"role": "system", "content": "你是一位友好的学习助手，请直接回答用户的问题。"},
        ]
        history = state.get("history") or []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})
        return {"result": call_chat(messages, max_tokens=800)}
    except Exception as exc:
        return {"result": f"回答失败：{exc}", "error": str(exc)}


def _retrieve(state: AgentState) -> dict:
    try:
        from app.services.retrieval import retrieve_context
        retry_count = state.get("retry_count", 0)
        # Use tool-calling refined query if available; fall back to original question
        query = state.get("refined_query") or state.get("question", "")
        # On retry, increase retrieval limit to cast a wider net
        limit = 8 if retry_count > 0 else 5
        chunks = retrieve_context(
            document_id=state["document_id"],
            query=query,
            limit=limit,
        )
        return {"chunks": chunks}
    except Exception as exc:
        return {"chunks": [], "error": f"检索失败：{exc}"}


def _retrieve_all(state: AgentState) -> dict:
    try:
        from app.services.document_store import get_chunks
        chunks = get_chunks(state["document_id"])
        return {"chunks": chunks}
    except Exception as exc:
        return {"chunks": [], "error": f"读取文档块失败：{exc}"}


def _answer(state: AgentState) -> dict:
    if state.get("error"):
        return {"result": f"无法回答：{state['error']}"}
    try:
        from app.services.llm import answer_question
        answer = answer_question(
            question=state.get("question", ""),
            chunks=state.get("chunks", []),
            history=state.get("history"),
        )
        return {"result": answer}
    except Exception as exc:
        return {"result": f"LLM 调用失败：{exc}", "error": str(exc)}


def _reflect(state: AgentState) -> dict:
    """Assess answer quality; signal retry if answer looks like a fallback."""
    result = state.get("result", "")
    retry_count = state.get("retry_count", 0)

    # Heuristic: if the answer is very short or contains common fallback phrases,
    # it probably means retrieval didn't find relevant content.
    fallback_signals = [
        "没有找到", "无法回答", "文档中没有", "没有相关",
        "找不到相关", "I don't know", "not found",
    ]
    is_fallback = len(result.strip()) < 30 or any(s in result for s in fallback_signals)

    if is_fallback and retry_count < _MAX_RETRIES:
        return {
            "reflection": "answer_insufficient",
            "retry_count": retry_count + 1,
        }
    return {
        "reflection": "answer_ok",
    }


def _route_after_reflect(state: AgentState) -> str:
    if state.get("reflection") == "answer_insufficient":
        return "retrieve"
    return END


def _summarize(state: AgentState) -> dict:
    if state.get("error"):
        return {"result": f"无法生成总结：{state['error']}"}
    try:
        from app.services.document_store import get_document
        from app.services.summary_generator import generate_summary
        document = get_document(state["document_id"])
        summary = generate_summary(document=document, chunks=state.get("chunks", []))
        return {"result": summary}
    except Exception as exc:
        return {"result": f"总结生成失败：{exc}", "error": str(exc)}


def _generate_quiz(state: AgentState) -> dict:
    if state.get("error"):
        from app.services.quiz_generator import _empty_quiz
        from app.services.document_store import get_document
        doc = get_document(state["document_id"])
        return {"quiz_result": _empty_quiz(doc), "error": state["error"]}
    try:
        from app.services.document_store import get_document
        from app.services.quiz_generator import generate_quiz
        document = get_document(state["document_id"])
        quiz = generate_quiz(
            document=document,
            chunks=state.get("chunks", []),
            num_questions=state.get("num_questions", 6),
        )
        return {"quiz_result": quiz}
    except Exception as exc:
        from app.services.quiz_generator import _empty_quiz
        from app.services.document_store import get_document
        doc = get_document(state["document_id"])
        return {"quiz_result": _empty_quiz(doc), "error": str(exc)}


# ── graph factories ────────────────────────────────────────────────────────────

def _build_chat_graph():
    g = StateGraph(AgentState)
    g.add_node("decide", _decide)
    g.add_node("retrieve", _retrieve)
    g.add_node("direct_answer", _direct_answer)
    g.add_node("answer", _answer)
    g.add_node("reflect", _reflect)
    g.set_entry_point("decide")
    g.add_conditional_edges(
        "decide",
        _route_after_decide,
        {"retrieve": "retrieve", "direct_answer": "direct_answer"},
    )
    g.add_edge("direct_answer", END)
    g.add_edge("retrieve", "answer")
    g.add_edge("answer", "reflect")
    g.add_conditional_edges("reflect", _route_after_reflect, {"retrieve": "retrieve", END: END})
    return g.compile()


def _build_summary_graph():
    g = StateGraph(AgentState)
    g.add_node("retrieve_all", _retrieve_all)
    g.add_node("summarize", _summarize)
    g.set_entry_point("retrieve_all")
    g.add_edge("retrieve_all", "summarize")
    g.add_edge("summarize", END)
    return g.compile()


def _build_quiz_graph():
    g = StateGraph(AgentState)
    g.add_node("retrieve_all", _retrieve_all)
    g.add_node("generate_quiz", _generate_quiz)
    g.set_entry_point("retrieve_all")
    g.add_edge("retrieve_all", "generate_quiz")
    g.add_edge("generate_quiz", END)
    return g.compile()


# Compiled graphs — import these in route handlers
chat_graph = _build_chat_graph()
summary_graph = _build_summary_graph()
quiz_graph = _build_quiz_graph()
