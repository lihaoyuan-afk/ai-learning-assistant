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

### 项目中的完整 RAG 管线

```
用户问题
  ↓
decide_retrieval(tool calling)   → LLM 判断是否需要检索，并精炼查询词
  ↓ needs_retrieval=True
embed_text(refined_query)        → 生成 768 维向量
  ↓
Qdrant.search(limit=15)          → 向量相似度召回候选
  ↓
BM25 重排                        → 综合分 = 0.7×向量 + 0.3×BM25，取 Top 5
  ↓
构造 prompt                      → "[第3页] 文本片段 ... 问题: ..."
  ↓
LLM 生成回答                     → 含来源页码
  ↓
reflect（质量检测）               → 回退信号 → 扩大召回重试一次
```

### 常见面试问题

**Q: RAG 和 Fine-tuning 的区别？**
A: RAG 是推理时检索外部知识，无需训练，适合知识频繁变化的场景。Fine-tuning 是把领域知识烧进模型权重，推理更快但更新成本高，适合风格/格式定制。

**Q: 如何提升 RAG 检索质量？**
A: ①更好的分块策略（语义分块）②混合检索（向量+BM25）③查询改写（本项目用工具调用让 LLM 精炼查询词）④重排模型（Reranker）⑤增大 TopK 再精筛。

---

## 2. LLM 工具调用（Function Calling）

### 是什么

Function Calling / Tool Use 是让 LLM 在生成文本的同时，输出一个结构化的"工具调用"指令。调用方解析这个指令、执行对应函数、把结果返回给 LLM，实现 LLM 驱动的动态决策。

### 和直接 if/else 路由的区别

| | 显式路由（if/else） | 工具调用路由 |
| --- | --- | --- |
| 决策者 | 代码逻辑 | LLM |
| 适用场景 | 规则明确、边界清晰 | 意图模糊、需要语言理解 |
| 可扩展性 | 需要改代码 | 只需增加工具描述 |
| 可靠性 | 确定性高 | 需要降级兜底 |

### 项目中的实现

`decide_retrieval()` 函数调用两个工具：

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_and_answer",
            "description": "需要查阅文档内容才能回答时调用（事实/数据/方法等）",
            "parameters": {
                "properties": {
                    "refined_query": {  # LLM 精炼后的检索词
                        "type": "string",
                        "description": "去除口语化表达，保留核心关键词，有利于语义检索"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "answer_directly",
            "description": "打招呼、闲聊、或纯粹常识问题时调用，不需要查文档"
        }
    }
]
```

返回值处理：

```python
def decide_retrieval(question: str) -> tuple[bool, str]:
    try:
        response = client.chat.completions.create(
            model=..., messages=..., tools=tools, tool_choice="required"
        )
        call = response.choices[0].message.tool_calls[0]
        if call.function.name == "answer_directly":
            return False, ""
        args = json.loads(call.function.arguments)
        return True, args.get("refined_query", question)
    except Exception:
        return True, question  # 安全降级：失败时始终检索
```

**关键设计**：`refined_query` 让 LLM 在做路由决策的同时顺带优化检索词，一次调用同时完成两件事。

### 常见面试问题

**Q: 什么时候该用工具调用，什么时候直接 if/else？**
A: 规则确定的逻辑用 if/else（比如 `retry_count >= MAX_RETRIES` 就停止），意图判断用工具调用（比如"这个问题需不需要查文档"——代码无法硬编码所有可能的问题类型）。本项目里两者都有：工具调用做意图路由，if/else 做终止条件控制。

**Q: 工具调用失败了怎么办？**
A: `try/except` 兜底，失败时默认走检索路径。检索路径是安全的（多出一次 LLM 调用但结果正确），直接回答路径才是风险路径（可能缺少文档依据），所以默认走"保守"的那条。

**Q: refined_query 有实际效果吗？**
A: 有。用户问"帮我解释一下这个"时，直接用原问题向量检索效果很差，因为"这个"没有任何语义。LLM 理解上下文后可以生成"上文提到的 YOLOv8 检测头结构"这样的精炼词，检索质量显著提升。

---

## 3. 向量数据库（Qdrant）

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
    limit=15,  # 多召回用于 BM25 重排
)

# 删除（按 payload 过滤，用于删除文档时清理向量）
client.delete(collection_name=..., points_selector=FilterSelector(
    filter=Filter(must=[FieldCondition(...)])
))
```

### 常见面试问题

**Q: 为什么用向量数据库而不是关系数据库存 embedding？**
A: 关系数据库做相似度搜索需要全表扫描计算余弦距离，O(n) 复杂度。Qdrant 用 HNSW 图索引，近似最近邻搜索复杂度接近 O(log n)，百万级向量毫秒响应。

---

## 4. LangGraph

### 是什么

LangGraph 是 LangChain 团队的有向状态图框架，用来编排 LLM Agent 的多步骤工作流。相比简单的链式调用，支持条件分支、循环和状态持久化。

### 核心概念

| 概念 | 说明 |
| --- | --- |
| StateGraph | 状态图，所有节点共享同一个 TypedDict 状态 |
| Node | 函数，接收 state → 返回 state 的部分更新 dict |
| Edge | 节点间的有向边 |
| Conditional Edge | 根据 state 中的值动态决定下一个节点 |
| END | 终止节点，图执行完毕 |

### 项目中的完整 Chat Graph

```python
# 状态定义（全部字段）
class AgentState(TypedDict, total=False):
    document_id: str
    question: str
    chunks: list[SourceChunk]
    result: str
    error: str
    history: list[dict]       # 多轮对话历史
    needs_retrieval: bool     # decide 节点工具调用结果
    refined_query: str        # LLM 精炼的检索词
    reflection: str           # "answer_ok" | "answer_insufficient"
    retry_count: int          # 已重试次数，上限 MAX_RETRIES=1

# 图结构
decide → route_after_decide
    ↓ True                         ↓ False
retrieve(refined_query)         direct_answer
    ↓                               ↓
answer                             END
    ↓
reflect → route_after_reflect
    ↓ answer_insufficient          ↓ answer_ok
retrieve(limit=8)                 END
    ↓
answer → reflect → END（第二次必定结束）
```

```python
# 关键路由函数
def _route_after_decide(state: AgentState) -> str:
    return "retrieve" if state.get("needs_retrieval", True) else "direct_answer"

def _route_after_reflect(state: AgentState) -> str:
    if state.get("reflection") == "answer_insufficient":
        return "retrieve"  # 重试，但 retry_count 已+1，下次 reflect 会终止
    return END
```

### 常见面试问题

**Q: LangGraph 和普通函数链有什么区别？**
A: 函数链是线性的，LangGraph 支持循环和条件路由，能实现 Reflection 重试、工具调用路由等复杂 Agent 模式。状态图让执行路径可追溯、可测试——每个节点独立，单元测试直接注入 state 就能测单个节点。

**Q: 如何防止 Agent 无限循环？**
A: 在 State 中维护 `retry_count`，节点每次重试前 +1，路由函数判断 `retry_count >= MAX_RETRIES` 时强制走向 END。终止条件必须在设计阶段就确定，不能等出问题再补。

**Q: decide 节点的工具调用和 Reflection 节点有什么区别？**
A: decide 是入口路由，基于 LLM 判断"需不需要检索"，属于意图理解；reflect 是出口质检，基于规则判断"答案质量够不够"，属于确定性逻辑。前者适合工具调用（LLM 做），后者适合 if/else（代码做）。

---

## 5. SSE 流式输出

### 是什么

SSE（Server-Sent Events）是一种单向的服务器推送协议，服务器可以持续向客户端发送事件流，客户端不需要轮询。

### 协议格式

```
data: {"type": "token", "content": "你"}\n\n
data: {"type": "token", "content": "好"}\n\n
data: {"type": "cached"}\n\n    ← 总结命中缓存时发送
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

总结缓存命中时的快速流出：

```python
# 30字符分块快速回放，先发cached事件
yield f"data: {json.dumps({'type': 'cached'})}\n\n"
for i in range(0, len(cached_text), 30):
    yield f"data: {json.dumps({'type': 'token', 'content': cached_text[i:i+30]})}\n\n"
yield f"data: {json.dumps({'type': 'done'})}\n\n"
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
        if (event.type === "cached") setIsCached(true);
    }
}
```

### 常见面试问题

**Q: SSE 和 WebSocket 的区别？**
A: SSE 是单向（服务器→客户端），基于 HTTP，浏览器原生支持，自动重连。WebSocket 是双向全双工，需要握手升级协议。对话流式输出场景用 SSE 更简单，不需要双向通信。

---

## 6. Embedding 与语义分块

### Embedding

将文本转换为固定维度的稠密向量，语义相近的文本在向量空间中距离近。

本项目用 `nomic-embed-text`（768 维），通过 Ollama 本地推理，batch 写入（每批 20 个）避免大文件超时。

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
3. 段落 > `max_chars` → 字符切割，前一块末尾保留 `overlap` 字符
4. **块末小尾部只与同页块合并**（跨页合并会导致页码错误，这是一个易踩的 bug）

---

## 7. BM25 混合检索

### BM25 是什么

BM25（Best Match 25）是经典的关键词相关性排序算法，TF-IDF 的改进版。词频高但文档很短的词得分高，避免长文档优势。

### 项目中的 Hybrid Search

```python
# 多召回：向量召回 3× 候选供重排用
candidates = vector_store.search(doc_id, query_vector, limit=15)

# BM25 重排
corpus = [c.content.split() for c in candidates]
bm25 = BM25Okapi(corpus)
bm25_scores = bm25.get_scores(query.split())

# 归一化后加权融合
final_scores = 0.7 * vector_score_normalized + 0.3 * bm25_score_normalized
return sorted(candidates, key=final_scores, reverse=True)[:limit]
```

`rank_bm25` 不可用时（`ImportError`）自动降级为纯向量检索，服务不中断。

### 常见面试问题

**Q: 纯向量检索有什么不足？**
A: 向量检索捕捉语义相似，但对精确关键词不敏感。比如查询"mAP@0.5"，向量检索可能返回泛泛的性能讨论，而 BM25 会优先返回包含这个精确术语的段落。混合搜索结合两者优势。

---

## 8. 间隔重复（SRS）

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
_WRONG_DELTA = -15     # 答错扣分（错误惩罚更重，迫使认真复习）
_INITIAL_SCORE = 50    # 新知识点初始分

def _schedule_next_review(score: int, from_dt: datetime) -> datetime:
    if score < 40:  return from_dt + timedelta(days=2)
    if score < 70:  return from_dt + timedelta(days=5)
    return from_dt + timedelta(days=14)
```

---

## 9. 项目常见追问与参考回答

**Q: 这个项目解决了什么问题？**
A: 传统学习方式中，看完 PDF 后缺乏主动检验和记忆巩固手段。这个系统把文档理解、自测、错题分析、复习规划整合到一个 AI 闭环里，让用户从"阅读"升级为"掌握"。

**Q: 为什么选 LangGraph 而不是直接写 Python 函数链？**
A: 函数链是线性的，无法表达循环。我的 Reflection 重试和工具调用路由本质上都是有状态的条件分支，LangGraph 的状态图让这些路径清晰可测试。每个节点独立，单元测试直接注入状态就能测单个节点。

**Q: 工具调用和 Reflection 节点，哪个对质量提升更大？**
A: 两者解决不同问题。工具调用解决"无效检索"问题——闲聊问题不应该进 RAG；Reflection 解决"检索不足"问题——进了 RAG 但文档里找不到时自动扩大范围。两者配合，先过滤无效请求，再对有效请求保底重试。

**Q: 项目中遇到的最难的技术问题是什么？**
A: 小模型（1.5B）几乎无法稳定输出合法 JSON，花了很多时间在 `_extract_json`、`_strip_think`、`response_format` 降级和 fallback 解析策略上。这让我理解了 AI 工程中"LLM 输出不可信"的核心挑战，以及为什么工业界用 structured output / function calling 强制格式。

**Q: 系统的主要局限性？**
A: ①单用户，没有认证；②掌握度评分是简单线性加减，没有时间衰减；③工具调用路由依赖 qwen2.5:7b，弱模型可能路由错误；④Docker 镜像构建依赖 PyMuPDF 系统依赖，构建较慢。

**Q: 如果要支持多用户，你会怎么改？**
A: ①所有 DB 表加 `user_id` 外键；②Qdrant payload 加 `user_id` 过滤；③FastAPI 加 JWT 认证中间件；④chat history 从 localStorage 改为后端 DB 存储（按 user_id + document_id 隔离）。

**Q: 你用 Claude Code 具体怎么配合开发的？**
A: 我把每个功能点拆成独立任务交给 Claude Code，但架构决策、模块边界、测试策略都是我先想清楚再执行。比如 Function Calling 节点，我描述设计意图，它给出实现后，我发现 mock LLM 返回字符串太短会误触发 Reflection 重试——这个边界判断是我做的，让它修 conftest 而不是改业务逻辑。大的取舍（工具调用 vs 显式路由、BM25 权重选 0.3 而不是 0.5）都是我自己权衡后拍板的。
