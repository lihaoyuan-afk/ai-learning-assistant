"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getDocument, importDocumentFromUrl, uploadDocument } from "@/lib/api";
import type { DocumentRead } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = {
  uploaded: "已接收，等待处理…",
  processing: "解析中，正在生成向量索引…",
  ready: "就绪",
  failed: "解析失败",
};

const POLL_INTERVAL_MS = 2500;

type Tab = "file" | "url";

export default function UploadPage() {
  const [tab, setTab] = useState<Tab>("file");

  // file tab
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // url tab
  const [url, setUrl] = useState("");
  const [isImporting, setIsImporting] = useState(false);

  // shared
  const [document, setDocument] = useState<DocumentRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!document) return;
    if (document.status === "ready" || document.status === "failed") {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      return;
    }
    pollRef.current = setInterval(async () => {
      try { setDocument(await getDocument(document.id)); } catch { /* network hiccup */ }
    }, POLL_INTERVAL_MS);
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [document?.id, document?.status]);

  async function handleFileSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!file) return;
    setIsUploading(true); setError(null); setDocument(null);
    try {
      const resp = await uploadDocument(file);
      setDocument(resp.document);
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleUrlSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!url.trim()) return;
    setIsImporting(true); setError(null); setDocument(null);
    try {
      const resp = await importDocumentFromUrl(url.trim());
      setDocument(resp.document);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setIsImporting(false);
    }
  }

  const isProcessing = document && document.status !== "ready" && document.status !== "failed";

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <h1>导入资料</h1>
          <p>支持 PDF、TXT、Markdown 上传，或直接粘贴网页/视频链接。</p>
        </div>
      </header>

      {/* Tab switcher */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        {(["file", "url"] as Tab[]).map((t) => (
          <button
            key={t}
            className={`button${tab === t ? "" : " secondary"}`}
            onClick={() => { setTab(t); setError(null); setDocument(null); }}
            type="button"
          >
            {t === "file" ? "上传文件" : "导入链接"}
          </button>
        ))}
      </div>

      {tab === "file" && (
        <section className="panel">
          <form className="form" onSubmit={handleFileSubmit}>
            <div className="field">
              <label htmlFor="file">文件（PDF / TXT / MD，最大 50 MB）</label>
              <input
                accept=".pdf,.txt,.md,.markdown"
                id="file"
                name="file"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                type="file"
              />
            </div>
            <button
              className="button"
              disabled={!file || isUploading || !!isProcessing}
              type="submit"
            >
              {isUploading ? "上传中…" : "上传并解析"}
            </button>
          </form>
        </section>
      )}

      {tab === "url" && (
        <section className="panel">
          <form className="form" onSubmit={handleUrlSubmit}>
            <div className="field">
              <label htmlFor="url">网页或视频链接</label>
              <input
                id="url"
                name="url"
                placeholder="https://example.com/article 或 YouTube/B站视频链接"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                style={{ width: "100%" }}
              />
              <p style={{ margin: "0.3rem 0 0", fontSize: "0.82rem", opacity: 0.6 }}>
                支持任意网页、YouTube 和 B 站视频（提取字幕和简介）
              </p>
            </div>
            <button
              className="button"
              disabled={!url.trim() || isImporting || !!isProcessing}
              type="submit"
            >
              {isImporting ? "正在获取…" : "导入并解析"}
            </button>
          </form>
        </section>
      )}

      {error ? (
        <div className="empty" style={{ color: "var(--color-danger, #c0392b)" }}>
          {error}
        </div>
      ) : null}

      {isProcessing ? (
        <section className="panel" style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span style={{ fontSize: "1.25rem" }}>⏳</span>
          <div>
            <p style={{ margin: 0, fontWeight: 600 }}>{document.title}</p>
            <p style={{ margin: "0.2rem 0 0", fontSize: "0.85rem", opacity: 0.65 }}>
              {STATUS_LABEL[document.status] ?? document.status}
            </p>
          </div>
        </section>
      ) : null}

      {document?.status === "failed" ? (
        <section className="panel" style={{ borderLeft: "3px solid var(--color-danger, #c0392b)" }}>
          <p style={{ fontWeight: 600, color: "var(--color-danger, #c0392b)", margin: "0 0 0.25rem" }}>
            处理失败
          </p>
          <p style={{ margin: 0, fontSize: "0.9rem", opacity: 0.7 }}>
            {document.title} — 请检查链接是否有效或文件是否损坏。
          </p>
        </section>
      ) : null}

      {document?.status === "ready" ? (
        <section className="card" style={{ borderLeft: "3px solid var(--color-success, #16a34a)" }}>
          <p style={{ fontWeight: 600, color: "var(--color-success, #16a34a)", margin: "0 0 0.25rem" }}>
            解析完成
          </p>
          <p style={{ margin: "0 0 0.75rem", fontSize: "0.9rem" }}>{document.title}</p>
          <div className="actions">
            <Link className="button" href={`/documents/${document.id}/chat`}>开始问答</Link>
            <Link className="button secondary" href={`/documents/${document.id}`}>文档详情</Link>
          </div>
        </section>
      ) : null}
    </div>
  );
}
