# Agent 学习助手项目任务计划

## 当前目标

后续优化全部完成（Quiz 历史 + Reflection + 学习规划 + Docker），项目进入稳定维护阶段。下一阶段视需求推进 Phase 4 长期能力扩展。

## 阶段状态

| 阶段 | 状态 | 目标 |
| --- | --- | --- |
| 0. 项目骨架整理 | complete | 优化并罗列清晰项目骨架 |
| 1. Phase 1 MVP | complete | PDF 上传、解析、问答、总结、Quiz |
| 2. 学习状态系统 | complete | 掌握度追踪、复习计划（基础版） |
| 3. Agent 工作流 | complete | LangGraph 编排 chat/summary/quiz |
| 5. 体验完善与能力提升 | complete | P1/P2/P3 全部完成 |
| 6. 后续优化 | complete | Quiz 历史、Reflection、学习规划、Docker |
| 4. 长期能力扩展 | pending | OCR、语音导师、AI 白板、多学科老师 |

## 核心原则

- 先跑通学习闭环，再扩展多 Agent。
- 第一版只支持 PDF，避免一开始被多格式解析拖慢。
- 第一版先做单用户或简单用户系统，认证可以后置。
- Agent 学习重点放在状态、工作流、记忆、工具调用、反思和用户建模。
- 技术选择优先透明、可控、可调试：LangGraph 优先于更黑盒的多 Agent 框架。

## 待办

- [x] 整理优化后的项目骨架
- [x] 确认 Phase 1 技术栈按 Next.js + FastAPI + LangGraph + Qdrant 推进
- [x] 创建代码项目骨架
- [x] 保留原始学习计划和项目参考文档
- [x] 实现文档上传与解析（PDF 校验、损坏检测、failed 状态）
- [x] 实现向量化与检索（Qdrant query_points、in-memory 测试）
- [x] 实现教材问答（LLM chat，附带页码来源）
- [x] 实现总结生成（结构化 LLM 总结）
- [x] 实现 Quiz 生成（JSON 输出 + 解析，多题型，不重复）
- [x] 补充测试（66 个测试，覆盖所有核心模块）
- [x] 修复 .env 模型配置（qwen2.5:7b → deepseek-r1:1.5b）
- [x] 修复 LLM 层（think 标签剥离、JSON 提取、Ollama 上下文扩展、超时）
- [x] 修复 models/document.py file_path nullable
- [x] LangGraph 节点错误处理
- [x] 路由层错误处理 + 文档状态保护
- [x] 前端导航高亮当前路由
- [x] 前端状态颜色区分（ready/failed/processing）
- [x] 前端文档详情页按状态启用/禁用功能入口
- [x] 前端首页更新（快速开始说明）
- [x] 真实端到端验证：启动 Ollama、启动后端、上传真实 PDF
- [x] 升级模型：qwen2.5:7b 替换 deepseek-r1:1.5b
- [x] 异步文档处理：上传即返回，后台解析，前端轮询状态
- [x] 流式输出（SSE）：问答页逐字流式，带闪烁光标
- [x] Markdown 渲染：问答 + 总结页用 react-markdown 渲染

## Phase 5 待办（体验完善与能力提升）

按优先级排列：

### P1 — 基础操作缺失

- [x] **Git 初始化**：`git init` + `.gitignore`，保护所有已有工作
- [x] **删除文档**：列表页 / 详情页加删除按钮，同步清理 DB + Qdrant + 文件
- [x] **总结流式输出**：复用 SSE 基础设施，summary 生成过程逐字展示（当前 30s+ 等待）

### P2 — 体验提升

- [x] **多轮对话记忆**：ChatRequest 加 history 字段，每轮追加消息，模型能理解追问上下文
- [x] **总结缓存**：首次生成后存库，再次点击直接读缓存，避免重复调用 LLM
- [x] **文档列表搜索 / 过滤**：按文件名搜索，按状态过滤，文档多时能快速定位

### P3 — AI 质量提升

- [x] **跨文档检索**：vector_store.search_global() + retrieve_context_global() + /search/stream 端点 + 前端全局搜索页
- [x] **检索重排（Rerank）**：向量召回后加 BM25 二次排序（0.7 向量 + 0.3 BM25），提升 RAG 准确率
- [x] **语义分块替换固定长度分块**：按段落边界切块，合并小段落，避免断句影响检索质量

### 后续优化（全部完成 2026-06-11）

- [x] **Quiz 历史记录**：`list_quizzes` API + 前端历史面板，可加载历史 quiz 重做
- [x] **LangGraph Reflection 节点**：chat 图加入 reflect → retry 循环，短回答自动扩大召回重试一次
- [x] **学习规划 Agent**：`POST /profile/study-plan`，LLM 根据掌握度生成优先级排序文档计划，前端画像页展示
- [x] **Docker Compose 完善**：三服务加 healthcheck，新增 api 服务（Dockerfile），depends_on 带健康检查条件

### P4 — 远期（Phase 4）

- [ ] OCR（处理扫描版 PDF）
- [ ] 语音导师（TTS / STT）
- [ ] AI 白板（知识点关联图）
- [ ] 多学科人格切换
