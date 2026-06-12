"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { deleteDocument, getDocuments, setDocumentVisibility } from "@/lib/api";
import { StatusPill } from "@/components/status-pill";
import type { DocumentRead } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = {
  uploaded: "等待解析",
  processing: "解析中…",
  ready: "就绪",
  failed: "解析失败",
};

const STATUS_OPTIONS = [
  { value: "all", label: "全部" },
  { value: "ready", label: "就绪" },
  { value: "processing", label: "解析中" },
  { value: "failed", label: "失败" },
];

const POLL_MS = 2500;

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function fetchDocs() {
    try {
      const res = await getDocuments();
      setDocuments(res.documents);
      return res.documents;
    } catch {
      return [];
    }
  }

  useEffect(() => {
    fetchDocs().finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    const hasPending = documents.some(
      (d) => d.status === "uploaded" || d.status === "processing"
    );
    if (hasPending && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        const updated = await fetchDocs();
        const stillPending = updated.some(
          (d) => d.status === "uploaded" || d.status === "processing"
        );
        if (!stillPending && pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }, POLL_MS);
    } else if (!hasPending && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [documents]);

  async function handleToggleVisibility(e: React.MouseEvent, doc: DocumentRead) {
    e.preventDefault();
    e.stopPropagation();
    setTogglingId(doc.id);
    try {
      const updated = await setDocumentVisibility(doc.id, !doc.is_public);
      setDocuments((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
    } catch (err) {
      alert(err instanceof Error ? err.message : "操作失败");
    } finally {
      setTogglingId(null);
    }
  }

  async function handleDelete(e: React.MouseEvent, documentId: string) {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("确定要删除此文档吗？此操作不可撤销。")) return;
    setDeletingId(documentId);
    try {
      await deleteDocument(documentId);
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
    } catch (err) {
      alert(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeletingId(null);
    }
  }

  const filtered = documents.filter((doc) => {
    const matchesSearch = doc.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || doc.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <h1>学习资料</h1>
          <p>
            {isLoading
              ? "加载中…"
              : documents.length > 0
              ? `共 ${documents.length} 份资料`
              : "资料会在这里进入解析、问答、总结和 Quiz 流程。"}
          </p>
        </div>
        <Link className="button" href="/documents/upload">
          上传 PDF
        </Link>
      </header>

      {documents.length > 0 && (
        <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1rem", flexWrap: "wrap" }}>
          <input
            type="text"
            placeholder="搜索文档名…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              flex: 1,
              minWidth: "160px",
              padding: "0.4rem 0.75rem",
              border: "1px solid var(--border, #ddd)",
              borderRadius: "6px",
              fontSize: "0.9rem",
            }}
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              padding: "0.4rem 0.75rem",
              border: "1px solid var(--border, #ddd)",
              borderRadius: "6px",
              fontSize: "0.9rem",
            }}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      )}

      <section className="list">
        {isLoading ? (
          <div className="empty">加载中…</div>
        ) : filtered.length === 0 ? (
          <div className="empty">
            {documents.length === 0
              ? "暂无资料，点击右上角上传第一份 PDF。"
              : "没有符合条件的资料。"}
          </div>
        ) : (
          filtered.map((document) => (
            <div key={document.id} style={{ position: "relative" }}>
              <Link className="card" href={`/documents/${document.id}`}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <h2 style={{ margin: 0, flex: 1, paddingRight: "2.5rem" }}>{document.title}</h2>
                  <StatusPill>{STATUS_LABEL[document.status] ?? document.status}</StatusPill>
                </div>
                <p style={{ margin: 0 }}>
                  {document.file_type.toUpperCase()} ·{" "}
                  {new Date(document.created_at).toLocaleString("zh-CN")}
                </p>
              </Link>
              <div style={{ position: "absolute", top: "0.75rem", right: "0.75rem", display: "flex", gap: "0.4rem", zIndex: 1 }}>
                <button
                  onClick={(e) => handleToggleVisibility(e, document)}
                  disabled={togglingId === document.id}
                  title={document.is_public ? "设为私有" : "公开分享"}
                  style={{
                    background: document.is_public ? "#e8f5e9" : "none",
                    border: `1px solid ${document.is_public ? "#4caf50" : "var(--border, #ddd)"}`,
                    borderRadius: "4px",
                    cursor: "pointer",
                    color: document.is_public ? "#2e7d32" : "var(--text-muted, #999)",
                    fontSize: "0.7rem",
                    opacity: togglingId === document.id ? 0.4 : 1,
                    padding: "0.15rem 0.4rem",
                    lineHeight: 1.4,
                  }}
                >
                  {togglingId === document.id ? "…" : document.is_public ? "公开" : "私有"}
                </button>
                <button
                  onClick={(e) => handleDelete(e, document.id)}
                  disabled={deletingId === document.id}
                  title="删除文档"
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: "var(--color-danger, #c0392b)",
                    fontSize: "1rem",
                    opacity: deletingId === document.id ? 0.4 : 0.6,
                    padding: "0.25rem",
                    lineHeight: 1,
                  }}
                >
                  {deletingId === document.id ? "…" : "✕"}
                </button>
              </div>
            </div>
          ))
        )}
      </section>
    </div>
  );
}
