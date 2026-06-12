"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { streamChat } from "@/lib/api";
import type { HistoryMessage } from "@/lib/api";
import type { SourceChunk } from "@/lib/types";
import { TTSButton } from "@/components/tts-button";

type MessageEntry = {
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
};

const STORAGE_KEY = (id: string) => `chat-history-${id}`;

export default function DocumentChatPage() {
  const params = useParams<{ id: string }>();
  const documentId = params.id;
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<MessageEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const initializedRef = useRef(false);

  // Restore history from localStorage on mount
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    try {
      const stored = localStorage.getItem(STORAGE_KEY(documentId));
      if (stored) setMessages(JSON.parse(stored));
    } catch { /* ignore */ }
  }, [documentId]);

  // Persist history to localStorage whenever messages change
  useEffect(() => {
    if (!initializedRef.current) return;
    if (messages.length > 0) {
      localStorage.setItem(STORAGE_KEY(documentId), JSON.stringify(messages));
    } else {
      localStorage.removeItem(STORAGE_KEY(documentId));
    }
  }, [messages, documentId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim() || isStreaming) return;

    const currentQuestion = question.trim();
    setQuestion("");
    setError(null);

    // Build history from current conversation (exclude sources metadata)
    const history: HistoryMessage[] = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    // Optimistically add user message
    setMessages((prev) => [...prev, { role: "user", content: currentQuestion }]);

    setIsStreaming(true);
    let answerText = "";
    let answerSources: SourceChunk[] = [];

    try {
      for await (const event of streamChat(documentId, currentQuestion, history)) {
        if (event.type === "sources") {
          answerSources = event.sources;
        } else if (event.type === "token") {
          answerText += event.content;
          // Update the streaming assistant message in place
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
      // Attach sources to final assistant message
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
          <h1>资料问答</h1>
          <p>回答仅基于文档内容，附来源页码。支持多轮追问。</p>
        </div>
        {messages.length > 0 && (
          <button
            className="button"
            onClick={() => {
              setMessages([]);
              localStorage.removeItem(STORAGE_KEY(documentId));
            }}
            type="button"
            style={{ opacity: 0.7 }}
          >
            清空对话
          </button>
        )}
      </header>

      {/* Conversation history */}
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
              {isStreaming && idx === messages.length - 1 ? (
                <span className="streaming-cursor" aria-hidden="true">▍</span>
              ) : (
                msg.content && (
                  <div style={{ marginTop: "0.5rem" }}>
                    <TTSButton text={msg.content} />
                  </div>
                )
              )}
            </div>
          )}
          {msg.sources && msg.sources.length > 0 && (
            <details style={{ marginTop: "0.75rem" }}>
              <summary style={{ fontSize: "0.8rem", opacity: 0.6, cursor: "pointer" }}>
                来源片段（{msg.sources.length} 条）
              </summary>
              {msg.sources.map((chunk) => (
                <article className="card" key={chunk.id} style={{ marginTop: "0.5rem" }}>
                  <p style={{ fontSize: "0.8rem", opacity: 0.6, marginBottom: "0.25rem" }}>
                    第 {chunk.page_number ?? "?"} 页
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
              {messages.length > 0 ? "继续提问" : "问题"}
            </label>
            <textarea
              id="question"
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={messages.length > 0 ? "继续追问…" : "请输入你的问题…"}
              value={question}
            />
          </div>
          <button className="button" disabled={!question.trim() || isStreaming} type="submit">
            {isStreaming ? "思考中…" : "提问"}
          </button>
        </form>
      </section>
    </div>
  );
}
