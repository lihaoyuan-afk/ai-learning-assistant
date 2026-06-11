# 架构说明

## 总体架构

```text
用户
↓
Next.js Web UI
↓
FastAPI API
↓
Service Layer
↓
LangGraph Agent Workflow
↓
LLM / Qdrant / Postgres / File Storage
```

## Phase 1 设计原则

- 前端只负责上传、展示、提问和查看结果。
- 后端统一负责文档解析、检索、模型调用和 Agent 编排。
- RAG 链路先做清楚，再扩展多 Agent。
- 数据库模型先保留清晰边界，真实迁移可以后续补。
- 上传文件先保存在本地 `uploads/`，后续再切换到 S3 或 Supabase Storage。

## 核心模块

| 模块 | 职责 |
| --- | --- |
| Document Parser | 解析 PDF，提取文本和页码 |
| Chunker | 将长文档切成适合检索的片段 |
| Embeddings | 将文本转成向量 |
| Vector Store | 写入和查询 Qdrant |
| Retrieval | 根据问题取回相关片段 |
| LLM Service | 封装 OpenAI 或 Claude 调用 |
| Agent Graph | 用 LangGraph 组织问答、总结、Quiz |

## 后续演进

Phase 2 加入学习记忆、错题和复习计划。Phase 3 再引入 Planner、Reflection 和 Knowledge Graph。

