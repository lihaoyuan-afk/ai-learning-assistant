"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { forkDocument, getPublicDocuments } from "@/lib/api";
import { StatusPill } from "@/components/status-pill";
import type { DocumentRead } from "@/lib/types";

export default function LibraryPage() {
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [forkingId, setForkingId] = useState<string | null>(null);
  const [forkedIds, setForkedIds] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    getPublicDocuments()
      .then((res) => setDocuments(res.documents))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  async function handleFork(e: React.MouseEvent, documentId: string) {
    e.preventDefault();
    e.stopPropagation();
    setForkingId(documentId);
    try {
      await forkDocument(documentId);
      setForkedIds((prev) => new Set([...prev, documentId]));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Fork 失败");
    } finally {
      setForkingId(null);
    }
  }

  const filtered = documents.filter((doc) =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <h1>公共库</h1>
          <p>
            {isLoading
              ? "加载中…"
              : documents.length > 0
              ? `共 ${documents.length} 份公开资料，Fork 到我的库后即可使用问答、Quiz 等功能`
              : "暂无公开资料。在「资料」页将你的文档设为「公开」即可出现在这里。"}
          </p>
        </div>
        <Link className="button" href="/documents">
          我的资料
        </Link>
      </header>

      {documents.length > 0 && (
        <div style={{ marginBottom: "1rem" }}>
          <input
            type="text"
            placeholder="搜索资料名…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: "100%",
              maxWidth: "360px",
              padding: "0.4rem 0.75rem",
              border: "1px solid var(--border, #ddd)",
              borderRadius: "6px",
              fontSize: "0.9rem",
            }}
          />
        </div>
      )}

      <section className="list">
        {isLoading ? (
          <div className="empty">加载中…</div>
        ) : filtered.length === 0 ? (
          <div className="empty">
            {documents.length === 0 ? "暂无公开资料。" : "没有符合条件的资料。"}
          </div>
        ) : (
          filtered.map((doc) => {
            const alreadyForked = forkedIds.has(doc.id);
            return (
              <div key={doc.id} style={{ position: "relative" }}>
                <div className="card" style={{ paddingRight: "6rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <h2 style={{ margin: 0, flex: 1 }}>{doc.title}</h2>
                    <StatusPill>{doc.status === "ready" ? "就绪" : doc.status}</StatusPill>
                  </div>
                  <p style={{ margin: "0.25rem 0 0", fontSize: "0.85rem", color: "var(--text-muted, #888)" }}>
                    {doc.file_type.toUpperCase()} ·{" "}
                    {new Date(doc.created_at).toLocaleString("zh-CN")}
                    {doc.forked_from && " · 已 Fork"}
                  </p>
                  {doc.summary && (
                    <p style={{ margin: "0.5rem 0 0", fontSize: "0.85rem", color: "var(--text-secondary, #555)", overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                      {doc.summary}
                    </p>
                  )}
                </div>
                <button
                  onClick={(e) => handleFork(e, doc.id)}
                  disabled={forkingId === doc.id || alreadyForked}
                  title={alreadyForked ? "已 Fork" : "Fork 到我的资料库"}
                  style={{
                    position: "absolute",
                    top: "50%",
                    right: "0.75rem",
                    transform: "translateY(-50%)",
                    background: alreadyForked ? "#e8f5e9" : "var(--color-primary, #2563eb)",
                    border: "none",
                    borderRadius: "6px",
                    cursor: alreadyForked ? "default" : "pointer",
                    color: alreadyForked ? "#2e7d32" : "#fff",
                    fontSize: "0.8rem",
                    fontWeight: 500,
                    padding: "0.4rem 0.75rem",
                    whiteSpace: "nowrap",
                    opacity: forkingId === doc.id ? 0.5 : 1,
                  }}
                >
                  {forkingId === doc.id ? "Fork 中…" : alreadyForked ? "已 Fork" : "Fork"}
                </button>
              </div>
            );
          })
        )}
      </section>
    </div>
  );
}
