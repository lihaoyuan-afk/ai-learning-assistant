from collections.abc import Generator

from app.schemas.document import DocumentRead, SourceChunk
from app.services import llm as _llm

# Fit within small local models: keep chunks short enough that
# system prompt + content + response stays under ~6000 tokens.
_MAX_CHUNKS = 12
_MAX_CHARS_PER_CHUNK = 400


def _trim(chunks: list[SourceChunk]) -> str:
    selected = chunks[:_MAX_CHUNKS]
    parts = []
    for c in selected:
        text = c.content[:_MAX_CHARS_PER_CHUNK]
        if len(c.content) > _MAX_CHARS_PER_CHUNK:
            text += "…"
        parts.append(f"[第{c.page_number or '?'}页] {text}")
    return "\n\n".join(parts)


_SYSTEM_PROMPT = (
    "你是一位专业的文档总结助手。请对以下文档内容生成结构化总结，包含：\n"
    "1. 文档概述（2-3句话）\n"
    "2. 核心概念（列表形式，每条一行）\n"
    "3. 主要内容（按主题分组）\n"
    "4. 学习要点（可供复习的关键点）\n"
    "请用中文回答，保持简洁清晰。"
)


def _build_messages(document: DocumentRead, chunks: list[SourceChunk]) -> list[dict]:
    content = _trim(chunks)
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"请总结以下文档内容：\n\n{content}"},
    ]


def generate_summary(document: DocumentRead, chunks: list[SourceChunk]) -> str:
    if not chunks:
        return f"《{document.title}》没有可用的文档内容，无法生成总结。"
    return _llm.call_chat(_build_messages(document, chunks), max_tokens=1500)


def stream_summary_text(
    document: DocumentRead, chunks: list[SourceChunk]
) -> Generator[str, None, None]:
    if not chunks:
        yield f"《{document.title}》没有可用的文档内容，无法生成总结。"
        return
    yield from _llm.stream_chat(_build_messages(document, chunks), max_tokens=1500)
