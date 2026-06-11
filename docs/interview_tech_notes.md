# 面试技术复习笔记

> 本文档整理项目中用到的核心技术点，供面试前快速回顾。

---

## 1. RAG（检索增强生成）

### 是什么

RAG = Retrieval-Augmented Generation。不直接让 LLM 凭训练知识回答，而是先从外部知识库检索相关片段，把片段塞进 prompt，再让 LLM 根据片段生成回答。

### 核心好处

- 回答有据可查，可附带来源页码
- 不需要微调模型，换文档即换知识
- 幻觉（hallucination）更少，因为 LLM 有参考上下文

### 项目中的 RAG 管线

```
用户问题
  ↓
embed_text(question)   → 生成 768 维向量
  ↓
Qdrant.search()        → 向量相似度召回 TopK 候选
  ↓
BM25 重排              → 综合分 = 0.7×向量 + 0.3×BM25
  ↓
构造 prompt            → "[第3页] 文本片段 ... 问题: ..."
  ↓
LLM 生成回答           → 含来源页码
```

### 常见面试问题

**Q: RAG 和 Fine-tuning 的区别？**
A: RAG 是推理时检索外部知识，无需训练，适合知识频繁变化的场景。Fine-tuning 是把领域知识烧进模型权重，推理更快但更新成本高，适合风格/格式定制。

**Q: 如何提升 RAG 检索质量？**
A: ①更好的分块策略（语义分块）②混合检索（向量+BM25）③重排模型（Reranker）④查询改写（HyDE）⑤增大 TopK 再精筛。

---

## 2. 向量数据库（Qdrant）

### 核心概念

| 概念 | 说明 |
| --- | --- |
| Collection | 类比关系数据库的"表"，存一类向量 |
| Point | 一条记录，包含 id、vector、payload（元数据）|
| Payload | 任意 JSON，可按字段过滤（如 document_id）|
| Distance | 向量相似度度量，本项目用 Cosine |

### 项目中的关键操作

```python
# 写入
client.upsert(collection_name=..., points=[
    PointStruct(id=..., vector=embedding, payload={"document_id": ..., "page": ...})
])

# 检索（含过滤）
client.query_points(
    collection_name=...,
    query=query_vector,
    query_filter=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=doc_id))]),
    limit=5,
)

# 删除（按 payload 过滤）
client.delete(collection_name=..., points_selector=FilterSelector(
    filter=Filter(must=[FieldCondition(...)])
))
```

### 常见面试问题

**Q: 为什么用向量数据库而不是关系数据库存 embedding？**
A: 关系数据库做相似度搜索需要全表扫描计算余弦距离，O(n) 复杂度。Qdrant 用 HNSW 图索引，近似最近邻搜索复杂度接近 O(log n)，百万级向量毫秒响应。

---

## 3. LangGraph

### 是什么

LangGraph 是 LangChain 团队的有向状态图框架，用来编排 LLM Agent 的多步骤工作流。相比简单的链式调用，支持条件分支、循环和状态持久化。

### 核心概念

| 概念 | 说明 |
| --- | --- |
| StateGraph | 状态图，节点共享同一个 TypedDict 状态 |
| Node | 函数，接收 state → 返回 state 的部分更新 |
| Edge | 节点间的有向边 |
| Conditional Edge | 根据 state 中的值动态决定下一个节点 |
| END | 终止节点 |

### 项目中的 Chat Graph

```python
# 状态定义
class AgentState(TypedDict, total=False):
    document_id: str
    question: str
    chunks: list[SourceChunk]
    result: str
    reflection: str     # "answer_ok" | "answer_insufficient"
    retry_count: int

# 图结构
retrieve → answer → reflect → [END | retrieve(retry)]

# 条件路由
def _route_after_reflect(state) -> str:
    if state.get("reflection") == "answer_insufficient":
        return "retrieve"   # 重试
    return END
```

### 常见面试问题

**Q: LangGraph 和普通函数链（LangChain）有什么区别？**
A: 函数链是线性的，LangGraph 支持循环和条件路由，能实现 Reflection（自我反思重试）、ReAct（思考-行动循环）等复杂 Agent 模式。状态图让 Agent 的执行路径可追溯、可测试。

**Q: 如何防止 Agent 无限循环？**
A: 在 State 中维护 `retry_count`，Reflection 节点判断 `retry_count >= MAX_RETRIES` 时强制走向 END，而不是继续重试。

---

## 4. SSE 流式输出

### 是什么

SSE（Server-Sent Events）是一种单向的服务器推送协议，服务器可以持续向客户端发送事件流，客户端不需要轮询。

### 协议格式

```
data: {"type": "token", "content": "你"}\n\n
data: {"type": "token", "content": "好"}\n\n
data: {"type": "done"}\n\n
```

每个事件以 `data:` 开头，两个 `\n` 作为分隔符。

### 项目后端实现（FastAPI）

```python
def event_stream():
    for chunk in stream_answer_question(question, chunks):
        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"

return StreamingResponse(event_stream(), media_type="text/event-stream")
```

### 项目前端实现（React）

```typescript
const reader = response.body!.getReader();
const decoder = new TextDecoder();
let buf = "";

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
        const json = part.trim().slice(5); // 去掉 "data:"
        const event = JSON.parse(json);
        if (event.type === "token") setContent(prev => prev + event.content);
    }
}
```

### 常见面试问题

**Q: SSE 和 WebSocket 的区别？**
A: SSE 是单向（服务器→客户端），基于 HTTP，浏览器原生支持，自动重连。WebSocket 是双向全双工，需要握手升级协议。对话流式输出场景用 SSE 更简单，不需要双向通信。

---

## 5. Embedding 与语义分块

### Embedding

将文本转换为固定维度的稠密向量，语义相近的文本在向量空间中距离近。

本项目用 `nomic-embed-text`（768 维），通过 Ollama 本地推理。

```python
def embed_text(text: str) -> list[float]:
    response = client.embeddings.create(model="nomic-embed-text", input=[text])
    return response.data[0].embedding  # 768 维
```

### 语义分块策略

| 方法 | 问题 |
| --- | --- |
| 固定字符切块 | 可能在句中断开，破坏语义 |
| 语义分块（本项目） | 按段落边界（双换行）切，语义完整 |

本项目的分块逻辑：
1. 按 `\n{2,}` 分割段落
2. 段落 < `max_chars` → 合并到当前块
3. 段落 > `max_chars` → 字符切割，前一块末尾保留 `overlap` 字符作为下一块开头
4. 块末小尾部只与同页块合并（保证页码准确）

---

## 6. BM25 混合检索

### BM25 是什么

BM25（Best Match 25）是经典的关键词相关性排序算法，TF-IDF 的改进版。词频高但文档很短的词得分高，避免长文档优势。

### 项目中的 Hybrid Search

```python
# 向量召回 3× 候选
candidates = vector_store.search(doc_id, query_vector, limit=15)

# BM25 重排
corpus = [c.content.split() for c in candidates]
bm25 = BM25Okapi(corpus)
query_tokens = query.split()
bm25_scores = bm25.get_scores(query_tokens)

# 归一化后加权融合
final_scores = 0.7 * vector_score_normalized + 0.3 * bm25_score_normalized
```

### 常见面试问题

**Q: 纯向量检索有什么不足？**
A: 向量检索捕捉语义相似，但对精确关键词不敏感。比如查询"mAP@0.5"，向量检索可能返回泛泛的性能讨论，而 BM25 会优先返回包含这个精确术语的段落。混合搜索结合两者优势。

---

## 7. 间隔重复（SRS）

### 原理

遗忘曲线（Ebbinghaus）：复习间隔越短，遗忘越少；随着记忆巩固，间隔可以拉长。

| 掌握度 | 复习间隔 | 逻辑 |
| --- | --- | --- |
| < 40%（弱） | 2 天 | 频繁复习巩固 |
| 40-70%（中） | 5 天 | 稳固后适当拉长 |
| ≥ 70%（强） | 14 天 | 长期记忆，低频维护 |

### 项目实现

```python
_CORRECT_DELTA = +8    # 答对加分
_WRONG_DELTA = -15     # 答错扣分
_INITIAL_SCORE = 50    # 新知识点初始分

def _schedule_next_review(score: int, from_dt: datetime) -> datetime:
    if score < 40:   return from_dt + timedelta(days=2)
    if score < 70:   return from_dt + timedelta(days=5)
    return           from_dt + timedelta(days=14)
```

---

## 8. 项目常见追问与参考回答

**Q: 这个项目解决了什么问题？**
A: 传统学习方式中，看完 PDF 后缺乏主动检验和记忆巩固手段。这个系统把文档理解、自测、错题分析、复习规划整合到一个 AI 闭环里，让用户从"阅读"升级为"掌握"。

**Q: 为什么选 LangGraph 而不是直接写 Python 函数链？**
A: 函数链无法表达条件分支和循环。LangGraph 的状态图让 Reflection 重试、错误降级这些复杂路径变得清晰可测试。每个节点独立，单元测试可以直接注入状态测试单个节点。

**Q: 项目中遇到的最难的技术问题是什么？**
A: 小模型（1.5B）几乎无法稳定输出合法 JSON，花了很多时间在 `_extract_json`、`_strip_think`、`response_format` 降级和多种 fallback 解析策略上。这让我理解了 AI 工程中"LLM 输出不可信"的核心挑战，以及为什么工业界通常用 structured output / function calling 强制格式。

**Q: 系统的主要技术债或局限性？**
A: ①目前没有用户认证，是单用户系统；②掌握度评分是简单的加减法，没有考虑时间衰减（遗忘）；③Reflection 重试只有 1 次，更复杂的 Agent 可以做多次反思和查询改写；④Docker 镜像构建依赖 PyMuPDF 的系统依赖，构建较慢。

**Q: 如果要支持多用户，你会怎么改？**
A: ①所有 DB 表加 `user_id` 外键；②Qdrant payload 里加 `user_id` 过滤；③FastAPI 加 JWT 认证中间件（用 `fastapi-users` 或自己实现）；④会话隔离后，chat history 从 localStorage 改为后端存储。
