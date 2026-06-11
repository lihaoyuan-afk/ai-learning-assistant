from typing import Any, Literal, TypedDict

from app.schemas.document import SourceChunk

AgentTask = Literal["answer_question", "generate_summary", "generate_quiz"]


class AgentState(TypedDict, total=False):
    document_id: str
    task: AgentTask
    question: str           # chat flow
    num_questions: int      # quiz flow
    chunks: list[SourceChunk]
    result: str             # chat / summary text output
    quiz_result: Any        # QuizResponse — typed Any to avoid circular import
    error: str              # set by nodes on failure; routes check this
    reflection: str         # reflection node's assessment
    retry_count: int        # how many times we've retried retrieval
    history: list[dict]     # conversation history for multi-turn chat
    needs_retrieval: bool   # set by decide node via tool calling
    refined_query: str      # LLM-optimised retrieval query from tool call
