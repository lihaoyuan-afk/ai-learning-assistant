"use client";

import { FormEvent, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import Link from "next/link";
import { getDocuments, streamGlobalSearch } from "@/lib/api";
import type { HistoryMessage } from "@/lib/api";
import type { SourceChunk } from "@/lib/types";

type MessageEntry = {
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
};

export default function GlobalSearchPage() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<MessageEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [docTitles, setDocTitles] = useState<Record<string, string>>({});

  // Load document id→title map so source chips show real names
  useEffect(() => {
    getDocuments()
      .then((res) => {
        const map: Record<string, string> = {};
        res.documents.forEach((doc) => { map[doc.id] = doc.title; });
        setDocTitles(map);
      })
      .catch(() => {});
  }, []);

  function docLabel(id: string): string {
    return docTitles[id] ?? `文档 ${id.slice(0, 8)}…`;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim() || isStreaming) return;

    const currentQuestion = question.trim();
    setQuestion("");
    setError(null);

    const history: HistoryMessage[] = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    setMessages((prev) => [...prev, { role: "user", content: currentQuestion }]);
    setIsStreaming(true);
    let answerText = "";
    let answerSources: SourceChunk[] = [];

    try {
      for await (const event of streamGlobalSearch(currentQuestion, history)) {
        if (event.type === "sources") {
          answerSources = event.sources;
        } else if (event.type === "token") {
          answerText += event.content;
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === "assistant") {
              return [...prev.slice(0, -1), { ...last, content: answerText }];
            }
            return [...prev, { role: "assistant", content: answerText, sources: [] }];
          });
        } else if (event.type === "error") {
          setError(event.detail);
          break;
        } else if (event.type === "done") {
          break;
        }
      }
      if (answerSources.length > 0) {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant") {
            return [...prev.slice(0, -1), { ...last, sources: answerSources }];
          }
          return prev;
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "请求失败");
    } finally {
      setIsStreaming(false);
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <h1>全局搜索</h1>
          <p>跨所有已上传资料检索并回答问题。</p>
        </div>
        {messages.length > 0 && (
          <button className="button" onClick={() => setMessages([])} type="button" style={{ opacity: 0.7 }}>
            清空对话
          </button>
        )}
      </header>

      {messages.map((msg, idx) => (
        <section
          key={idx}
          className="panel"
          style={{
            borderLeft: msg.role === "user" ? "3px solid var(--accent, #5b6af8)" : "none",
          }}
        >
          <p style={{ fontSize: "0.75rem", opacity: 0.5, marginBottom: "0.5rem" }}>
            {msg.role === "user" ? "你" : "助手"}
          </p>
          {msg.role === "user" ? (
            <p>{msg.content}</p>
          ) : (
            <div className="prose">
              <ReactMarkdown>{msg.content || " "}</ReactMarkdown>
              {isStreaming && idx === messages.length - 1 && (
                <span className="streaming-cursor" aria-hidden="true">▍</span>
              )}
            </div>
          )}
          {msg.sources && msg.sources.length > 0 && (
            <details style={{ marginTop: "0.75rem" }}>
              <summary style={{ fontSize: "0.8rem", opacity: 0.6, cursor: "pointer" }}>
                来源片段（{msg.sources.length} 条，来自多份资料）
              </summary>
              {msg.sources.map((chunk) => (
                <article className="card" key={chunk.id} style={{ marginTop: "0.5rem" }}>
                  <p style={{ fontSize: "0.8rem", opacity: 0.6, marginBottom: "0.25rem" }}>
                    <Link href={`/documents/${chunk.document_id}`} style={{ textDecoration: "underline" }}>
                      {docLabel(chunk.document_id)}
                    </Link>
                    {" · "}第 {chunk.page_number ?? "?"} 页
                    {chunk.score != null ? `  ·  相关度 ${(chunk.score * 100).toFixed(0)}%` : ""}
                  </p>
                  <p style={{ fontSize: "0.9rem" }}>{chunk.content}</p>
                </article>
              ))}
            </details>
          )}
        </section>
      ))}

      {error ? (
        <div className="empty" style={{ color: "var(--color-danger, #c0392b)" }}>
          {error}
        </div>
      ) : null}

      <section className="panel">
        <form className="form" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="question">
              {messages.length > 0 ? "继续追问" : "搜索所有资料"}
            </label>
            <textarea
              id="question"
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="输入问题，将在所有已上传资料中检索…"
              value={question}
            />
          </div>
          <button className="button" disabled={!question.trim() || isStreaming} type="submit">
            {isStreaming ? "检索中…" : "搜索"}
          </button>
        </form>
      </section>
    </div>
  );
}
