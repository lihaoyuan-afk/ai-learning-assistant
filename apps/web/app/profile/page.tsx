"use client";

import { useEffect, useState } from "react";
import { getMastery, generateStudyPlan } from "@/lib/api";
import type { MasteryItem, MasteryResponse, StudyPlan } from "@/lib/types";

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

function MasteryBar({ item }: { item: MasteryItem }) {
  const color = masteryColor(item.mastery_score);
  const total = item.correct_count + item.mistake_count;

  return (
    <article className="card" style={{ padding: "0.75rem 1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
        <span style={{ fontWeight: 500, fontSize: "0.95rem" }}>{item.knowledge_point}</span>
        <span style={{ fontSize: "0.8rem", fontWeight: 600, color, background: `${color}18`, padding: "0.1rem 0.45rem", borderRadius: "999px" }}>
          {item.mastery_score}% · {masteryLabel(item.mastery_score)}
        </span>
      </div>

      <div style={{ height: "6px", borderRadius: "3px", background: "var(--bg-subtle, #f1f5f9)", overflow: "hidden", marginBottom: "0.35rem" }}>
        <div
          style={{
            height: "100%",
            width: `${item.mastery_score}%`,
            background: color,
            borderRadius: "3px",
            transition: "width 0.4s ease",
          }}
        />
      </div>

      <p style={{ fontSize: "0.75rem", opacity: 0.55, margin: 0 }}>
        答对 {item.correct_count} · 答错 {item.mistake_count}
        {total > 0 ? ` · 共 ${total} 次` : ""}
        {item.last_reviewed_at
          ? ` · 最近练习 ${new Date(item.last_reviewed_at).toLocaleDateString("zh-CN")}`
          : ""}
      </p>
    </article>
  );
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <article className="card" style={{ textAlign: "center", padding: "1rem" }}>
      <p style={{ fontSize: "1.6rem", fontWeight: 700, margin: "0 0 0.2rem" }}>{value}</p>
      <p style={{ fontSize: "0.85rem", fontWeight: 500, margin: 0 }}>{label}</p>
      {sub && <p style={{ fontSize: "0.75rem", opacity: 0.5, margin: "0.15rem 0 0" }}>{sub}</p>}
    </article>
  );
}

function StudyPlanPanel({ plan, onRegenerate, isLoading }: {
  plan: StudyPlan | null;
  onRegenerate: () => void;
  isLoading: boolean;
}) {
  return (
    <section style={{ marginBottom: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
        <h2 style={{ fontSize: "0.9rem", opacity: 0.6, fontWeight: 600, margin: 0 }}>学习计划</h2>
        <button
          className="button"
          style={{ fontSize: "0.8rem", padding: "0.25rem 0.65rem", opacity: isLoading ? 0.6 : 1 }}
          onClick={onRegenerate}
          disabled={isLoading}
          type="button"
        >
          {isLoading ? "生成中…" : plan ? "重新生成" : "生成学习计划"}
        </button>
      </div>

      {plan && plan.items.length === 0 && (
        <div className="empty" style={{ fontSize: "0.85rem" }}>还没有上传文档，无法生成学习计划。</div>
      )}

      {plan && plan.items.length > 0 && (
        <div className="list" style={{ gap: "0.4rem" }}>
          {plan.items.map((item, i) => (
            <article key={item.document_id} className="card" style={{ padding: "0.75rem 1rem" }}>
              <div style={{ display: "flex", gap: "0.6rem", alignItems: "flex-start" }}>
                <span style={{
                  minWidth: "1.5rem", height: "1.5rem", borderRadius: "50%",
                  background: "var(--color-primary, #2563eb)", color: "#fff",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "0.75rem", fontWeight: 700, flexShrink: 0,
                }}>
                  {i + 1}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontWeight: 600, margin: "0 0 0.2rem", fontSize: "0.9rem" }}>{item.document_title}</p>
                  <p style={{ fontSize: "0.8rem", opacity: 0.65, margin: 0 }}>{item.reason}</p>
                </div>
              </div>
            </article>
          ))}
          <p style={{ fontSize: "0.7rem", opacity: 0.4, textAlign: "right", margin: "0.25rem 0 0" }}>
            生成于 {new Date(plan.generated_at).toLocaleString("zh-CN")}
          </p>
        </div>
      )}

      {!plan && !isLoading && (
        <div className="empty" style={{ fontSize: "0.85rem" }}>点击「生成学习计划」，AI 将根据你的掌握情况推荐学习顺序。</div>
      )}
    </section>
  );
}

export default function ProfilePage() {
  const [data, setData] = useState<MasteryResponse | null>(null);
  const [plan, setPlan] = useState<StudyPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isPlanLoading, setIsPlanLoading] = useState(false);

  useEffect(() => {
    getMastery()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"))
      .finally(() => setIsLoading(false));
  }, []);

  async function handleGeneratePlan() {
    setIsPlanLoading(true);
    setPlanError(null);
    try {
      setPlan(await generateStudyPlan());
    } catch (e) {
      setPlanError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setIsPlanLoading(false);
    }
  }

  const weakItems = data?.items.filter((i) => i.mastery_score < 40) ?? [];
  const masteredItems = data?.items.filter((i) => i.mastery_score >= 70) ?? [];

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <h1>学习画像</h1>
          <p>
            {data
              ? `追踪了 ${data.total} 个知识点 · 平均掌握度 ${data.average_score}%`
              : "完成 Quiz 答题后，掌握度将自动更新。"}
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
          还没有答题记录。去完成一份 Quiz，掌握度将自动追踪。
        </div>
      )}

      {/* Study plan — always visible */}
      {!isLoading && (
        <>
          {planError && (
            <div className="empty" style={{ color: "var(--color-danger, #c0392b)", marginBottom: "0.5rem" }}>
              {planError}
            </div>
          )}
          <StudyPlanPanel plan={plan} onRegenerate={handleGeneratePlan} isLoading={isPlanLoading} />
        </>
      )}

      {data && data.total > 0 && (
        <>
          <section className="grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem", marginBottom: "1rem" }}>
            <StatCard label="追踪知识点" value={String(data.total)} />
            <StatCard label="平均掌握度" value={`${data.average_score}%`} />
            <StatCard
              label="已掌握"
              value={String(masteredItems.length)}
              sub={`${data.total > 0 ? Math.round((masteredItems.length / data.total) * 100) : 0}%`}
            />
          </section>

          {weakItems.length > 0 && (
            <section style={{ marginBottom: "1rem" }}>
              <h2 style={{ fontSize: "0.9rem", opacity: 0.6, fontWeight: 600, marginBottom: "0.5rem" }}>
                待加强（{weakItems.length} 个）
              </h2>
              <div className="list" style={{ gap: "0.4rem" }}>
                {weakItems.map((item) => (
                  <MasteryBar key={item.knowledge_point} item={item} />
                ))}
              </div>
            </section>
          )}

          <section>
            <h2 style={{ fontSize: "0.9rem", opacity: 0.6, fontWeight: 600, marginBottom: "0.5rem" }}>
              全部知识点（掌握度由低到高）
            </h2>
            <div className="list" style={{ gap: "0.4rem" }}>
              {data.items.map((item) => (
                <MasteryBar key={item.knowledge_point} item={item} />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
