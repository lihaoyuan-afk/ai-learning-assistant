"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { StatusPill } from "@/components/status-pill";
import { deleteDocument, getDocument } from "@/lib/api";
import type { DocumentRead } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = {
  uploaded: "等待解析",
  processing: "解析中…",
  ready: "就绪",
  failed: "解析失败",
};

const featureLinks = [
  { href: "chat", title: "问答", body: "基于文档内容检索并回答问题，附来源页码。" },
  { href: "summary", title: "总结", body: "生成结构化学习总结。" },
  { href: "quiz", title: "Quiz", body: "生成不重复的自测题目。" },
];

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const [document, setDocument] = useState<DocumentRead | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    getDocument(id)
      .then(setDocument)
      .catch(() => setDocument(null))
      .finally(() => setIsLoading(false));
  }, [id]);

  async function handleDelete() {
    if (!confirm("确定要删除此文档吗？删除后将同步清理向量索引和磁盘文件，不可撤销。")) return;
    setIsDeleting(true);
    try {
      await deleteDocument(id);
      router.push("/documents");
    } catch (err) {
      alert(err instanceof Error ? err.message : "删除失败");
      setIsDeleting(false);
    }
  }

  if (isLoading) {
    return <div className="page"><div className="empty">加载中…</div></div>;
  }

  if (!document) {
    return <div className="page"><div className="empty">文档不存在或加载失败</div></div>;
  }

  const createdAt = new Date(document.created_at).toLocaleString("zh-CN");
  const isReady = document.status === "ready";

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <StatusPill>{STATUS_LABEL[document.status] ?? document.status}</StatusPill>
          <h1>{document.title}</h1>
          <p>
            {document.file_type.toUpperCase()} · {createdAt}
          </p>
        </div>
        <button
          className="button"
          onClick={handleDelete}
          disabled={isDeleting}
          style={{ background: "var(--color-danger, #c0392b)", color: "#fff" }}
          type="button"
        >
          {isDeleting ? "删除中…" : "删除文档"}
        </button>
      </header>

      {document.status === "failed" && (
        <div className="empty" style={{ color: "var(--coral, #d15d45)" }}>
          文档解析失败。请检查文件是否为有效 PDF，或重新上传。
        </div>
      )}

      {document.summary && (
        <section className="panel">
          <h2>已生成总结</h2>
          <p style={{ whiteSpace: "pre-wrap" }}>{document.summary}</p>
        </section>
      )}

      {isReady ? (
        <section className="grid">
          {featureLinks.map((item) => (
            <Link className="card" href={`/documents/${id}/${item.href}`} key={item.href}>
              <h2>{item.title}</h2>
              <p>{item.body}</p>
            </Link>
          ))}
        </section>
      ) : (
        <section className="grid">
          {featureLinks.map((item) => (
            <article
              className="card"
              key={item.href}
              style={{ opacity: 0.45, cursor: "not-allowed" }}
            >
              <h2>{item.title}</h2>
              <p>{item.body}</p>
              <p style={{ fontSize: "0.8rem" }}>
                {document.status === "failed" ? "解析失败，不可用" : "文档解析后可用"}
              </p>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
