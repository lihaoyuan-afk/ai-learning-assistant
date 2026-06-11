"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { getDocument, streamSummary } from "@/lib/api";

export default function DocumentSummaryPage() {
  const params = useParams<{ id: string }>();
  const documentId = params.id;
  const [summaryText, setSummaryText] = useState<string>("");
  const [isCached, setIsCached] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const abortRef = useRef<boolean>(false);

  // Load cached summary on mount
  useEffect(() => {
    getDocument(documentId)
      .then((doc) => {
        if (doc.summary) {
          setSummaryText(doc.summary);
          setIsCached(true);
        }
      })
      .catch(() => {})
      .finally(() => setInitialLoading(false));
  }, [documentId]);

  async function handleGenerate() {
    setIsStreaming(true);
    setError(null);
    setSummaryText("");
    setIsCached(false);
    abortRef.current = false;

    try {
      for await (const event of streamSummary(documentId)) {
        if (abortRef.current) break;
        if (event.type === "token") {
          setSummaryText((prev) => prev + event.content);
        } else if (event.type === "cached") {
          setIsCached(true);
        } else if (event.type === "error") {
          setError(event.detail);
          break;
        } else if (event.type === "done") {
          break;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setIsStreaming(false);
    }
  }

  const buttonLabel = isStreaming
    ? "生成中…"
    : isCached || summaryText
    ? "重新生成"
    : "生成总结";

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <h1>资料总结</h1>
          <p>基于全文生成结构化学习总结。</p>
        </div>
        <button className="button" disabled={isStreaming || initialLoading} onClick={handleGenerate} type="button">
          {buttonLabel}
        </button>
      </header>

      {error ? (
        <div className="empty" style={{ color: "var(--color-danger, #c0392b)" }}>
          {error}
        </div>
      ) : null}

      <section className="panel">
        {initialLoading ? (
          <p style={{ opacity: 0.5 }}>加载中…</p>
        ) : summaryText ? (
          <>
            {isCached && !isStreaming && (
              <p style={{ fontSize: "0.8rem", opacity: 0.5, marginBottom: "0.75rem" }}>
                已缓存的总结（点击"重新生成"更新）
              </p>
            )}
            <div className="prose">
              <ReactMarkdown>{summaryText}</ReactMarkdown>
            </div>
            {isStreaming && (
              <span className="streaming-cursor" aria-hidden="true">▍</span>
            )}
          </>
        ) : (
          <p style={{ opacity: 0.5 }}>点击"生成总结"开始。</p>
        )}
      </section>
    </div>
  );
}
