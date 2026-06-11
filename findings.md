# Agent 学习助手项目发现记录

## 已确认方向

- 项目目标不是普通聊天机器人，而是 AI Learning Operating System。
- 学习目标不是单纯调用 LLM API，而是掌握 Agent 系统设计。
- 核心能力包括：状态、工作流、记忆、规划、工具调用、反思、用户建模。
- 第一阶段应该控制范围，只做 PDF 上传、RAG 问答、总结、Quiz。
- LangGraph 更适合作为主线学习框架，因为它的状态机和工作流更透明。

## 风险与取舍

- 如果一开始同时支持 PDF、PPT、Markdown、字幕、笔记，会导致解析链路过重。
- 如果一开始做完整多 Agent，很容易变成框架堆叠，反而不利于理解核心原理。
- 如果过早引入复杂权限、计费、多人协作，会偏离 Agent 学习目标。

## 项目骨架实现取舍

- 后端第一版使用内存态 document store 和占位 LLM/RAG 逻辑，目的是先固定模块边界。
- PDF 解析服务优先使用 PyMuPDF；未安装依赖时会返回占位文本，方便接口先跑通。
- Qdrant、Postgres、LangGraph 已预留文件和依赖，但真实业务接入放到后续任务。
- 前端第一版提供工作台、资料、上传、详情、问答、总结、Quiz、复习、画像页面入口。
- Next 15.5.19 当前传递依赖 `postcss@8.4.31`，npm audit 报 2 个中等风险；强制修复会降级 Next，暂时保留并记录。

## Phase 1 实现确认（2026-06-04）

### embeddings 服务
- 使用 OpenAI `text-embedding-3-small`（1536 维），成本极低（约 $0.02/1M tokens）。
- 客户端懒初始化，`OPENAI_API_KEY` 未配置时 ingestion 会失败并将文档置为 `failed` 状态。
- 测试中用 in-memory mock 替代，不依赖真实 API。

### Qdrant 客户端版本适配
- 项目安装的 qdrant-client 已移除 `search()` 方法，改为 `query_points()`。
- 统一使用 `query_points()` + `Filter/FieldCondition/MatchValue` 模型进行过滤检索。
- 测试使用 `QdrantClient(":memory:")` 运行 in-memory 实例，无需启动 Docker。

### mock 注入模式
- 所有外部依赖（embeddings、LLM、Qdrant）均通过 `autouse` pytest fixture 在 conftest.py 注入 mock。
- `vector_store.py` 和 `retrieval.py` 改用模块引用（`from app.services import embeddings as _emb`）而非直接函数引用，确保 `monkeypatch` 能正确拦截。

### LLM 调用设计
- `llm.py` 暴露 `call_chat` 和 `call_chat_json` 两个公共函数，所有 LLM 调用收口在此。
- `summary_generator.py` 和 `quiz_generator.py` 通过模块引用调用，方便 mock。
- Quiz 生成使用 `response_format={"type": "json_object"}` 约束输出，并对 JSON 解析失败做降级处理（返回空题目列表）。

### 小模型 Quiz 生成适配（2026-06-10 端到端验证）

- `deepseek-r1:1.5b` 是推理模型，输出会包含 `<think>…</think>` 块，必须在 `llm.py` 层剥离。
- 小模型无法可靠生成嵌套 JSON（如 `{"questions": [...]}`）：会把格式示例里的 `{` 当作 JSON key，产生 `{"{"："multiple_choice",...}` 这种无效结构。
- 模板中使用 `（在这里写...）` 占位符也无效：1.5B 模型会原样复制占位符而不替换内容。
- **有效方案**：Few-shot 驱动——在 user 消息里给一个完整的具体例子，要求模型按相同格式出新题，配合正则解析代替 JSON 解析。每次只出一道题，多次调用收集结果。
- **Quiz 质量与模型大小强相关**：1.5B 模型典型成功率约 1-3/4 题；升级到 qwen2.5:7b 或 deepseek-r1:7b 后成功率和题目质量会显著提升。
- **Chat 和 Summary** 对 1.5B 模型效果更好（无结构约束），回答和总结质量可用。
- `mastery_service.py` 中所有 datetime 应使用 naive UTC（`datetime.now(timezone.utc).replace(tzinfo=None)`），因为 SQLite 不保留时区信息，混用 naive/aware datetime 会导致比较时 TypeError。

### 模型升级：qwen2.5:7b（2026-06-10）

- `deepseek-r1:1.5b`（1.5B 参数）Quiz 成功率约 0-1/6，会跳过 `答案：` 行，生成多余内容。
- `qwen2.5:7b`（7B 参数）Quiz 成功率 6/6，严格遵循 few-shot 格式，简答题有实质内容，32 秒完成 6 题。
- `qwen2.5:7b` 不产生 `<think>` 块，`_strip_think` 正则无副作用（空匹配）。
- Chat / Summary 质量也有明显提升，建议作为本项目默认模型。
- `.env` 只需改一行 `OPENAI_CHAT_MODEL` 即可切换，无需代码变更。

### 异步文档处理（2026-06-10）

- 上传端点改为 `BackgroundTasks`：保存文件后立即返回 `status: uploaded`，背景中执行解析 + 向量化。
- 实测 0.1 秒返回（之前 30-60 秒）；PDF 在背景中 ~2 秒变为 `ready`。
- 后端启动时自动将卡住的 `uploaded/processing` 文档重置为 `failed`，避免用户永远等待。
- 前端上传页和文档列表页均加入 2.5 秒轮询，文档状态实时更新至 `ready` 或 `failed`。

### 中文字符串注意事项
- Python 源文件中避免在字符串字面量内使用中文弯引号（U+201C/U+201D），它们会被 Python 解析器当作普通字符但与周围的 ASCII 引号产生歧义导致 SyntaxError。
- 改用直角引号或括号替代：`（第X页）` 而非 `"（第X页）"`。
