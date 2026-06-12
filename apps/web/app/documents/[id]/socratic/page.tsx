"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getDocument, streamSocratic, type HistoryMessage } from "@/lib/api";
import type { DocumentRead } from "@/lib/types";

type ChatTurn = { role: "assistant" | "user"; content: string };

export default function SocraticPage() {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<DocumentRead | null>(null);
  const [topic, setTopic] = useState("");
  const [started, setStarted] = useState(false);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getDocument(id).then(setDoc).catch(() => {});
  }, [id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, streaming]);

  async function startSession() {
    setStarted(true);
    setTurns([]);
    setError(null);
    await streamTurn(null, topic || undefined);
  }

  async function streamTurn(userAnswer: string | null, topicHint?: string) {
    setStreaming(true);
    const history: HistoryMessage[] = turns.map((t) => ({ role: t.role, content: t.content }));

    if (userAnswer !== null) {
      setTurns((prev) => [...prev, { role: "user", content: userAnswer }]);
    }

    let accumulated = "";
    setTurns((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      for await (const event of streamSocratic(id, {
        user_answer: userAnswer ?? undefined,
        history,
        topic: topicHint,
      })) {
        if (event.type === "token") {
          accumulated += event.content;
          setTurns((prev) => {
            const next = [...prev];
            next[next.length - 1] = { role: "assistant", content: accumulated };
            return next;
          });
        } else if (event.type === "error") {
          setError(event.detail);
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "请求失败");
    } finally {
      setStreaming(false);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const answer = input.trim();
    if (!answer || streaming) return;
    setInput("");
    await streamTurn(answer);
  }

  if (!doc) return <div className="page"><div className="empty">加载中…</div></div>;

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <h1>苏格拉底对话</h1>
          <p style={{ opacity: 0.65 }}>{doc.title}</p>
        </div>
        <div className="actions">
          <Link className="button secondary" href={`/documents/${id}`}>返回文档</Link>
        </div>
      </header>

      {!started ? (
        <section className="panel">
          <p style={{ marginBottom: "0.75rem" }}>
            AI 将通过一系列启发性问题，引导你深入理解文档内容，而不是直接给出答案。
          </p>
          <div className="field" style={{ marginBottom: "0.75rem" }}>
            <label htmlFor="topic">聚焦主题（选填）</label>
            <input
              id="topic"
              placeholder="留空则覆盖全文，或输入如「第二章」「梯度下降」"
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              style={{ width: "100%" }}
            />
          </div>
          <button className="button" onClick={startSession}>开始对话</button>
        </section>
      ) : (
        <>
          <div style={{ marginBottom: "1rem" }}>
            {turns.map((turn, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  justifyContent: turn.role === "user" ? "flex-end" : "flex-start",
                  marginBottom: "0.75rem",
                }}
              >
                <div
                  style={{
                    maxWidth: "75%",
                    padding: "0.6rem 0.9rem",
                    borderRadius: "8px",
                    background: turn.role === "user"
                      ? "var(--color-primary, #2563eb)"
                      : "var(--panel-bg, #f1f5f9)",
                    color: turn.role === "user" ? "#fff" : "inherit",
                    lineHeight: 1.6,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {turn.content || (streaming && i === turns.length - 1 ? "▌" : "")}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {error && (
            <div className="empty" style={{ color: "var(--color-danger, #c0392b)" }}>{error}</div>
          )}

          <form onSubmit={handleSubmit} style={{ display: "flex", gap: "0.5rem" }}>
            <input
              disabled={streaming}
              placeholder="输入你的回答…"
              style={{ flex: 1, padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border, #e5e7eb)" }}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button className="button" disabled={!input.trim() || streaming} type="submit">
              {streaming ? "…" : "发送"}
            </button>
          </form>

          <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem" }}>
            <button
              className="button secondary"
              style={{ fontSize: "0.82rem" }}
              onClick={() => { setStarted(false); setTurns([]); }}
            >
              重新开始
            </button>
          </div>
        </>
      )}
    </div>
  );
}
