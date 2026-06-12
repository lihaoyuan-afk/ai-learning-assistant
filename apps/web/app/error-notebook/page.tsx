"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getErrorNotebook, scheduleReview } from "@/lib/api";
import type { ErrorGroup, ErrorNotebookResponse } from "@/lib/types";

export default function ErrorNotebookPage() {
  const [data, setData] = useState<ErrorNotebookResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [scheduled, setScheduled] = useState<Set<string>>(new Set());

  useEffect(() => {
    getErrorNotebook()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"))
      .finally(() => setLoading(false));
  }, []);

  function toggle(kp: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(kp) ? next.delete(kp) : next.add(kp);
      return next;
    });
  }

  async function handleSchedule(kp: string) {
    try {
      await scheduleReview(kp);
      setScheduled((prev) => new Set(prev).add(kp));
    } catch { /* ignore */ }
  }

  const masteryColor = (score: number | null | undefined) => {
    if (score == null) return "#888";
    if (score < 40) return "var(--color-danger, #c0392b)";
    if (score < 70) return "var(--color-warning, #d97706)";
    return "var(--color-success, #16a34a)";
  };

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <h1>错题本</h1>
          <p>按知识点汇总所有答错的选择题，帮助找到薄弱环节。</p>
        </div>
      </header>

      {loading && <div className="empty">加载中…</div>}
      {error && <div className="empty" style={{ color: "var(--color-danger, #c0392b)" }}>{error}</div>}

      {data && data.groups.length === 0 && (
        <div className="empty">
          <p>暂无错题记录。</p>
          <p style={{ fontSize: "0.85rem", opacity: 0.6 }}>完成 Quiz 并提交答案后，答错的题目会出现在这里。</p>
        </div>
      )}

      {data && data.groups.length > 0 && (
        <>
          <div style={{ marginBottom: "1rem", opacity: 0.65, fontSize: "0.85rem" }}>
            共 {data.groups.length} 个薄弱知识点，{data.total_mistakes} 次错误
          </div>

          {data.groups.map((group) => (
            <section key={group.knowledge_point} className="panel" style={{ marginBottom: "0.75rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <div
                  style={{ flex: 1, cursor: "pointer" }}
                  onClick={() => toggle(group.knowledge_point)}
                >
                  <span style={{ fontWeight: 600 }}>{group.knowledge_point}</span>
                  <span style={{ marginLeft: "0.5rem", fontSize: "0.82rem", opacity: 0.6 }}>
                    {group.entries.length} 道题 · 共答错 {group.mistake_count} 次
                  </span>
                </div>
                {group.mastery_score != null && (
                  <span style={{
                    fontSize: "0.8rem",
                    fontWeight: 600,
                    color: masteryColor(group.mastery_score),
                    border: `1px solid ${masteryColor(group.mastery_score)}`,
                    borderRadius: "4px",
                    padding: "1px 6px",
                  }}>
                    掌握度 {group.mastery_score}
                  </span>
                )}
                <button
                  onClick={() => handleSchedule(group.knowledge_point)}
                  disabled={scheduled.has(group.knowledge_point)}
                  title="安排 3 天后出现在今日复习"
                  style={{
                    fontSize: "0.75rem",
                    padding: "1px 7px",
                    borderRadius: "4px",
                    border: "1px solid var(--border, #e5e7eb)",
                    background: scheduled.has(group.knowledge_point) ? "var(--bg-subtle,#f1f5f9)" : "#fff",
                    cursor: scheduled.has(group.knowledge_point) ? "default" : "pointer",
                    opacity: scheduled.has(group.knowledge_point) ? 0.6 : 1,
                    whiteSpace: "nowrap",
                  }}
                  type="button"
                >
                  {scheduled.has(group.knowledge_point) ? "已安排 ✓" : "3天后复习"}
                </button>
                <span
                  style={{ opacity: 0.5, userSelect: "none", cursor: "pointer" }}
                  onClick={() => toggle(group.knowledge_point)}
                >
                  {expanded.has(group.knowledge_point) ? "▲" : "▼"}
                </span>
              </div>

              {expanded.has(group.knowledge_point) && (
                <div style={{ marginTop: "0.75rem", borderTop: "1px solid var(--border, #e5e7eb)", paddingTop: "0.75rem" }}>
                  {group.entries.map((entry) => (
                    <div key={entry.question_id} style={{ marginBottom: "1rem" }}>
                      <p style={{ margin: "0 0 0.4rem", fontWeight: 500 }}>
                        {entry.question_text}
                        <span style={{ marginLeft: "0.5rem", fontSize: "0.78rem", opacity: 0.5 }}>
                          (答错 {entry.mistake_count} 次)
                        </span>
                      </p>
                      <ul style={{ margin: "0 0 0.4rem", paddingLeft: "1.4rem" }}>
                        {entry.options.map((opt, i) => {
                          const letter = String.fromCharCode(65 + i);
                          const isCorrect = letter === entry.correct_answer.charAt(0).toUpperCase();
                          return (
                            <li key={i} style={{ color: isCorrect ? "var(--color-success, #16a34a)" : "inherit", fontWeight: isCorrect ? 600 : 400 }}>
                              {letter}. {opt}
                            </li>
                          );
                        })}
                      </ul>
                      {entry.explanation && (
                        <p style={{ margin: "0 0 0.4rem", fontSize: "0.85rem", opacity: 0.7 }}>
                          解析：{entry.explanation}
                        </p>
                      )}
                      {entry.document_id && (
                        <Link href={`/documents/${entry.document_id}/quiz`} style={{ fontSize: "0.8rem", opacity: 0.5 }}>
                          前往文档练习 →
                        </Link>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>
          ))}
        </>
      )}
    </div>
  );
}
