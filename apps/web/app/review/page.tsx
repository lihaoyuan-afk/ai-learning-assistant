"use client";

import { useEffect, useState } from "react";
import { getReviewToday } from "@/lib/api";
import type { ReviewItem, ReviewQuestion } from "@/lib/types";

function masteryColor(score: number): string {
  if (score >= 70) return "var(--color-success, #16a34a)";
  if (score >= 40) return "#d97706";
  return "var(--color-danger, #c0392b)";
}

function masteryLabel(score: number): string {
  if (score >= 70) return "已掌握";
  if (score >= 40) return "学习中";
  return "待加强";
}

function QuestionCard({ q }: { q: ReviewQuestion }) {
  const [revealed, setRevealed] = useState(false);

  return (
    <div
      style={{
        background: "var(--bg-subtle, #f8fafc)",
        border: "1px solid var(--border, #e2e8f0)",
        borderRadius: "8px",
        padding: "0.75rem 1rem",
        fontSize: "0.875rem",
      }}
    >
      <p style={{ margin: "0 0 0.5rem", fontWeight: 500, lineHeight: 1.5 }}>{q.question}</p>

      {q.options.length > 0 && (
        <ul style={{ margin: "0 0 0.5rem", paddingLeft: "1.25rem", lineHeight: 1.6 }}>
          {q.options.map((opt, i) => (
            <li key={i} style={{ opacity: 0.8 }}>{opt}</li>
          ))}
        </ul>
      )}

      {!revealed ? (
        <button
          onClick={() => setRevealed(true)}
          style={{
            fontSize: "0.78rem",
            padding: "0.2rem 0.6rem",
            borderRadius: "6px",
            border: "1px solid var(--border, #e2e8f0)",
            background: "transparent",
            cursor: "pointer",
            opacity: 0.7,
          }}
        >
          显示答案
        </button>
      ) : (
        <div
          style={{
            marginTop: "0.4rem",
            padding: "0.45rem 0.65rem",
            background: "var(--color-success-bg, #f0fdf4)",
            borderRadius: "6px",
            borderLeft: "3px solid var(--color-success, #16a34a)",
          }}
        >
          <p style={{ margin: "0 0 0.2rem", fontWeight: 600, fontSize: "0.82rem" }}>
            正确答案：{q.answer}
          </p>
          {q.explanation && (
            <p style={{ margin: 0, opacity: 0.7, fontSize: "0.78rem", lineHeight: 1.5 }}>
              {q.explanation}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function ReviewCard({ item }: { item: ReviewItem }) {
  const [expanded, setExpanded] = useState(false);
  const color = masteryColor(item.mastery_score);

  return (
    <article className="card" style={{ padding: "0.85rem 1rem" }}>
      <div
        style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}
      >
        <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>{item.knowledge_point}</span>
        <span
          style={{
            fontSize: "0.78rem",
            fontWeight: 600,
            color,
            background: `${color}18`,
            padding: "0.1rem 0.45rem",
            borderRadius: "999px",
          }}
        >
          {item.mastery_score}% · {masteryLabel(item.mastery_score)}
        </span>
      </div>

      <div style={{ height: "4px", borderRadius: "2px", background: "var(--bg-subtle, #f1f5f9)", overflow: "hidden", marginBottom: "0.6rem" }}>
        <div
          style={{
            height: "100%",
            width: `${item.mastery_score}%`,
            background: color,
            borderRadius: "2px",
            transition: "width 0.4s ease",
          }}
        />
      </div>

      {item.questions.length > 0 ? (
        <>
          <button
            onClick={() => setExpanded((v) => !v)}
            style={{
              fontSize: "0.8rem",
              padding: "0.2rem 0.55rem",
              borderRadius: "6px",
              border: "1px solid var(--border, #e2e8f0)",
              background: "transparent",
              cursor: "pointer",
              opacity: 0.75,
              marginBottom: expanded ? "0.65rem" : 0,
            }}
          >
            {expanded ? "收起练习题" : `练习 ${item.questions.length} 道题`}
          </button>

          {expanded && (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {item.questions.map((q) => (
                <QuestionCard key={q.id} q={q} />
              ))}
            </div>
          )}
        </>
      ) : (
        <p style={{ fontSize: "0.78rem", opacity: 0.5, margin: 0 }}>暂无关联练习题</p>
      )}
    </article>
  );
}

export default function ReviewPage() {
  const [data, setData] = useState<{ items: ReviewItem[]; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getReviewToday()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <h1>今日复习</h1>
          <p>
            {data
              ? data.total > 0
                ? `${data.total} 个知识点到期，建议今天复习`
                : "今日没有到期的复习任务"
              : "根据掌握度自动安排复习计划"}
          </p>
        </div>
      </header>

      {error && (
        <div className="empty" style={{ color: "var(--color-danger, #c0392b)" }}>
          {error}
        </div>
      )}

      {isLoading && <div className="empty">加载中…</div>}

      {!isLoading && data && data.total === 0 && (
        <div className="empty">
          <p style={{ margin: "0 0 0.5rem" }}>今日没有到期的复习任务。</p>
          <p style={{ margin: 0, opacity: 0.6, fontSize: "0.85rem" }}>
            完成 Quiz 后，系统将根据掌握度自动安排下次复习时间：
            未掌握 → 2 天后，学习中 → 5 天后，已掌握 → 14 天后。
          </p>
        </div>
      )}

      {data && data.total > 0 && (
        <section>
          <div className="list" style={{ gap: "0.5rem" }}>
            {data.items.map((item) => (
              <ReviewCard key={item.knowledge_point} item={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
