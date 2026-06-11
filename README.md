# AI 学习助手 · LearnOS

> 基于 LLM + RAG 的个人 AI 学习操作系统。上传 PDF，即可问答、总结、自测、追踪掌握度、生成复习计划。

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent-orange)
![Tests](https://img.shields.io/badge/Tests-88%20passed-brightgreen)

---

## 功能演示

| 功能 | 说明 |
| --- | --- |
| 📄 PDF 上传与解析 | 异步处理，前端实时轮询状态；语义分块保留段落完整性 |
| 💬 智能问答（RAG）| 向量检索 + BM25 混合重排，回答附带原文页码；支持多轮追问 |
| 📝 文档总结 | 四节结构化总结，流式逐字输出，有缓存时秒返回 |
| 🎯 Quiz 自测 | LLM 生成多题型试题（含答案/解析/知识点），支持查阅历史 Quiz |
| 📊 掌握度追踪 | 答题后自动更新知识点评分，错题权重更高 |
| 🗓 间隔复习计划 | 基于掌握度动态安排复习时间（2/5/14 天梯度） |
| 🧭 AI 学习规划 | 分析薄弱知识点，LLM 生成优先级排序的文档学习计划 |
| 🌐 跨文档全局搜索 | 跨所有文档语义检索，支持多轮对话 |

---

## 技术架构

```
┌──────────────────────────────────────────────────────┐
│               前端  Next.js 15 + TypeScript           │
│  文档管理 · 问答气泡 · 总结流式 · Quiz · 画像 · 全局搜索  │
└─────────────────────┬────────────────────────────────┘
                      │  REST / SSE
┌─────────────────────▼────────────────────────────────┐
│              后端  FastAPI + Python 3.12              │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │              LangGraph Agent 层               │    │
│  │  chat graph: retrieve→answer→reflect→[retry|END]│ │
│  │  summary graph: retrieve_all→summarize→END   │    │
│  │  quiz graph:    retrieve_all→generate→END    │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  embeddings · retrieval(BM25+vector) · llm · chunker │
│  mastery_service · planning_service                  │
└───────────┬──────────────────┬───────────────────────┘
            │                  │
   ┌────────▼───────┐  ┌───────▼────────┐
   │  SQLite / PG   │  │ Qdrant 向量库   │
   │ 文档/Quiz/掌握度 │  │ chunk embeddings│
   └────────────────┘  └────────────────┘
```

### 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Next.js 15、React 19、TypeScript |
| 后端 | Python 3.12、FastAPI、Pydantic v2、SQLAlchemy |
| AI 编排 | LangGraph（有向状态图 + Reflection 节点） |
| 向量数据库 | Qdrant（本地文件模式 / Docker 模式） |
| 关系数据库 | SQLite（开发）/ PostgreSQL（生产） |
| LLM | Ollama 本地推理（qwen2.5:7b）或 OpenAI 兼容 API |
| Embeddings | nomic-embed-text（768 维） |
| 测试 | pytest · 88 个测试 · 全离线（内存 Qdrant + mock LLM） |

---

## 核心 AI 设计

### LangGraph Reflection 节点

Chat Agent 具备自我反思能力：生成回答后检测是否为回退信号（过短 / 含"没有找到"等），若是则自动扩大检索范围重试，最多 1 次，防止无限循环。

```
retrieve(limit=5) → answer → reflect
                                ↓              ↓
                    answer_insufficient    answer_ok
                                ↓              ↓
                    retrieve(limit=8)        END
```

### 混合检索（Hybrid Search）

向量召回 3× 候选后做 BM25 二次重排：

```
final_score = 0.7 × cosine_similarity + 0.3 × bm25_score
```

BM25 库缺失时自动降级为纯向量检索，不影响服务可用性。

### 语义分块

按段落边界（`\n\n`）切块，保留语义完整性；段落过长时字符级 overlap 分割；小尾部只在同页内合并，保证页码准确。

### SSE 流式输出

问答与总结均使用 Server-Sent Events 实时推送，总结有缓存时以 30 字符批次快速回放，无缓存时 LLM 生成完毕后自动存库。

---

## 本地运行

### 前置条件

- Python 3.12+
- Node.js 18+
- [Ollama](https://ollama.com/) 并拉取模型：

```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

### 1. 配置环境变量

```bash
cp .env.example .env
# 按需修改 .env（默认使用本地 Ollama + SQLite，开箱即用）
```

### 2. 启动后端

```bash
cd apps/api
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. 启动前端

```bash
cd apps/web
npm install
npm run dev
```

访问 [http://localhost:3000](http://localhost:3000)

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
pytest                        # 88 个测试，全部离线，无需真实 Ollama/DB
pytest tests/test_graph.py    # 仅 LangGraph 图测试
```

---

## 项目结构

```
apps/
  api/                  FastAPI 后端
    app/
      agents/           LangGraph 状态图（graph.py · state.py）
      api/              路由层（chat · summary · quiz · profile · search）
      services/         核心服务（embeddings · retrieval · llm · chunker · mastery）
      models/           SQLAlchemy ORM 模型
      schemas/          Pydantic 请求/响应模型
    tests/              88 个 pytest 测试
  web/                  Next.js 前端
    app/                页面（documents · chat · quiz · summary · profile · search）
    lib/                API 客户端 · 类型定义
infra/
  docker-compose.yml    本地基础设施（含 healthcheck）
docs/                   架构 · API · Agent 工作流 · 数据模型 · 面试文档
```

---

## 已验证的真实 PDF 效果

使用一份 2874KB 的毕业设计 PDF（麦田病虫害检测系统）验证：

| 功能 | 结果 |
| --- | --- |
| 上传解析 | 0.1 秒返回，后台处理，状态实时更新 |
| RAG 问答 | 正确回答 YOLOv8、Spring Boot、Vue.js 相关问题，附 5 个页码来源 |
| 总结生成 | 识别出 mAP@0.5=68%、14ms 推理等关键指标 |
| Quiz 生成 | 6 题，答案准确，简答题有深度 |
| 掌握度追踪 | 4 个知识点，平均掌握度 46.8% |

---

## License

MIT
