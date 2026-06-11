import json
import re
from collections.abc import Generator

from openai import OpenAI

from app.core.config import settings
from app.schemas.document import SourceChunk

_client: OpenAI | None = None

# deepseek-r1 wraps reasoning in <think>…</think> before the real answer
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
# Greedy JSON extraction when the model adds prose around the object
_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _strip_think(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


def _extract_json(text: str) -> str:
    """Return the outermost {...} block, or the original text if not found."""
    m = _JSON_BLOCK_RE.search(text)
    return m.group() if m else text


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.openai_api_key or "ollama",
            base_url=settings.openai_base_url,
            timeout=settings.llm_timeout,
        )
    return _client


def _ollama_extra() -> dict | None:
    """Pass num_ctx when using a local Ollama endpoint."""
    if settings.openai_base_url:
        return {"options": {"num_ctx": settings.ollama_num_ctx}}
    return None


def call_chat(messages: list[dict], max_tokens: int = 2000) -> str:
    response = _get_client().chat.completions.create(
        model=settings.openai_chat_model,
        messages=messages,
        max_tokens=max_tokens,
        extra_body=_ollama_extra(),
    )
    return _strip_think(response.choices[0].message.content or "")


def call_chat_json(messages: list[dict], max_tokens: int = 3000) -> str:
    """Call LLM and return a JSON string.

    Tries response_format=json_object first (supported by OpenAI and recent
    Ollama builds). Falls back to plain chat if the model/server rejects it.
    Strips deepseek-r1 <think> blocks and extracts the first {...} object.
    """
    extra = _ollama_extra()
    try:
        response = _get_client().chat.completions.create(
            model=settings.openai_chat_model,
            messages=messages,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            extra_body=extra,
        )
    except Exception:
        # Some models / older Ollama builds don't support json_object format
        response = _get_client().chat.completions.create(
            model=settings.openai_chat_model,
            messages=messages,
            max_tokens=max_tokens,
            extra_body=extra,
        )

    raw = _strip_think(response.choices[0].message.content or "{}")
    if not raw.startswith("{"):
        raw = _extract_json(raw)
    return raw or "{}"


def answer_question(
    question: str,
    chunks: list[SourceChunk],
    history: list[dict] | None = None,
) -> str:
    if not chunks:
        return "未检索到相关文档片段，请确保文档已完成解析。"

    context = "\n\n".join(
        f"[第{c.page_number or '?'}页] {c.content}" for c in chunks
    )
    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "你是一位专业的学习助手。请严格根据提供的文档片段回答问题，"
                "回答时必须在括号内注明来源页码，格式为（第X页）。"
                "如果文档中没有相关信息，请如实说明，不要编造内容。"
            ),
        },
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": f"文档片段：\n{context}\n\n问题：{question}"})
    return call_chat(messages, max_tokens=1200)


def stream_chat(messages: list[dict], max_tokens: int = 1200) -> Generator[str, None, None]:
    stream = _get_client().chat.completions.create(
        model=settings.openai_chat_model,
        messages=messages,
        max_tokens=max_tokens,
        stream=True,
        extra_body=_ollama_extra(),
    )
    buf = ""
    in_think = False
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if not delta:
            continue
        buf += delta
        if in_think:
            end = buf.find("</think>")
            if end >= 0:
                in_think = False
                buf = buf[end + 8:].lstrip("\n")
        else:
            start = buf.find("<think>")
            if start >= 0:
                if start > 0:
                    yield buf[:start]
                in_think = True
                buf = buf[start + 7:]
            else:
                # Keep last 7 chars in buffer to catch a partial <think> tag at boundary
                safe = max(0, len(buf) - 7)
                if safe > 0:
                    yield buf[:safe]
                    buf = buf[safe:]
    if buf and not in_think:
        yield buf


def stream_answer_question(
    question: str,
    chunks: list[SourceChunk],
    history: list[dict] | None = None,
) -> Generator[str, None, None]:
    if not chunks:
        yield "未检索到相关文档片段，请确保文档已完成解析。"
        return
    context = "\n\n".join(
        f"[第{c.page_number or '?'}页] {c.content}" for c in chunks
    )
    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "你是一位专业的学习助手。请严格根据提供的文档片段回答问题，"
                "回答时必须在括号内注明来源页码，格式为（第X页）。"
                "如果文档中没有相关信息，请如实说明，不要编造内容。"
            ),
        },
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": f"文档片段：\n{context}\n\n问题：{question}"})
    yield from stream_chat(messages, max_tokens=1200)


# ── Tool calling: retrieval routing ──────────────────────────────────────────

_DECIDE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_and_answer",
            "description": (
                "需要查阅上传文档的内容才能回答时调用。"
                "适用于：问文档里的事实、数据、方法、结论、具体章节内容等。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "refined_query": {
                        "type": "string",
                        "description": (
                            "用于向量检索的精炼查询词，可与原问题措辞不同，"
                            "去掉口语化表达，保留核心关键词，有利于语义检索。"
                        ),
                    }
                },
                "required": ["refined_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "answer_directly",
            "description": (
                "不需要查阅文档即可回答时调用。"
                "适用于：打招呼、闲聊、或纯粹的常识/通用知识问题。"
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def decide_retrieval(question: str) -> tuple[bool, str]:
    """Use LLM tool calling to decide if retrieval is needed.

    Returns (needs_retrieval, refined_query).
    Falls back to (True, question) if tool calling is unsupported or fails.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个路由助手。判断用户的问题是否需要查阅上传的文档才能回答，"
                "选择合适的工具。"
            ),
        },
        {"role": "user", "content": question},
    ]
    try:
        response = _get_client().chat.completions.create(
            model=settings.openai_chat_model,
            messages=messages,
            tools=_DECIDE_TOOLS,
            tool_choice="required",
            max_tokens=200,
            extra_body=_ollama_extra(),
        )
        message = response.choices[0].message
        if message.tool_calls:
            call = message.tool_calls[0]
            if call.function.name == "answer_directly":
                return False, ""
            args = json.loads(call.function.arguments or "{}")
            refined = args.get("refined_query", question)
            return True, refined or question
    except Exception:
        pass
    # Safe fallback: always retrieve when uncertain
    return True, question
