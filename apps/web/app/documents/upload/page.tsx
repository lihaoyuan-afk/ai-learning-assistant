"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getDocument, uploadDocument } from "@/lib/api";
import type { DocumentRead } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = {
  uploaded: "已接收，等待处理…",
  processing: "解析中，正在生成向量索引…",
  ready: "就绪",
  failed: "解析失败",
};

const POLL_INTERVAL_MS = 2500;

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [document, setDocument] = useState<DocumentRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Poll until document reaches a terminal status
  useEffect(() => {
    if (!document) return;
    if (document.status === "ready" || document.status === "failed") {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }

    pollRef.current = setInterval(async () => {
      try {
        const updated = await getDocument(document.id);
        setDocument(updated);
      } catch {
        // network hiccup — keep polling
      }
    }, POLL_INTERVAL_MS);

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [document?.id, document?.status]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setDocument(null);

    try {
      const response = await uploadDocument(file);
      setDocument(response.document);
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setIsUploading(false);
    }
  }

  const isProcessing =
    document && document.status !== "ready" && document.status !== "failed";

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <h1>上传 PDF</h1>
          <p>第一阶段只接收 PDF，最大 50 MB。</p>
        </div>
      </header>

      <section className="panel">
        <form className="form" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="file">文件</label>
            <input
              accept="application/pdf"
              id="file"
              name="file"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
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

      {error ? (
        <div className="empty" style={{ color: "var(--color-danger, #c0392b)" }}>
          {error}
        </div>
      ) : null}

      {/* Processing progress */}
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

      {/* Failed */}
      {document?.status === "failed" ? (
        <section className="panel" style={{ borderLeft: "3px solid var(--color-danger, #c0392b)" }}>
          <p style={{ fontWeight: 600, color: "var(--color-danger, #c0392b)", margin: "0 0 0.25rem" }}>
            解析失败
          </p>
          <p style={{ margin: 0, fontSize: "0.9rem", opacity: 0.7 }}>
            {document.title} — 请检查文件是否为有效 PDF，或重新上传。
          </p>
        </section>
      ) : null}

      {/* Ready */}
      {document?.status === "ready" ? (
        <section className="card" style={{ borderLeft: "3px solid var(--color-success, #16a34a)" }}>
          <p style={{ fontWeight: 600, color: "var(--color-success, #16a34a)", margin: "0 0 0.25rem" }}>
            解析完成
          </p>
          <p style={{ margin: "0 0 0.75rem", fontSize: "0.9rem" }}>{document.title}</p>
          <div className="actions">
            <Link className="button" href={`/documents/${document.id}/chat`}>
              开始问答
            </Link>
            <Link className="button secondary" href={`/documents/${document.id}`}>
              文档详情
            </Link>
          </div>
        </section>
      ) : null}
    </div>
  );
}
