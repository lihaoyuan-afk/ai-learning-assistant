# Agent 学习助手项目进度记录

## 2026-06-03

- 读取并理解了桌面上的学习计划文档。
- 确认当前项目目录为空。
- 创建项目长期推进用的计划、发现、进度记录文件。
- 开始整理优化后的项目骨架。
- 完成优化后的项目骨架文档，包含产品定位、主流程、技术栈、工程目录、前后端模块、Agent 划分、数据模型、MVP 边界、API 骨架和学习路线。
- 按用户要求创建 `E:\codex` 作为新的项目存储位置，并将原 `C:\Users\86157\Documents\agentlearn` 中的项目文件迁移到 `E:\codex`。
- 更新 Codex 配置，将项目受信任路径从原 C 盘目录调整为 `E:\codex`。
- 基于项目骨架创建第一版代码结构：Next.js 前端、FastAPI 后端、shared 包、docs 参考文档、infra 本地基础设施配置和 uploads 目录。
- 将桌面原始学习计划备份到 `docs/reference/original_learning_plan.md`，并保留 `PROJECT_SKELETON.md` 作为根目录参考。
- 安装前端依赖并完成 Next.js 生产构建检查，构建通过。
- 创建后端虚拟环境并安装 FastAPI/LangGraph/Qdrant/PyMuPDF 等依赖，`pytest` 健康检查通过。
- 启动本地服务：前端 `http://127.0.0.1:3000`，后端 `http://127.0.0.1:8000`。
- npm audit 当前提示 Next 传递依赖 `postcss@8.4.31` 存在 2 个中等风险项；`npm audit fix --force` 会破坏性降级 Next，因此暂未强制修复。

## 2026-06-04

- 创建根目录 `CLAUDE.md`，用于帮助 Claude Code 接手项目。
- 交接文档记录了项目目标、真实工作目录、当前状态、占位实现、运行命令、已知风险、工作原则和推荐下一步。
- 确认交接时前端和后端服务均未运行，项目仍未初始化 Git。

## 2026-06-04（Phase 1 实现完成）

### Step 1：文档上传与解析闭环

- `document_parser.py`：加入 `DocumentParseError`，非 PDF / 损坏文件统一抛出异常。
- `ingest_document.py`：上传前校验扩展名、空文件、文件大小（默认 50MB 限制）；解析失败自动将文档状态更新为 `failed`。
- `routes_documents.py`：校验失败返回 HTTP 400 + 明确错误信息；解析失败返回文档 + `failed` 状态 + 错误描述。
- `config.py`：新增 `max_upload_size_mb` 配置项。
- 新增测试：`test_parser.py`（6 项）、`test_chunker.py`（6 项）、`test_upload.py`（7 项）。

### Step 2：Qdrant + 真实 embeddings

- `embeddings.py`：使用 Ollama `nomic-embed-text`（768 维），懒初始化客户端。
- `vector_store.py`：真实 Qdrant，使用 `query_points`（适配 qdrant-client 新 API），自动建集合，按 `document_id` 过滤检索。
- `retrieval.py`：向量检索替换关键词匹配。
- `conftest.py`：`in_memory_vector_store` + `mock_embeddings` autouse fixture，测试全程不需要真实服务。
- 新增测试：`test_vector_store.py`（6 项）。

### Step 3 + Step 4：LLM 问答 / 总结 / Quiz

- `llm.py`：`call_chat`、`call_chat_json`、`answer_question`（附带来源页码）。
- `summary_generator.py`：结构化 LLM 总结（概述 + 核心概念 + 主要内容 + 学习要点）。
- `quiz_generator.py`：JSON 模式生成 Quiz（多题型、含答案 / 解析 / 知识点），含 parse 失败降级处理。
- `routes_chat.py`：接入真实 `answer_question`。
- `routes_quiz.py`：传递 chunks 给 `generate_quiz`。
- `conftest.py`：`mock_llm` autouse fixture。
- 新增测试：`test_chat.py`（4 项）、`test_summary.py`（3 项）、`test_quiz.py`（6 项）。

### LangGraph 编排

- `graph.py`：实现 chat/summary/quiz 三条 LangGraph 图并接入路由。
- `state.py`：定义 `AgentState` TypedDict。
- 新增测试：`test_graph.py`（9 项）。

### 学习状态系统

- `mastery_service.py`：掌握度记录、间隔复习调度算法。
- `models/learning_memory.py`：知识点记录 ORM 模型。
- `routes_profile.py`：`/profile/mastery` 和 `/profile/review/today` 接口。
- 新增测试：`test_mastery.py`（6 项）、`test_review.py`（7 项）。

### 最终测试状态（Phase 1 完成时）

```
66 passed, 2 warnings in 1.74s
```

## 2026-06-10（全面修复与完善）

### 问题清查与修复

修复了以下影响真实运行的问题：

1. **`.env` 模型配置错误**：`OPENAI_CHAT_MODEL=qwen2.5:7b` 改为 `deepseek-r1:1.5b`（本机 Ollama 实际安装的模型）。新增 `OLLAMA_NUM_CTX=8192`。

2. **`llm.py` 重写**：
   - 新增 `_strip_think()` 剥离 deepseek-r1 输出的 `<think>…</think>` 推理块。
   - 新增 `_extract_json()` 从混合文本中提取 `{…}` JSON 块。
   - `call_chat_json` 增加 `response_format` 降级：若模型/服务不支持则静默回落到普通调用后提取 JSON。
   - 新增 `_ollama_extra()`，通过 `extra_body` 传递 `num_ctx=8192` 扩展上下文窗口。
   - 所有 LLM 调用加 `timeout=180s`。
   - `max_tokens` 默认值提升（chat 2000、json 3000）。

3. **`config.py`**：新增 `ollama_num_ctx: int = 8192` 和 `llm_timeout: int = 180`。

4. **`models/document.py`**：`file_path` 改为 `Mapped[str | None]`（nullable），修复磁盘写入失败时的潜在 IntegrityError。

5. **`agents/graph.py`**：每个节点用 try/except 包裹，失败时设置 `state["error"]` 而非直接抛出，保证图不会崩溃。

6. **`agents/state.py`**：新增 `error: str` 字段。

7. **路由层错误处理**：
   - `routes_chat.py`：新增文档状态保护（`status != "ready"` → 422），捕获图异常 → 500 with detail。
   - `routes_summary.py`：同上。
   - `routes_quiz.py`：同上。

8. **`summary_generator.py` / `quiz_generator.py`**：将传给 LLM 的内容从 `chunks[:30]`/`chunks[:20]` 缩减到 `chunks[:12]`/`chunks[:8]`，每 chunk 最多 400/500 字符，适配小模型有限的上下文窗口。

### 前端改进

9. **`app-shell.tsx`**：改为 `"use client"` 组件，使用 `usePathname` 高亮当前导航项。
10. **`globals.css`**：新增 `[aria-current="page"]` 样式。
11. **`status-pill.tsx`**：按状态文本自动选颜色（ready=绿、failed=红、processing=橙）。
12. **`documents/page.tsx`**：显示中文状态标签 + 日期格式化。
13. **`documents/[id]/page.tsx`**：文档未就绪时，功能卡片变灰且标注原因；解析失败时显示错误提示。
14. **`page.tsx`（首页）**：更新为功能卡片网格 + 快速开始步骤。

### 验证

- 所有 66 个测试继续通过（无新增失败）。
- Next.js 生产构建零错误零警告。

## 2026-06-10（代码完善）

### 三处改进

1. **`mastery_service.py`**：修复 `from uuid import uuid4` import 位置错误（原在函数定义之后）。
2. **`embeddings.py`**：新增 batch 处理（每批 20 个 chunk），避免大 PDF 上传时单次请求过大导致 Ollama 超时。
3. **`apps/web/app/documents/upload/page.tsx`**：上传处理期间显示进度提示（"正在生成向量索引，页数越多耗时越长"）。

### 验证

- 66 个测试继续通过
- 前端生产构建零错误

## 2026-06-10（方向一 + 方向二完成）

### 方向一：模型升级

- `qwen2.5:7b` 已下载并设为默认（`.env` `OPENAI_CHAT_MODEL=qwen2.5:7b`）。
- Quiz 生成成功率：1.5b 模型 0-1/6 → 7b 模型 **6/6**，32 秒完成。
- 题目质量：选择题答案准确，简答题有实质技术内容（CBAM 过拟合、Mosaic 增强等）。

### 方向二：异步文档处理

**后端**
- `routes_documents.py`：上传端点用 `BackgroundTasks`，立即返回 `status: uploaded`。
- `_run_ingest` 包装函数吸收异常（`ingest_document` 已将 DB 状态更新为 `failed`）。
- `main.py` lifespan：启动时将所有卡住的 `uploaded/processing` 文档重置为 `failed`。

**前端**
- `upload/page.tsx`：`useEffect` + `setInterval` 每 2.5 秒轮询文档状态，分三个阶段展示（处理中 / 就绪 / 失败）。
- `documents/page.tsx`：转为 Client Component，列表中有未完成文档时自动轮询刷新。

**测试**
- `test_upload.py`：新增 `_wait_for_final_status` 辅助函数，断言走 GET 轮询而非 POST 响应状态。
- `conftest.py`：`uploaded_doc_id` fixture 等待 `status == "ready"` 再返回 ID。
- 66 个测试全部通过。

### 验证结果（qwen2.5:7b）

| 功能 | 结果 |
| --- | --- |
| 异步上传返回时间 | 0.1 秒（之前 30-60 秒） |
| 毕业设计 PDF Quiz | 6/6 题，答案准确，简答题有深度 |
| Chat / Summary | 质量同步提升 |

## 2026-06-10（端到端验证完成）

### 测试 PDF

`C:\Users\86157\Desktop\毕业设计\李浩\（4）毕业设计说明书.pdf`（2874KB，麦田病虫害检测系统毕业设计）

### 验证结果

| 功能 | 状态 | 说明 |
| --- | --- | --- |
| PDF 上传 & 解析 | ✅ 通过 | 状态变为 ready，向量写入 Qdrant 本地存储 |
| 问答（RAG） | ✅ 通过 | 正确回答关于 YOLOv8、Spring Boot、Vue.js 的内容，附 5 个来源页码 |
| 总结 | ✅ 通过 | 6 节结构化总结，识别出 mAP@0.5=68%、14ms 推理等关键指标 |
| Quiz 生成 | ✅ 通过（1/6 道） | 修复 fallback 答案提取后从 0 题提升到 1 题，1.5B 模型限制 |
| 答题提交 | ✅ 通过 | 正确评分，错误答案记录正确 |
| 掌握度追踪 | ✅ 通过 | 4 个知识点已追踪，平均 46.8% |
| 今日复习 | ✅ 通过 | 新题安排 5 天后复习（掌握度 40-70% 区间） |
| 数据持久化 | ✅ 通过 | 后端重启后文档、总结仍可查询 |

### 本次修复

- **`quiz_generator.py`**：新增 `_first_block()` 截断多余输出，新增 `_extract_answer_fallback()` 从"正确答案为A"等表达中提取答案字母，`max_tokens` 从 600 → 800。
- **`quiz_generator.py`**：新增 `[选项]` 等中括号占位符检测，防止无效题目进入结果。

### 当前运行状态

| 服务 | 端口 | 状态 |
| --- | --- | --- |
| Ollama | 11434 | ✅ running（deepseek-r1:1.5b + nomic-embed-text） |
| 后端 FastAPI | 8000 | ✅ running |
| 前端 Next.js | 3000 | ✅ running |

浏览器访问：`http://127.0.0.1:3000`

## 2026-06-11（后续优化：Quiz 历史、Reflection、学习规划、Docker）

### Item 1 — Quiz 历史记录

- `schemas/quiz.py`：新增 `QuizSummary`、`QuizListResponse`。
- `document_store.py`：新增 `list_quizzes(document_id)` 按创建时间倒序返回摘要列表。
- `routes_quiz.py`：新增 `GET /documents/{id}/quiz` 端点返回历史列表。
- `lib/types.ts`：新增 `QuizSummary`、`QuizListResponse`、`StudyPlan`、`StudyPlanItem` 类型；修复 `api.ts` 中 `StudyPlan` 导入缺失导致的构建错误。
- 前端 `quiz/page.tsx`：完整重写，挂载时加载历史列表，未激活 quiz 时显示可点击历史面板，`handleLoadPastQuiz` 按 ID 加载历史。

### Item 2 — LangGraph Reflection 节点

- `agents/state.py`：新增 `reflection: str`、`retry_count: int`、`history: list[dict]` 字段。
- `agents/graph.py`：新增 `_reflect` 节点（检测短回答或回退信号词）和 `_route_after_reflect` 条件路由；chat graph 流程改为 `retrieve → answer → reflect → [retry→retrieve | END]`，最多重试 1 次；重试时 `retrieve` 扩大召回数量（limit=8）。
- 新增测试 3 项：正常流程有 `reflection="answer_ok"`、短回答触发 1 次重试、无限重试防护。

### Item 3 — 学习规划 Agent

- `schemas/plan.py`：新增 `StudyPlanItem`、`StudyPlan` Pydantic 模型。
- `services/planning_service.py`：读取掌握度 + 文档列表，构建 LLM prompt 生成优先级排序计划，JSON 解析失败时降级为启发式顺序。
- `api/routes_profile.py`：新增 `POST /profile/study-plan` 端点。
- 前端 `profile/page.tsx`：新增 `StudyPlanPanel` 组件，带序号圆形优先级标记；"生成学习计划"/ "重新生成"按钮；计划项展示文档标题 + AI 建议理由。
- 新增测试 5 项：200 状态、schema、无文档为空、LLM mock、JSON 降级。

### Item 4 — Docker Compose 完善

- `apps/api/Dockerfile`：新建，`python:3.12-slim` 基础镜像，安装 PyMuPDF 系统依赖。
- `infra/docker-compose.yml`：postgres/qdrant/redis 三服务均加 healthcheck；新增 `api` 服务，`depends_on` 带 `condition: service_healthy`，volumes 挂载 uploads 目录。
- `.env.example`：补充 Docker Compose 使用说明（含 Ollama host.docker.internal 访问方式）。

### 验证状态

```
88 passed, 1 warning in 2.73s
```

Next.js 生产构建零错误，输出 11 个路由。

## 2026-06-11（Phase 5 全部完成）

### P1 — 基础操作缺失

1. **Git 初始化**：`git init` + `.gitignore`（首次提交 87 个文件）
2. **删除文档**：
   - `vector_store.py`：新增 `delete_by_document_id()`
   - `document_store.py`：新增 `delete_document()`，级联清理 DB（Quiz/Chunk/Document）+ Qdrant 向量 + 磁盘文件
   - `routes_documents.py`：新增 `DELETE /documents/{id}` 端点
   - 前端：列表页每条文档加删除按钮（✕），详情页加红色"删除文档"按钮
3. **总结流式输出**：
   - `summary_generator.py`：新增 `stream_summary_text()`
   - `routes_summary.py`：新增 `POST /summary/stream` SSE 端点（有缓存时快速流出，无缓存时调用 LLM 流式生成并存库）
   - 前端 `summary/page.tsx`：改用流式 SSE，逐字显示

### P2 — 体验提升

4. **多轮对话记忆**：
   - `schemas/chat.py`：`ChatRequest` 新增 `history: list[dict]`
   - `llm.py`：`stream_answer_question()` 接受 `history` 参数，拼入消息列表
   - `routes_chat.py`：传 `request.history` 给 LLM
   - 前端 `chat/page.tsx`：重构为多轮对话气泡布局，来源折叠展示，支持"清空对话"
5. **总结缓存**：
   - `routes_summary.py`：常规 POST 端点检查 `doc.summary` 有缓存直接返回
   - 前端 `summary/page.tsx`：挂载时读取文档缓存摘要并展示，按钮变为"重新生成"
6. **文档列表搜索/过滤**：
   - 前端 `documents/page.tsx`：搜索框按文件名过滤，下拉按状态过滤

### P3 — AI 质量提升

7. **跨文档检索**：
   - `vector_store.py`：新增 `search_global()`（去掉 document_id 过滤）
   - `retrieval.py`：新增 `retrieve_context_global()`
   - 新建 `routes_search.py`：`POST /search/stream` SSE 端点
   - `main.py`：注册新路由
   - 新建前端页 `/search`：全局搜索，支持多轮对话，来源注明文档 ID
   - `app-shell.tsx`：导航栏新增"全局搜索"入口
8. **BM25 重排**：
   - `pyproject.toml`：新增 `rank-bm25>=0.2.2` 依赖（已安装）
   - `retrieval.py`：向量召回 3x 候选后用 BM25Okapi 二次排序（0.7 向量 + 0.3 BM25）
   - `rank_bm25` 不可用时优雅降级，不影响正常运行
9. **语义分块**：
   - `chunker.py`：完全重写，按段落边界（双换行）切块；段落过长时字符分割并加 overlap；小尾部同页合并

### 验证

- 66 个测试全部通过（包含修复一个跨页合并 bug）
- Next.js 生产构建零错误，输出 11 个页面/路由
- 首次 git 提交 41ee16f
