# API 说明

## Health

```text
GET /health
```

用于检查后端服务是否启动。

## Documents

```text
POST /documents/upload
GET  /documents
GET  /documents/{document_id}
POST /documents/{document_id}/ingest
```

文档上传、查看和解析入口。

## Chat

```text
POST /documents/{document_id}/chat
```

针对指定文档进行问答。Phase 1 返回回答和引用来源。

## Summary

```text
POST /documents/{document_id}/summary
```

生成指定文档的结构化总结。

## Quiz

```text
POST /documents/{document_id}/quiz
GET  /documents/{document_id}/quiz/{quiz_id}
```

生成并读取指定文档的 Quiz。

