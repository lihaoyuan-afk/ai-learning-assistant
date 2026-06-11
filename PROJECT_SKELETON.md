# AI 学习助手 Agent 项目骨架

## 1. 项目定位

本项目不是普通 AI ChatBot，而是面向学习过程的 AI Learning Operating System。

用户上传学习资料后，系统帮助用户完成：

- 理解资料
- 建立知识库
- 针对资料问答
- 生成结构化笔记
- 生成 Quiz
- 记录薄弱点
- 安排复习
- 长期追踪学习状态

## 2. 产品主流程

```text
上传学习资料
↓
文档解析与结构化
↓
切片、向量化、入库
↓
基于资料问答
↓
生成总结和 Quiz
↓
记录答题结果
↓
更新掌握度和复习计划
```

## 3. 推荐技术栈

| 层级 | Phase 1 推荐 | 后续扩展 |
| --- | --- | --- |
| 前端 | Next.js | React Flow、白板、语音交互 |
| 后端 | FastAPI | 后台任务、权限、计费 |
| Agent | LangGraph | 多 Agent、Reflection、Memory |
| RAG | LlamaIndex 或轻量自研封装 | 混合检索、重排序 |
| LLM | OpenAI 或 Claude | 多模型路由 |
| 数据库 | Postgres | 学习画像、复习系统 |
| 向量库 | Qdrant | 多集合、多用户隔离 |
| 队列 | Phase 1 可暂缓 | Redis + worker |
| 文件存储 | 本地 uploads 起步 | S3 / Supabase Storage |
| 认证 | Phase 1 可暂缓 | Clerk |

## 4. 工程目录建议

```text
agentlearn/
  apps/
    web/                         # Next.js 前端
      app/
      components/
      lib/
      styles/
    api/                         # FastAPI 后端
      app/
        main.py
        api/
        core/
        db/
        models/
        schemas/
        services/
        agents/
        workers/
        tests/
  packages/
    shared/                      # 前后端共享类型或约定，后期再加
  docs/
    architecture.md
    api.md
    agent_workflows.md
    data_model.md
  infra/
    docker-compose.yml
    qdrant/
    postgres/
  uploads/                       # 本地开发上传目录
  task_plan.md
  findings.md
  progress.md
  PROJECT_SKELETON.md
```

## 5. 后端模块骨架

```text
apps/api/app/
  main.py
  api/
    routes_documents.py          # 上传、查看、删除文档
    routes_chat.py               # 基于资料问答
    routes_quiz.py               # Quiz 生成与答题记录
    routes_summary.py            # 总结生成
  core/
    config.py                    # 环境变量与配置
    logging.py
    errors.py
  db/
    session.py
    migrations/
  models/
    user.py
    document.py
    chunk.py
    quiz.py
    learning_memory.py
  schemas/
    document.py
    chat.py
    quiz.py
    summary.py
  services/
    document_parser.py           # PDF 解析
    chunker.py                   # 文档切片
    embeddings.py                # 向量生成
    vector_store.py              # Qdrant 封装
    retrieval.py                 # 检索
    llm.py                       # 模型调用
    quiz_generator.py
    summary_generator.py
  agents/
    state.py                     # LangGraph 状态定义
    graph.py                     # Agent 工作流入口
    document_agent.py
    tutor_agent.py
    quiz_agent.py
    review_agent.py
    memory_agent.py
  workers/
    ingest_document.py           # 后续改成异步任务
  tests/
```

## 6. 前端页面骨架

```text
apps/web/app/
  page.tsx                       # 默认跳转或项目首页
  documents/
    page.tsx                     # 文档列表
    upload/page.tsx              # 上传资料
    [id]/page.tsx                # 文档详情
    [id]/chat/page.tsx           # 针对文档问答
    [id]/summary/page.tsx        # 总结
    [id]/quiz/page.tsx           # Quiz
  review/
    page.tsx                     # 今日复习，Phase 2
  profile/
    page.tsx                     # 学习画像，Phase 2
```

## 7. Agent 划分

### Phase 1 必做

| Agent | 作用 |
| --- | --- |
| Document Understanding Agent | 解析 PDF，提取文本、章节、摘要信息 |
| Tutor Agent | 基于资料回答问题，解释概念 |
| Quiz Agent | 根据资料生成不同难度题目 |

### Phase 2 再做

| Agent | 作用 |
| --- | --- |
| Memory Agent | 记录用户学过什么、哪里薄弱、错题模式 |
| Review Planner Agent | 根据掌握度和错误率安排复习 |

### Phase 3 再做

| Agent | 作用 |
| --- | --- |
| Planner Agent | 判断用户意图，选择调用 Tutor、Quiz、Review、Research |
| Reflection Agent | 检查回答是否太难、是否需要换解释方式 |
| Knowledge Graph Agent | 建立知识点之间的关系 |

## 8. 数据模型骨架

### users

- id
- email
- display_name
- created_at

### documents

- id
- user_id
- title
- file_type
- file_path
- status
- summary
- created_at

### chunks

- id
- document_id
- chunk_index
- content
- page_number
- section_title
- embedding_id

### chat_sessions

- id
- user_id
- document_id
- title
- created_at

### chat_messages

- id
- session_id
- role
- content
- sources
- created_at

### quizzes

- id
- user_id
- document_id
- title
- difficulty
- created_at

### quiz_questions

- id
- quiz_id
- type
- question
- options
- answer
- explanation
- knowledge_point

### quiz_attempts

- id
- user_id
- quiz_id
- score
- answers
- created_at

### learning_memory

- id
- user_id
- knowledge_point
- mastery_score
- mistake_count
- last_reviewed_at
- next_review_at

## 9. Phase 1 MVP 边界

只做：

- PDF 上传
- PDF 文本解析
- 文档切片
- 向量化入 Qdrant
- 针对单个文档提问
- 生成文档总结
- 生成 Quiz

暂缓：

- 多格式上传
- OCR
- 复杂知识图谱
- 多用户权限
- 语音
- 白板
- 自动复习
- 完整多 Agent 协作

## 10. Phase 1 API 骨架

```text
POST   /documents/upload
GET    /documents
GET    /documents/{document_id}
POST   /documents/{document_id}/ingest
POST   /documents/{document_id}/chat
POST   /documents/{document_id}/summary
POST   /documents/{document_id}/quiz
GET    /documents/{document_id}/quiz/{quiz_id}
```

## 11. Phase 1 LangGraph 工作流

```text
用户问题
↓
加载文档上下文
↓
检索相关 chunks
↓
判断任务类型
↓
调用对应节点：
  - answer_question
  - generate_summary
  - generate_quiz
↓
返回结果和引用来源
```

## 12. 学习路线建议

### 第 1 周

- 搭建 FastAPI 和 Next.js
- 完成 PDF 上传
- 完成 PDF 解析
- 完成 chunk 切片
- 接入 embeddings 和 Qdrant

### 第 2 周

- 完成基于资料问答
- 完成总结生成
- 完成 Quiz 生成
- 做简单 UI 闭环
- 加最小测试和 README

### 第 3-4 周

- 加学习记录
- 加错题本
- 加掌握度
- 加复习计划

### 第 2 个月

- 引入 LangGraph Planner
- 多 Agent 编排
- Reflection
- Knowledge Graph
- 个性化学习路径

