"""Generate a personalised study plan from mastery + document data."""

import json
from datetime import datetime, timezone

from app.schemas.plan import StudyPlan, StudyPlanItem


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_study_plan() -> StudyPlan:
    from app.services.document_store import list_documents
    from app.services.mastery_service import get_mastery
    from app.services.llm import call_chat_json

    mastery = get_mastery()
    documents = list_documents()

    if not documents:
        return StudyPlan(items=[], generated_at=_utcnow_iso())

    # Summarise weak knowledge points (mastery < 70)
    weak = [i for i in mastery.items if i.mastery_score < 70]
    weak_summary = (
        "\n".join(
            f"- {i.knowledge_point}：掌握度 {i.mastery_score}%，"
            f"答对 {i.correct_count} 次，答错 {i.mistake_count} 次"
            for i in sorted(weak, key=lambda x: x.mastery_score)[:10]
        )
        if weak
        else "暂无薄弱知识点记录"
    )

    doc_list = "\n".join(
        f"- document_id={d.id}，标题：{d.title}" for d in documents
    )

    messages = [
        {
            "role": "system",
            "content": (
                "你是一位学习规划专家。根据学习者的知识点掌握情况和上传的文档列表，"
                "为学习者生成一份优先级排序的学习计划。"
                "你必须只输出合法的 JSON，格式如下：\n"
                '{"items": [{"document_id": "...", "document_title": "...", '
                '"reason": "建议学习原因", "priority": 1}]}\n'
                "priority 为整数，1 表示最高优先级，依次递增。"
                "如果某份文档与薄弱知识点高度相关，优先级应更高。"
                "只返回 JSON，不要添加任何解释文字。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"薄弱知识点（掌握度 < 70%）：\n{weak_summary}\n\n"
                f"可用文档列表：\n{doc_list}\n\n"
                "请生成学习计划 JSON。"
            ),
        },
    ]

    try:
        raw = call_chat_json(messages, max_tokens=1500)
        data = json.loads(raw)
        items_raw = data.get("items", [])
        items = [
            StudyPlanItem(
                document_id=it.get("document_id", ""),
                document_title=it.get("document_title", ""),
                reason=it.get("reason", ""),
                priority=int(it.get("priority", 99)),
            )
            for it in items_raw
            if it.get("document_id")
        ]
        items.sort(key=lambda x: x.priority)
    except Exception:
        # Fallback: rank all documents, weakest-first heuristic
        items = [
            StudyPlanItem(
                document_id=d.id,
                document_title=d.title,
                reason="根据文档内容建议复习" if not weak else "与薄弱知识点相关，建议优先复习",
                priority=i + 1,
            )
            for i, d in enumerate(documents)
        ]

    return StudyPlan(items=items, generated_at=_utcnow_iso())
