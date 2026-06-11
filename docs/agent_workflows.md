# Agent 工作流

## Phase 1 工作流

```text
用户请求
↓
加载文档状态
↓
检索相关 chunks
↓
根据任务类型选择节点
↓
执行：
  answer_question
  generate_summary
  generate_quiz
↓
返回结果和来源
```

## Phase 1 节点

| 节点 | 输入 | 输出 |
| --- | --- | --- |
| retrieve_context | document_id, query | chunks |
| answer_question | query, chunks | answer, sources |
| generate_summary | document_id, chunks | summary |
| generate_quiz | document_id, chunks | questions |

## Phase 3 目标工作流

```text
用户输入
↓
Planner Agent 判断意图
↓
选择 Tutor / Quiz / Review / Research
↓
调用工具和记忆
↓
Reflection Agent 检查质量
↓
Memory Agent 更新用户状态
```

