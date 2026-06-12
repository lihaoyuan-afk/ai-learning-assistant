"""Extract concept relationships from document chunks and return a graph structure."""

import json

from app.schemas.document import SourceChunk


def extract_knowledge_graph(
    document_id: str,
    chunks: list[SourceChunk],
) -> dict:
    """Call LLM to extract concepts and relationships from document chunks.

    Returns a dict with:
      nodes: list of {id, label, type}
      edges: list of {source, target, label}
    """
    if not chunks:
        return {"nodes": [], "edges": []}

    # Use up to 8 chunks to keep the prompt manageable
    sample = chunks[:8]
    context = "\n\n".join(
        f"[第{c.page_number or '?'}页] {c.content[:400]}" for c in sample
    )

    prompt = f"""请分析以下文档片段，提取其中的核心概念和它们之间的关系，以 JSON 格式返回知识图谱。

文档片段：
{context}

请按以下 JSON 格式返回（不要有额外说明文字）：
{{
  "nodes": [
    {{"id": "概念唯一标识（英文或拼音，无空格）", "label": "概念名称（中文）", "type": "concept|term|method|theory"}}
  ],
  "edges": [
    {{"source": "来源概念id", "target": "目标概念id", "label": "关系描述（如：包含、依赖、对比、应用于）"}}
  ]
}}

要求：
- 提取 5-15 个最重要的概念节点
- 提取 5-20 条关系边
- 确保 source 和 target 都是 nodes 中存在的 id
- 关系标签简短（2-6 字）"""

    from app.services.llm import call_chat_json
    raw = call_chat_json(
        [{"role": "user", "content": prompt}],
        max_tokens=2000,
    )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"nodes": [], "edges": [], "error": "LLM returned invalid JSON"}

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    # Validate: only keep edges where both source and target are valid node IDs
    node_ids = {n.get("id") for n in nodes if n.get("id")}
    valid_edges = [
        e for e in edges
        if e.get("source") in node_ids and e.get("target") in node_ids
    ]

    return {"nodes": nodes, "edges": valid_edges, "document_id": document_id}
