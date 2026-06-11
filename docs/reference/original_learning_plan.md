我已经帮你整理成一份完整的 Markdown 文档，你可以直接复制保存为 `AI_Learning_Assistant_Agent_Plan.md`。

# AI 学习助手 Agent 项目计划书

## 项目目标

构建一个 AI 学习助手 Agent，用户上传：

* PDF
* PPT
* Markdown
* 视频字幕
* 课堂笔记

Agent 自动：

```text
理解内容
↓
建立知识库
↓
生成笔记
↓
生成思维导图
↓
生成Quiz
↓
生成复习计划
↓
检测薄弱点
↓
持续记忆学习进度
```

最终目标类似：

* NotebookLM
* Perplexity Labs
* Khanmigo
* Anki + AI
* AI Tutor

的结合体。

---

# 一、项目整体架构

建议技术栈：

```text
Frontend:
Next.js

Backend:
FastAPI

Agent:
LangGraph

LLM:
Claude / OpenAI

Database:
Postgres

Vector DB:
Qdrant

Queue:
Redis

Storage:
S3 / Supabase

Auth:
Clerk
```

---

# 二、系统架构设计

## 总体架构

```text
用户
↓
Web UI
↓
API Gateway
↓
Agent Orchestrator
↓
多个Agent协作
↓
Memory / RAG / Tools
```

---

# 三、核心 Agent 设计

---

## Agent 1：Document Understanding Agent

负责：

```text
解析PDF
提取结构
识别章节
提取公式
提取图片
生成摘要
```

技术：

```text
PyMuPDF
unstructured
OCR
```

输出：

```json
{
  "chapters": [],
  "summary": "",
  "keywords": []
}
```

---

## Agent 2：Knowledge Graph Agent

负责：

```text
建立知识点关系
```

例如：

```text
微积分
↕
导数
↕
链式法则
↕
积分
```

建议：

```text
NetworkX
Neo4j
```

---

## Agent 3：Tutor Agent

负责：

```text
回答问题
解释概念
举例
类比
循序渐进教学
```

不要直接给答案，而是：

```text
判断用户水平
↓
选择教学策略
↓
一步一步引导
```

例如：

* beginner
* intermediate
* advanced

使用不同 Prompt。

---

## Agent 4：Quiz Agent

负责：

```text
自动生成：
选择题
填空题
问答题
```

并且：

```text
动态调整难度
```

---

## Agent 5：Review Planner Agent

核心：

艾宾浩斯复习算法。

根据：

```text
错误率
掌握度
时间间隔
```

自动安排：

```text
今天复习什么
```

---

## Agent 6：Memory Agent

记录：

```text
用户学过什么
哪里不会
经常错什么
```

这是普通 AI 与真正学习 Agent 的关键区别。

---

# 四、阶段开发路线

---

# Phase 1（2周）

## 目标

做 MVP：

```text
上传PDF
↓
提问
↓
生成总结
↓
生成Quiz
```

---

## 技术路线

### 后端

```text
FastAPI
```

---

### RAG

```text
LlamaIndex
或 LangChain
```

---

### 向量库

```text
Qdrant
```

---

### 模型

建议：

```text
Claude Sonnet
```

因为：

* 长文本能力强
* 教材理解强
* 总结能力强

---

## 页面设计

### 页面1：上传

```text
拖拽PDF
```

---

### 页面2：聊天

```text
针对教材问问题
```

---

### 页面3：Quiz

```text
自动生成题目
```

---

## Phase 1 目标

14天内上线。

重点：

```text
跑通闭环
```

---

# Phase 2（3~4周）

加入：

```text
学习状态系统
```

新增：

```text
用户档案
知识掌握度
学习记录
```

---

## 新功能

### 学习画像

例如：

```json
{
  "math": 70,
  "physics": 40
}
```

---

### 错题本

记录：

```text
错过什么题
```

---

### 自动复习

每天推荐：

```text
今日学习
今日复习
```

---

# Phase 3（1个月）

真正进入 Agent 化。

---

## Multi-Agent System

使用：

```text
LangGraph
```

---

## Workflow

```text
用户提问
↓
Planner Agent
↓
选择：
  Tutor
  Quiz
  Review
  Research
↓
生成结果
```

---

## Reflection

例如：

```text
回答是否太难？
用户是否理解？
是否需要换种解释？
```

---

## Self-Improvement

Agent 自动：

```text
分析用户错误模式
```

例如：

```text
总是错积分
```

然后：

```text
自动增加积分练习
```

---

# 五、推荐技术栈

## Agent Framework

首选：

```text
LangGraph
```

不要一开始陷入：

```text
AutoGen
CrewAI
```

原因：

* 黑盒太多
* 难控制
* 不适合深入学习

---

# 六、数据库设计

## User

```sql
users
```

---

## Documents

```sql
documents
```

---

## Chunks

```sql
chunks
```

---

## Quiz

```sql
quiz_history
```

---

## Memory

```sql
learning_memory
```

---

# 七、Prompt Engineering 设计

---

## Tutor Prompt

```text
你是一个耐心的老师。

你必须：
- 不直接给答案
- 先确认用户理解
- 逐步教学
- 使用类比
- 给生活中的例子
```

---

## Quiz Prompt

```text
根据教材生成：
- 3道简单题
- 2道中等题
- 1道困难题
```

---

# 八、长期进化路线

---

# V2

加入：

## OCR

支持：

* 拍照题目
* 手写笔记

---

# V3

加入：

## Voice Tutor

语音学习。

---

# V4

加入：

## AI 白板

边讲边画图。

---

# V5

加入：

## 多Agent协作老师

例如：

```text
数学老师
物理老师
英语老师
```

---

# 九、Claude Code 的最佳使用方式

---

## 用 Claude Code 做：

### 1. 架构设计

```text
设计项目结构
```

---

### 2. Refactor

```text
把Quiz模块拆分
```

---

### 3. Agent Workflow

```text
设计LangGraph状态机
```

---

# 十、Codex 的最佳使用方式

---

## 用 Codex 做：

### 快速生成：

```text
CRUD
API
Tests
Schemas
```

---

### 自动修复：

```text
跑测试
修复错误
```

---

# 十一、真正要学习的核心

不是：

```text
怎么调用API
```

而是：

```text
怎么设计 Agent 系统
```

包括：

* 状态
* 工作流
* 记忆
* 规划
* 工具调用
* 反思
* 用户建模

---

# 十二、建议开发节奏

每天：

---

## 2小时开发

---

## 1小时读源码

推荐：

* LangGraph
* OpenHands
* Claude Code相关项目

---

## 1小时研究 Prompt

这是高价值能力。

---

# 十三、最终成果目标

用户上传一本教材后：

```text
建立知识图谱
↓
生成学习路线
↓
每天安排学习
↓
检测薄弱点
↓
动态调整题目
↓
长期记忆学习状态
```

最终做出的不是：

```text
AI ChatBot
```

而是：

```text
AI Learning Operating System
```
