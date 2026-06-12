# AI 学习助手 · LearnOS

> 基于 LLM + RAG 的个人 AI 学习操作系统。上传 PDF，即可问答、总结、自测、追踪掌握度、生成复习计划。支持多用户 JWT 认证、知识库共享、语音朗读、可拖拽知识图谱。

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent-orange)
![Tests](https://img.shields.io/badge/Tests-146%20passed-brightgreen)

---

## 功能一览

### 核心学习功能

| 功能 | 说明 |
| --- | --- |
| 📄 多格式文档上传 | PDF / TXT / MD 上传；URL 网页导入；YouTube / B 站视频字幕导入 |
| 💬 智能问答（RAG）| 向量检索 + BM25 混合重排，回答附带原文页码；支持多轮追问 |
| 📝 文档总结 | 四节结构化总结，流式逐字输出，有缓存时秒返回 |
| 🎯 Quiz 自测 | LLM 生成多题型试题（含答案/解析/知识点），支持查阅历史 Quiz |
| 📊 掌握度追踪 | 答题后自动更新知识点评分，错题权重更高 |
| 🗓 间隔复习计划 | 基于掌握度动态安排复习时间（2/5/14 天梯度） |
| 🧭 AI 学习规划 | 分析薄弱知识点，LLM 生成优先级排序的文档学习计划 |
| 🌐 跨文档全局搜索 | 跨所有文档语义检索，支持多轮对话 |

### AI 深化功能

| 功能 | 说明 |
| --- | --- |
| 🕸️ 知识图谱 | LLM 提取文档概念关系，SVG 可视化；支持拖拽节点、平移、缩放 |
| 🧠 苏格拉底对话 | AI 扮演苏格拉底式导师，主动提问引导深度思考，流式输出 |
| 📒 错题本 | 自动收集所有答错题目，支持一键加入复习队列 |
| 📈 学习周报 | 统计一周学习数据，LLM 生成个性化改进建议 |
| 🔊 语音朗读 | 问答回答与总结支持 TTS 朗读，一键播放/暂停 |
| 🔍 OCR 支持 | 扫描版 PDF 自动 OCR 提取文字（需安装 pytesseract） |

### 用户与协作

| 功能 | 说明 |
| --- | --- |
| 🔐 多用户认证 | 邮箱注册/登录，JWT 令牌，用户数据完全隔离 |
| 📚 公共知识库 | 将文档设为公开，其他用户可浏览和 Fork |
| 🍴 Fork 机制 | Fork 公开文档到个人库，复制全部 chunks 和向量 |

---

## 技术架构

```
┌──────────────────────────────────────────────────────────┐
│               前端  Next.js 15 + TypeScript               │
│  文档管理 · 问答 · 总结 · Quiz · 知识图谱 · 苏格拉底对话   │
│  全局搜索 · 错题本 · 学习规划 · 公共库 · 语音朗读          │
└──────────────────────┬───────────────────────────────────┘
                       │  REST / SSE  (JWT Bearer Token)
┌──────────────────────▼───────────────────────────────────┐
│               后端  FastAPI + Python 3.12                 │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │              LangGraph Agent 层                    │  │
│  │  chat:    decide(tool calling)→retrieve→answer     │  │
│  │           →reflect→[retry|END]                     │  │
│  │  summary: retrieve_all→summarize→END               │  │
│  │  quiz:    retrieve_all→generate→END                │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  embeddings · retrieval(BM25+vector) · llm · chunker     │
│  mastery_service · knowledge_graph · tts_service         │
│  auth_service (JWT) · document_store (user-scoped)       │
└──────────────┬─────────────────────┬─────────────────────┘
               │                     │
      ┌────────▼────────┐   ┌────────▼────────┐
      │  SQLite / PG    │   │  Qdrant 向量库   │
      │ 文档/Quiz/用户   │   │ chunk embeddings │
      └─────────────────┘   └─────────────────┘
```

### 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Next.js 15、React 19、TypeScript |
| 后端 | Python 3.12、FastAPI、Pydantic v2、SQLAlchemy |
| AI 编排 | LangGraph（有向状态图 + Function Calling 路由 + Reflection 节点） |
| 向量数据库 | Qdrant（本地文件模式 / Docker 模式 / Qdrant Cloud） |
| 关系数据库 | SQLite（开发）/ PostgreSQL（生产 / Neon） |
| LLM | DeepSeek API / OpenAI 兼容 API / Ollama 本地推理 |
| Embeddings | Jina AI / nomic-embed-text（768 维） |
| 认证 | JWT（python-jose + passlib/bcrypt） |
| TTS | OpenAI TTS API（mp3 流式返回） |
| 测试 | pytest · **146 个测试** · 全离线（内存 Qdrant + mock LLM） |

---

## 核心 AI 设计

### 1. LLM 工具调用（Function Calling）路由

Chat Agent 入口节点 `decide` 用工具调用让 LLM 自主决定是否检索，并同步精炼查询词：

```
decide(tool calling)
    ↓ needs_retrieval=True              ↓ needs_retrieval=False
retrieve(refined_query, limit=5)    direct_answer
    ↓                                   ↓
answer                                 END
    ↓
reflect（检测回退信号词 / 字数过短）
    ↓ answer_insufficient              ↓ answer_ok
retrieve(limit=8, 扩大召回)            END
    ↓
answer → reflect → END（最多重试 1 次）
```

### 2. 混合检索（Hybrid Search）

向量召回 3× 候选后做 BM25 二次重排：

```
final_score = 0.7 × cosine_similarity + 0.3 × bm25_score
```

BM25 库缺失时自动降级为纯向量检索，服务不中断。

### 3. 用户隔离 + 全局搜索

所有查询携带 JWT 后解析 `user_id`，DB 查询和 Qdrant 检索均加 `user_id` 过滤。全局搜索先查用户的文档 ID 列表，再用 `MatchAny` 过滤向量检索范围。

---

## 本地运行

### 前置条件

- Python 3.12+、Node.js 18+
- DeepSeek API Key（或本地 Ollama + qwen2.5:7b + nomic-embed-text）

### 1. 配置环境变量

```bash
cp .env.example .env
# 填入 OPENAI_API_KEY（DeepSeek）、OPENAI_BASE_URL、JINA_API_KEY 等
```

### 2. 启动后端

```bash
cd apps/api
python -m venv .venv
# Windows:  .\.venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. 启动前端

```bash
cd apps/web
npm install
npm run dev
```

访问 [http://localhost:3000](http://localhost:3000)，注册账号或使用演示密码登录。

### 4. 可选：Docker Compose 启动全套基础设施

```bash
cd infra
docker compose up -d
# 包含 postgres · qdrant · redis · api，均带 healthcheck
```

---

## 运行测试

```bash
cd apps/api
pytest                          # 146 个测试，全部离线，无需真实 API
pytest tests/test_auth.py       # 多用户认证与隔离
pytest tests/test_library.py    # 公共库 / Fork
pytest tests/test_graph.py      # LangGraph 图测试
pytest tests/test_tool_calling.py  # Function Calling 路由
```

---

## 项目结构

```
apps/
  api/                    FastAPI 后端
    app/
      agents/             LangGraph 状态图（graph.py · state.py）
      api/                路由层（auth · chat · summary · quiz · profile
                                  search · knowledge_graph · tts）
      services/           核心服务（embeddings · retrieval · llm · chunker
                                   mastery · knowledge_graph · tts_service
                                   auth_service · error_notebook）
      models/             SQLAlchemy ORM 模型
      schemas/            Pydantic 请求/响应模型
    tests/                146 个 pytest 测试
  web/                    Next.js 前端
    app/                  页面路由（documents · chat · quiz · summary
                                   knowledge-graph · socratic · error-notebook
                                   library · profile · search · login）
    components/           共享组件（app-shell · tts-button）
    lib/                  API 客户端 · 类型定义
  extension/              Chrome 扩展（Manifest V3）
infra/
  docker-compose.yml      本地基础设施（含 healthcheck）
docs/                     架构 · API · Agent 工作流 · 数据模型 · 面试文档
```

---

## 云端部署

| 服务 | 平台 |
| --- | --- |
| 前端 | Vercel |
| 后端 | Google Cloud Run |
| 数据库 | Neon PostgreSQL |
| 向量库 | Qdrant Cloud |
| LLM | DeepSeek API |
| Embeddings | Jina AI |

---

## License

MIT
