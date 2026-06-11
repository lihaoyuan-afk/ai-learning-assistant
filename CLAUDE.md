# Claude Code 项目接手说明

## 1. 接手任务

你正在接手一个 AI 学习助手 Agent 项目。

项目的核心目标不是制作普通聊天机器人，而是通过实际开发学习并构建一个 AI Learning Operating System，使用户上传学习资料后可以完成资料理解、问答、总结、Quiz、复习规划和长期学习状态记录。

当前优先任务是继续完成 Phase 1 MVP：

```text
上传 PDF
↓
解析 PDF
↓
文档切片
↓
向量化和检索
↓
基于资料问答
↓
生成总结
↓
生成 Quiz
```

## 2. 工作目录

项目真实工作目录是：

```text
E:\codex
```

不要在以下旧目录继续创建项目文件：

```text
C:\Users\86157\Documents\agentlearn
```

当前 Codex 会话的 workspace root 可能仍显示旧的 C 盘路径，但项目内容已经迁移到 `E:\codex`。

## 3. 开始工作前必须阅读

按以下顺序读取：

1. `task_plan.md`：当前阶段、原则和待办
2. `progress.md`：已完成工作和验证记录
3. `findings.md`：已确认方向、风险和技术取舍
4. `PROJECT_SKELETON.md`：完整项目骨架
5. `docs/phase1_mvp.md`：Phase 1 边界
6. `docs/architecture.md`
7. `docs/api.md`
8. `docs/agent_workflows.md`
9. `docs/data_model.md`

原始学习计划备份位于：

```text
docs/reference/original_learning_plan.md
```

请保留这些参考文档，不要删除或覆盖原始学习计划。

## 4. 当前项目状态

### 已完成

- 已创建 Next.js 前端骨架。
- 已创建 FastAPI 后端骨架。
- 已创建 Agent、services、schemas、models、workers 等模块边界。
- 已创建 Postgres、Qdrant、Redis 的 Docker Compose 配置。
- 已安装前端依赖并生成 `package-lock.json`。
- 已创建后端虚拟环境 `apps/api/.venv` 并安装依赖。
- Next.js 生产构建曾通过。
- FastAPI 健康检查测试曾通过。
- 原始学习计划和相关参考文档已保留。

### 当前没有运行

截至 2026-06-04，前端和后端服务没有在监听 `3000` 或 `8000` 端口。开始开发时需要重新启动。

### 尚未完成

- 真实 Qdrant 向量写入和搜索
- 真实 embeddings
- 真实 OpenAI / Claude 模型调用
- Postgres 数据持久化
- LangGraph 工作流编排
- 完整的上传错误处理和解析状态管理
- 基于真实资料的总结和 Quiz
- 学习记忆、复习计划和用户画像

## 5. 哪些代码是真实实现，哪些是占位

### 已有基础实现

| 文件 | 当前能力 |
| --- | --- |
| `apps/api/app/workers/ingest_document.py` | 保存上传文件，调用解析和切片流程 |
| `apps/api/app/services/document_parser.py` | 使用 PyMuPDF 提取 PDF 每页文本 |
| `apps/api/app/services/chunker.py` | 按字符长度和 overlap 切片 |
| `apps/api/app/api/routes_documents.py` | 上传、列表、详情和重新解析接口 |
| `apps/api/app/api/routes_chat.py` | 问答 API 外壳 |
| `apps/api/app/api/routes_summary.py` | 总结 API 外壳 |
| `apps/api/app/api/routes_quiz.py` | Quiz API 外壳 |
| `apps/web/app/` | 工作台、资料、上传、问答、总结、Quiz、复习、画像页面 |

### 仍是占位实现

| 文件 | 现状 |
| --- | --- |
| `apps/api/app/services/document_store.py` | 仅使用内存字典，服务重启后数据丢失 |
| `apps/api/app/services/embeddings.py` | 使用哈希生成假向量 |
| `apps/api/app/services/vector_store.py` | 只记录写入数量，没有连接 Qdrant |
| `apps/api/app/services/retrieval.py` | 使用简单关键词匹配，不是向量检索 |
| `apps/api/app/services/llm.py` | 返回占位回答，没有调用模型 |
| `apps/api/app/services/summary_generator.py` | 返回占位总结 |
| `apps/api/app/services/quiz_generator.py` | 返回重复占位题目 |
| `apps/api/app/agents/graph.py` | LangGraph 尚未接线，当前直接返回 state |
| `apps/api/app/db/session.py` | 已定义连接，但业务代码没有使用数据库 |

不要把当前占位逻辑当作已完成能力。

## 6. 技术栈

### 前端

- Next.js 15.5.19
- React 19
- TypeScript

### 后端

- Python 3.12.7
- FastAPI
- Pydantic
- SQLAlchemy
- PyMuPDF
- Qdrant Client
- LangGraph
- OpenAI SDK

### 基础设施

- Postgres
- Qdrant
- Redis
- Docker Compose

Phase 1 暂时不做认证、计费、多人协作、OCR、语音、白板和复杂知识图谱。

## 7. 本地运行与验证

### 后端测试

```powershell
cd E:\codex\apps\api
.\.venv\Scripts\python.exe -m pytest
```

已知结果：

```text
1 passed
```

测试会出现一个 Starlette TestClient 弃用提醒，目前不影响运行。

### 启动后端

```powershell
cd E:\codex\apps\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

验证：

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

### 前端构建

本机 PowerShell 会优先命中一个无效的 `C:\Windows\System32\npm`。请显式使用真实 npm：

```powershell
cd E:\codex
E:\Nodejs\npm.cmd install
E:\Nodejs\npm.cmd run build:web
```

### 启动前端

直接在 Web 应用目录启动，避免根 workspace 参数传递错误：

```powershell
cd E:\codex\apps\web
E:\Nodejs\npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

验证：

```text
http://127.0.0.1:3000
```

### 启动基础设施

```powershell
cd E:\codex\infra
docker compose up -d
```

Docker Compose 尚未实际验证。首次启动后请检查 Postgres、Qdrant 和 Redis 是否健康。

## 8. 已知环境和依赖问题

### npm audit

Next 15.5.19 的传递依赖包含 `postcss@8.4.31`，当前 `npm audit` 报告 2 个中等风险项。

不要直接运行：

```powershell
npm audit fix --force
```

该命令当前会建议将 Next 破坏性降级到旧版本。请在升级 Next 或依赖生态提供兼容修复后再处理。

### TLS 环境警告

npm / Next 启动时可能提示：

```text
NODE_TLS_REJECT_UNAUTHORIZED=0
```

这是当前机器环境设置导致的警告，不是项目代码设置。不要在项目中继续固化这个配置。

### Git

项目目前不是 Git 仓库。不要假设存在提交历史或可回滚分支。初始化 Git 前先向用户说明。

## 9. 推荐的下一步执行顺序

### 第一项：完成真实文档上传与解析闭环

目标：

- 只允许 PDF
- 校验空文件、损坏文件和文件大小
- 解析失败时把文档状态更新为 `failed`
- 返回明确错误信息
- 为 parser、chunker、上传接口补测试

完成后更新：

- `task_plan.md`
- `progress.md`
- `findings.md`
- `docs/api.md`

### 第二项：接入 Qdrant 和真实 embeddings

目标：

- 使用 `infra/docker-compose.yml` 启动 Qdrant
- 为每个 chunk 生成真实 embedding
- 写入 Qdrant，并带上 `document_id`、页码、chunk_index 等 metadata
- 按 `document_id` 隔离检索
- 为写入和检索补测试

### 第三项：接入真实教材问答

目标：

- 使用检索结果组成上下文
- 调用真实 LLM
- 回答必须附带页码或来源片段
- 不允许在缺少资料依据时编造

### 第四项：实现真实总结和 Quiz

目标：

- 总结基于完整文档或分层总结
- Quiz 包含难度、答案、解释和知识点
- 避免所有题目重复

### 第五项：稳定后再接入 LangGraph

先保证独立 services 可测试、可运行，再把问答、总结和 Quiz 编排进 LangGraph。不要一开始就扩展复杂多 Agent。

## 10. 工作原则

- 第一版只支持 PDF。
- 先跑通闭环，再增加功能。
- 保持 services 与 Agent 编排分离。
- 每个真实能力都补最小测试。
- 不要提前实现 Phase 2 和 Phase 3。
- 不要删除用户已有文档或无关文件。
- 重大技术选择写入 `findings.md`。
- 每完成一个阶段更新 `task_plan.md` 和 `progress.md`。
- API、数据模型或工作流变化时同步更新 `docs/`。

## 11. 完成 Phase 1 的判断标准

Phase 1 完成时，用户应该可以：

1. 上传一个真实 PDF。
2. 查看 PDF 解析状态。
3. 针对 PDF 提问并得到带来源的回答。
4. 生成真实结构化总结。
5. 生成不重复、带答案和解释的 Quiz。
6. 重启服务后仍能找到文档和相关数据。

在以上闭环完成前，不要将 Phase 1 标记为 complete。

