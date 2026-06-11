# 数据模型

## users

| 字段 | 说明 |
| --- | --- |
| id | 用户 ID |
| email | 邮箱 |
| display_name | 昵称 |
| created_at | 创建时间 |

## documents

| 字段 | 说明 |
| --- | --- |
| id | 文档 ID |
| user_id | 用户 ID |
| title | 文档标题 |
| file_type | 文件类型 |
| file_path | 本地或云端文件路径 |
| status | uploaded / processing / ready / failed |
| summary | 文档总结 |
| created_at | 创建时间 |

## chunks

| 字段 | 说明 |
| --- | --- |
| id | chunk ID |
| document_id | 文档 ID |
| chunk_index | 片段序号 |
| content | 片段内容 |
| page_number | 页码 |
| section_title | 所属章节 |
| embedding_id | 向量库记录 ID |

## quiz

包含 `quizzes`、`quiz_questions` 和 `quiz_attempts` 三类记录，用于保存题目、答案、解释和用户答题表现。

## learning_memory

记录知识点掌握度、错误次数、上次复习时间和下次复习时间。Phase 2 再正式实现。

