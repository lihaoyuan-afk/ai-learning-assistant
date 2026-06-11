# AI 学习助手——项目介绍

## 项目概述

这是一个基于大语言模型（LLM）和 RAG（检索增强生成）技术构建的个人 AI 学习操作系统。用户上传 PDF 学习资料后，系统能自动完成内容解析、智能问答、结构化总结、Quiz 出题、错题分析与复习计划生成，全程由 AI Agent 驱动，帮助用户将被动阅读转化为主动学习闭环。

项目从零开始独立设计与实现，历时约两周，覆盖从后端 AI 服务到前端交互的完整全栈开发。

---

## 核心功能

| 功能 | 说明 |
| --- | --- |
| PDF 解析与向量化 | 上传 PDF 后自动提取文本、语义分块、生成 embedding，写入本地 Qdrant 向量库 |
| 智能问答（RAG） | 基于文档内容回答问题，回答附带原文页码来源，支持多轮对话上下文 |
| 文档总结 | LLM 生成四节结构化总结（概述/核心概念/主要内容/学习要点），结果缓存复用 |
| Quiz 自动出题 | LLM 生成含答案/解析/知识点的多题型测验，支持历史记录查阅 |
| 掌握度追踪 | 答题后自动更新各知识点掌握度评分（0-100），记录对错次数 |
| 间隔复习计划 | 基于掌握度自动安排复习时间（弱点 2 天/中等 5 天/已掌握 14 天）|
| AI 学习规划 | Agent 分析薄弱知识点，生成优先级排序的文档学习计划 |
| 跨文档全局搜索 | 跨所有已上传文档进行语义检索，支持多轮追问 |

---

## 技术架构

```
┌─────────────────────────────────────────────────────┐
│                    前端 (Next.js 15)                 │
│  文档管理 · 问答气泡 · 总结流式 · Quiz · 画像 · 全局搜索  │
└──────────────────────┬──────────────────────────────┘
                       │  HTTP / SSE
┌──────────────────────▼──────────────────────────────┐
│                  后端 (FastAPI + Python 3.12)         │
│                                                     │
│  ┌─────────────┐   ┌────────────────────────────┐   │
│  │  LangGraph  │   │     REST API 路由层          │   │
│  │  Agent 图   │   │ documents / chat / summary  │   │
│  │  (有状态图) │   │ quiz / profile / search     │   │
│  └──────┬──────┘   └──────────────┬─────────────┘   │
│         │                         │                  │
│  ┌──────▼─────────────────────────▼─────────────┐   │
│  │              核心服务层                        │   │
│  │  embeddings · retrieval(BM25+vector) · llm   │   │
│  │  chunker · mastery_service · planning_service │   │
│  └──────────────────────────────────────────────┘   │
└────────────┬──────────────────┬──────────────────────┘
             │                  │
    ┌────────▼───────┐  ┌───────▼────────┐
    │  SQLite / PG   │  │  Qdrant 向量库  │
    │ 文档/Quiz/掌握度 │  │ chunk embeddings│
    └────────────────┘  └────────────────┘
```

### 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Next.js 15、React 19、TypeScript |
| 后端 | Python 3.12、FastAPI、Pydantic v2 |
| AI 编排 | LangGraph（有向状态图，支持条件路由与循环） |
| 向量数据库 | Qdrant（本地文件模式 / Docker 模式） |
| 关系数据库 | SQLite（开发）/ PostgreSQL（生产） |
| LLM | Ollama 本地推理（qwen2.5:7b）/ OpenAI 兼容 API |
| Embeddings | nomic-embed-text（768 维） |
| 测试 | pytest · 95 个测试 · 全离线（内存 Qdrant + mock LLM）|

---

## 核心 AI 设计亮点

### 1. LLM 工具调用（Function Calling）路由

Chat Agent 的入口节点 `decide` 通过工具调用让 LLM **自主决定**是否需要检索文档，并同步精炼查询词：

```python
tools = [
    {"name": "retrieve_and_answer",  # 需要查文档时调用，携带 refined_query
     "description": "需要查阅文档内容时调用，适用于事实/数据/方法等问题"},
    {"name": "answer_directly",      # 不需要文档时调用（闲聊/常识）
     "description": "不需要查文档即可回答时调用"},
]
```

`refined_query` 是工具调用返回的精炼检索词（去除口语化表达，保留核心关键词），直接传入 Qdrant 检索，提升召回质量。工具调用失败时安全降级为始终检索，不中断服务。

### 2. 完整的有状态 Chat Graph

结合工具调用路由、RAG 检索与 Reflection 自我反思，Chat Graph 形成完整的 Agent 决策环路：

```
decide(tool calling)
    ↓ needs_retrieval=True             ↓ needs_retrieval=False
retrieve(refined_query, limit=5)    direct_answer
    ↓                                   ↓
answer                                 END
    ↓
reflect（检测回退信号）
    ↓ answer_insufficient              ↓ answer_ok
retrieve(limit=8, 扩大召回)            END
    ↓
answer → reflect → END（最多重试1次）
```

三类节点各司其职：`decide` 负责工具调用路由，`reflect` 负责质量自检与重试，`retry_count` 上限防止无限循环。

### 3. RAG 管线 + BM25 混合重排

向量检索后对候选文本进行 BM25 二次排序：

```
综合分 = 0.7 × cosine_similarity + 0.3 × bm25_score
```

向量召回 3× 候选（15 个），BM25 精筛到 Top 5。相比纯向量检索，在精确关键词查询（如专有名词、指标数据）下准确率明显提升。`rank-bm25` 不可用时自动降级，不影响服务可用性。

### 4. 语义分块

彻底替换固定长度分块：按段落边界（`\n\n`）切块，过长段落再做字符级 overlap 分割，相邻小尾部仅在同一页内合并，保证语义完整性和页码准确性。

### 5. 流式 SSE 输出

问答和总结均使用 SSE（Server-Sent Events）流式推送。总结有缓存时以 30 字符分块快速回放并发送 `{"type":"cached"}` 事件，无缓存时 LLM 流式生成后自动存库，前端区分两种体验。

### 6. 掌握度 + 间隔复习（SRS）

每次 Quiz 答题后按知识点更新评分：答对 +8，答错 -15，新知识点初始 50 分。评分触发不同复习间隔（2/5/14 天），实现类 Anki 的间隔重复效果。

### 7. 学习规划 Agent

调用 LLM 综合掌握度弱点和文档列表，生成优先级排序的个性化学习计划。JSON 解析失败时降级为启发式排序，不中断用户流程。

---

## 工程亮点

### 全面的测试覆盖

**95 个 pytest 测试**，全部离线，CI 可直接运行：

| 测试文件 | 覆盖内容 |
| --- | --- |
| test_upload | 文档上传/解析/状态管理 |
| test_vector_store | 向量写入/检索/删除（内存 Qdrant）|
| test_chat / test_summary / test_quiz | LLM 路由层（全量 mock）|
| test_graph | LangGraph 三条图状态转换 |
| test_tool_calling | Function Calling：路由/精炼查询/降级/direct_answer 路径 |
| test_phase5 | 删除文档/SSE 流式/多轮对话/全局搜索 |
| test_mastery / test_review | 掌握度更新/间隔复习 |
| test_plan | 学习规划 schema/降级/mock LLM |

### 可靠的错误处理

- **上传层**：扩展名/文件大小/损坏文件三重校验
- **后端恢复**：服务重启时自动将中断的 `processing` 文档标记为 `failed`
- **LLM 层**：deepseek-r1 `<think>` 标签剥离；JSON 模式降级；工具调用失败安全回退
- **Agent 层**：每个 LangGraph 节点独立 try/except，错误写入状态而非中断图

### 前端体验细节

- 异步上传：立即返回，前端每 2.5 秒轮询状态
- 多轮对话 localStorage 持久化（刷新不丢失）
- SSE 来源折叠展示（`<details>` 折叠避免干扰阅读）
- 文档详情按状态灰显/启用功能入口

### Docker Compose 可部署

`infra/docker-compose.yml` 包含 postgres、qdrant、redis、api 四个服务，所有服务带 healthcheck，API 服务 `depends_on: condition: service_healthy`，一键启动整套生产等效环境。

---

## 项目规模

| 指标 | 数值 |
| --- | --- |
| 后端代码 | ~3,200 行 Python |
| 前端代码 | ~2,500 行 TypeScript/TSX |
| 测试用例 | 95 个（全离线，全通过）|
| API 端点 | 19 个 |
| 前端页面/路由 | 11 个 |
| 技术文档 | 6 份（架构/API/Agent工作流/数据模型/项目介绍/面试笔记）|
| 开发周期 | ~2 周（独立完成）|

---

## 我的技术成长

这个项目最大的收获不是堆砌功能，而是在真实工程问题中理解 AI 系统的取舍：

- **Function Calling 的价值：** 最初路由是硬编码的，后来加了 decide 节点让 LLM 自主决策。这不只是技术升级，更让我理解了"让模型做判断"和"让代码做判断"各自适用的边界——工具调用适合意图判断，显式路由适合确定性逻辑。
- **为什么要 refined_query：** 用户问"帮我解释一下这个"时，直接用原问题检索效果很差。工具调用让 LLM 在决策的同时顺带精炼检索词，一次 LLM 调用同时完成两件事，这是工具调用相比普通路由的额外价值。
- **Reflection 终止条件是第一公民：** LangGraph 条件路由如果没有 `retry_count` 上限，理论上可以无限重试。设计有状态 Agent 时，我学到的最重要的一条原则是：终止条件必须在设计阶段就确定，不能等到出问题再补。
- **小模型的限制与应对：** 本机 1.5B 参数模型几乎无法稳定输出合法 JSON，换 7B 后质量跃升。这让我理解了模型规模、上下文窗口（num_ctx）对工程可靠性的实际影响，以及为什么工业界用 structured output 强制格式。
- **为什么先跑通再优化：** 项目一开始 LLM 层是占位实现，但架构分层做好了，后来替换真实模型时只改了一两个文件，其余测试无需改动。这让我真正理解了"接缝在哪"的重要性。
