"""
LangGraph graphs for the three main agent flows.

chat_graph:    retrieve → answer → END
summary_graph: retrieve_all → summarize → END
quiz_graph:    retrieve_all → generate_quiz → END

Each node receives the full AgentState dict and returns a partial dict
of keys to merge back into state.  Errors are caught per-node and stored
in state["error"] so routes can surface them cleanly.
"""

from langgraph.graph import END, StateGraph

from app.agents.state import AgentState


# ── node functions ─────────────────────────────────────────────────────────────

def _retrieve(state: AgentState) -> dict:
    try:
        from app.services.retrieval import retrieve_context
        chunks = retrieve_context(
            document_id=state["document_id"],
            query=state.get("question", ""),
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
        )
        return {"result": answer}
    except Exception as exc:
        return {"result": f"LLM 调用失败：{exc}", "error": str(exc)}


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
    g.add_node("retrieve", _retrieve)
    g.add_node("answer", _answer)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "answer")
    g.add_edge("answer", END)
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
