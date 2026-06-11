"""Quiz generator — few-shot text format for small local models.

deepseek-r1:1.5b learns best by example.  We show one concrete sample
question and ask the model to follow the same format for new content.
Answers are extracted with regex; no JSON parsing required.
"""

import re
from uuid import uuid4

from app.schemas.document import DocumentRead, SourceChunk
from app.schemas.quiz import QuizQuestion, QuizResponse
from app.services import llm as _llm

_MAX_CHUNKS = 6
_MAX_CHARS_PER_CHUNK = 400

_SYSTEM = "你是一位专业的中文出题老师，只根据提供的文档内容出题，题目和答案必须与文档相关。"

_MC_PROMPT = """\
文档内容：
{content}

参考格式（不要照抄，要根据上面的文档内容出新题）：
题目：线性回归属于哪种学习范式
A：监督学习
B：无监督学习
C：强化学习
D：半监督学习
答案：A
解析：线性回归使用带标签的数据进行训练，是监督学习的典型算法
知识点：机器学习基础

请根据上面文档内容出1道新的单选题，格式和参考格式完全相同，题目和选项都用中文："""

_SA_PROMPT = """\
文档内容：
{content}

参考格式（不要照抄，要根据上面的文档内容出新题）：
题目：什么是过拟合，如何预防
答案：过拟合是模型在训练集上表现好但测试集上表现差的现象，可通过正则化、Dropout、数据增强等方法预防
解析：过拟合说明模型记住了训练数据而没有学到泛化规律
知识点：模型优化

请根据上面文档内容出1道新的简答题，格式和参考格式完全相同，题目和答案都用中文："""


def generate_quiz(
    document: DocumentRead, chunks: list[SourceChunk], num_questions: int = 6
) -> QuizResponse:
    if not chunks:
        return _empty_quiz(document)

    content = _trim(chunks)
    questions: list[QuizQuestion] = []

    mc_count = (num_questions + 1) // 2
    sa_count = num_questions - mc_count

    for _ in range(mc_count):
        q = _ask_one(_MC_PROMPT.format(content=content), q_type="multiple_choice")
        if q:
            questions.append(q)

    for _ in range(sa_count):
        q = _ask_one(_SA_PROMPT.format(content=content), q_type="short_answer")
        if q:
            questions.append(q)

    if not questions:
        return _empty_quiz(document)

    return QuizResponse(
        id=uuid4().hex,
        document_id=document.id,
        title=f"《{document.title}》测验",
        difficulty="mixed",
        questions=questions,
    )


# ── text parser ───────────────────────────────────────────────────────────────

# Patterns where the model embeds the answer letter in prose rather than on its own line
_ANSWER_FALLBACK_RE = re.compile(
    r"(?:正确答案|答案)[是为：:]\s*([A-Da-d])|选([A-Da-d])[^A-Za-z]|应选\s*([A-Da-d])",
    re.IGNORECASE,
)
# Split point when the model re-generates the prompt or starts a second question
_REPROMPT_RE = re.compile(r"\n(?:请根据|请你|按照参考格式|再出)", re.IGNORECASE)


def _field(text: str, key: str) -> str:
    pattern = rf"^{re.escape(key)}[：:]\s*(.+)"
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _first_block(text: str) -> str:
    """Keep only the first question block; cut at re-prompts or a second 题目：."""
    m = _REPROMPT_RE.search(text)
    if m:
        text = text[: m.start()]
    matches = list(re.finditer(r"\n题目[：:]", text))
    if len(matches) >= 2:
        text = text[: matches[1].start()]
    return text


def _extract_answer_fallback(text: str) -> str:
    """Extract answer letter when the model omits the 答案：line."""
    m = _ANSWER_FALLBACK_RE.search(text)
    if not m:
        return ""
    letter = m.group(1) or m.group(2) or m.group(3)
    return letter.upper() if letter else ""


def _ask_one(user_content: str, q_type: str) -> QuizQuestion | None:
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user_content},
    ]
    try:
        raw = _llm.call_chat(messages, max_tokens=800)
        if not raw.strip():
            return None

        raw = _first_block(raw)

        # Reject responses that just copy the example
        if "线性回归属于哪种学习范式" in raw or "什么是过拟合，如何预防" in raw:
            return None

        question_text = _field(raw, "题目")
        answer = _field(raw, "答案") or _extract_answer_fallback(raw)
        explanation = _field(raw, "解析")
        knowledge_point = _field(raw, "知识点") or None

        if not question_text or not answer:
            return None

        # Reject placeholders that slipped through
        if "在这里" in question_text or "在这里" in answer:
            return None
        # Reject unfilled bracket placeholders like [选项] [内容]
        if re.search(r"\[.{1,6}\]", question_text):
            return None

        options: list[str] = []
        if q_type == "multiple_choice":
            for letter in ("A", "B", "C", "D"):
                val = _field(raw, letter)
                if val:
                    options.append(f"{letter}. {val}")
            if not options:
                return None
            # Normalise answer: extract the leading letter (A/B/C/D).
            m = re.match(r"^([A-Da-d])", answer.strip())
            answer = m.group(1).upper() if m else answer.strip()

        return QuizQuestion(
            id=uuid4().hex,
            type=q_type,
            question=question_text,
            options=options,
            answer=answer,
            explanation=explanation,
            knowledge_point=knowledge_point,
        )
    except Exception:
        return None


# ── helpers ───────────────────────────────────────────────────────────────────

def _trim(chunks: list[SourceChunk]) -> str:
    selected = chunks[:_MAX_CHUNKS]
    parts = []
    for c in selected:
        text = c.content[:_MAX_CHARS_PER_CHUNK]
        if len(c.content) > _MAX_CHARS_PER_CHUNK:
            text += "…"
        parts.append(f"[第{c.page_number or '?'}页] {text}")
    return "\n\n".join(parts)


def _empty_quiz(document: DocumentRead) -> QuizResponse:
    return QuizResponse(
        id=uuid4().hex,
        document_id=document.id,
        title=f"《{document.title}》测验",
        difficulty="mixed",
        questions=[],
    )
