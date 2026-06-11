"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { createQuiz, getQuizById, listQuizzes, submitQuizAttempt } from "@/lib/api";
import type {
  QuestionResult, QuizQuestion, QuizResponse,
  QuizAttemptResponse, QuizSummary,
} from "@/lib/types";

// ── AnswerCard ─────────────────────────────────────────────────────────────────

function AnswerCard({
  question, index, answer, onChange,
}: {
  question: QuizQuestion; index: number; answer: string; onChange: (v: string) => void;
}) {
  const isMC = question.type === "multiple_choice" && question.options.length > 0;
  return (
    <article className="card">
      <p style={{ fontSize: "0.8rem", opacity: 0.5, marginBottom: "0.25rem" }}>
        第 {index + 1} 题 · {isMC ? "单选" : "简答"}
        {question.knowledge_point ? ` · ${question.knowledge_point}` : ""}
      </p>
      <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>{question.question}</h2>
      {isMC ? (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {question.options.map((opt) => {
            const letter = opt[0];
            const selected = answer === letter;
            return (
              <li
                key={opt}
                onClick={() => onChange(letter)}
                style={{
                  padding: "0.4rem 0.6rem", borderRadius: "6px", marginBottom: "0.25rem",
                  cursor: "pointer",
                  border: selected ? "1.5px solid var(--color-primary, #2563eb)" : "1.5px solid transparent",
                  background: selected ? "var(--color-primary-bg, #eff6ff)" : "var(--bg-subtle, #f8f9fa)",
                  fontWeight: selected ? 600 : 400, transition: "all 0.1s",
                }}
              >
                {opt}
              </li>
            );
          })}
        </ul>
      ) : (
        <textarea
          placeholder="请输入你的答案…" value={answer}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid var(--border)", fontSize: "0.9rem", resize: "vertical", boxSizing: "border-box" }}
        />
      )}
    </article>
  );
}

// ── ResultCard ─────────────────────────────────────────────────────────────────

function ResultCard({ question, index, result }: { question: QuizQuestion; index: number; result: QuestionResult }) {
  const isMC = question.type === "multiple_choice";
  let badge: string; let badgeColor: string;
  if (result.requires_review) { badge = "📝 待核对"; badgeColor = "var(--color-warning, #b45309)"; }
  else if (result.is_correct) { badge = "✓ 正确"; badgeColor = "var(--color-success, #16a34a)"; }
  else { badge = "✗ 错误"; badgeColor = "var(--color-danger, #c0392b)"; }

  return (
    <article className="card" style={{ borderLeft: `3px solid ${badgeColor}` }}>
      <p style={{ fontSize: "0.8rem", opacity: 0.5, marginBottom: "0.25rem" }}>
        第 {index + 1} 题 · {isMC ? "单选" : "简答"}
        {question.knowledge_point ? ` · ${question.knowledge_point}` : ""}
      </p>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
        <h2 style={{ fontSize: "1rem", margin: 0, flex: 1 }}>{question.question}</h2>
        <span style={{ fontSize: "0.85rem", fontWeight: 600, color: badgeColor, marginLeft: "0.75rem", whiteSpace: "nowrap" }}>{badge}</span>
      </div>
      {isMC && question.options.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, marginBottom: "0.5rem" }}>
          {question.options.map((opt) => {
            const letter = opt[0];
            const isCorrect = letter === result.correct_answer[0];
            const isSelected = letter === result.user_answer[0];
            let bg = "transparent";
            if (isCorrect) bg = "var(--color-success-bg, #dcfce7)";
            else if (isSelected && !isCorrect) bg = "var(--color-danger-bg, #fee2e2)";
            return <li key={opt} style={{ padding: "0.3rem 0.5rem", borderRadius: "4px", marginBottom: "0.2rem", background: bg, fontSize: "0.9rem" }}>{opt}</li>;
          })}
        </ul>
      )}
      <div style={{ fontSize: "0.85rem", borderTop: "1px solid var(--border)", paddingTop: "0.4rem" }}>
        {result.requires_review && <p style={{ marginBottom: "0.25rem" }}><strong>你的回答：</strong>{result.user_answer || "（未作答）"}</p>}
        {(!isMC || !result.is_correct) && <p style={{ marginBottom: "0.25rem" }}><strong>正确答案：</strong>{result.correct_answer}</p>}
        {result.explanation && <p style={{ opacity: 0.8 }}><strong>解析：</strong>{result.explanation}</p>}
      </div>
    </article>
  );
}

// ── main page ──────────────────────────────────────────────────────────────────

export default function DocumentQuizPage() {
  const params = useParams<{ id: string }>();
  const documentId = params.id;

  const [quizList, setQuizList] = useState<QuizSummary[]>([]);
  const [quiz, setQuiz] = useState<QuizResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [attempt, setAttempt] = useState<QuizAttemptResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [listLoading, setListLoading] = useState(true);

  // Load quiz history on mount
  useEffect(() => {
    listQuizzes(documentId)
      .then((res) => setQuizList(res.quizzes))
      .catch(() => {})
      .finally(() => setListLoading(false));
  }, [documentId]);

  const answeredCount = quiz ? quiz.questions.filter((q) => (answers[q.id] ?? "").trim() !== "").length : 0;
  const allAnswered = quiz ? answeredCount === quiz.questions.length : false;
  const mcTotal = quiz ? quiz.questions.filter((q) => q.type === "multiple_choice").length : 0;
  const scorePercent = attempt && attempt.total > 0 ? Math.round((attempt.score / attempt.total) * 100) : null;

  async function handleGenerate() {
    setIsLoading(true);
    setError(null);
    setAttempt(null);
    setAnswers({});
    setQuiz(null);
    try {
      const newQuiz = await createQuiz(documentId);
      setQuiz(newQuiz);
      setQuizList((prev) => [
        { id: newQuiz.id, title: newQuiz.title, difficulty: newQuiz.difficulty, question_count: newQuiz.questions.length, created_at: new Date().toISOString() },
        ...prev,
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleLoadPastQuiz(quizId: string) {
    setIsLoading(true);
    setError(null);
    setAttempt(null);
    setAnswers({});
    try {
      setQuiz(await getQuizById(documentId, quizId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit() {
    if (!quiz) return;
    setIsSubmitting(true);
    setError(null);
    try {
      setAttempt(await submitQuizAttempt(documentId, quiz.id, answers));
    } catch (err) {
      setError(err instanceof Error ? err.message : "提交失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleRetry() {
    setAttempt(null);
    setAnswers({});
  }

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <h1>Quiz</h1>
          <p>
            {attempt
              ? `得分 ${attempt.score}/${attempt.total}${scorePercent !== null ? `（${scorePercent}%）` : ""}${attempt.total < (quiz?.questions.length ?? 0) ? " · 简答题请自行核对" : ""}`
              : quiz
              ? `${quiz.title} · ${quiz.questions.length} 题 · 已答 ${answeredCount}/${quiz.questions.length}`
              : "基于文档内容生成自测题目。"}
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          {attempt && <button className="button" style={{ opacity: 0.7 }} onClick={handleRetry} type="button">再做一次</button>}
          <button className="button" disabled={isLoading} onClick={handleGenerate} type="button">
            {isLoading ? "生成中…" : "生成新 Quiz"}
          </button>
        </div>
      </header>

      {error && <div className="empty" style={{ color: "var(--color-danger, #c0392b)" }}>{error}</div>}

      {/* Past quizzes list — shown when no quiz is active */}
      {!quiz && !isLoading && (
        <section className="panel">
          <h2 style={{ fontSize: "0.9rem", opacity: 0.6, fontWeight: 600, marginBottom: "0.75rem" }}>
            {listLoading ? "加载历史…" : quizList.length > 0 ? `历史 Quiz（${quizList.length} 份）` : "还没有 Quiz 记录，点击「生成新 Quiz」开始。"}
          </h2>
          {quizList.map((q) => (
            <article
              key={q.id}
              className="card"
              onClick={() => handleLoadPastQuiz(q.id)}
              style={{ marginBottom: "0.5rem", cursor: "pointer" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 500 }}>{q.title}</span>
                <span style={{ fontSize: "0.8rem", opacity: 0.55 }}>
                  {q.question_count} 题 · {new Date(q.created_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
            </article>
          ))}
        </section>
      )}

      {/* Score banner */}
      {attempt && (
        <div className="panel" style={{
          textAlign: "center", padding: "1.25rem",
          background: scorePercent !== null && scorePercent >= 60 ? "var(--color-success-bg, #dcfce7)" : "var(--color-danger-bg, #fee2e2)",
        }}>
          <p style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0 }}>{attempt.score} / {attempt.total}</p>
          {scorePercent !== null && (
            <p style={{ opacity: 0.7, margin: "0.25rem 0 0" }}>
              客观题正确率 {scorePercent}%{mcTotal < (quiz?.questions.length ?? 0) ? "（简答题需自行对照答案）" : ""}
            </p>
          )}
        </div>
      )}

      <section className="list">
        {quiz && quiz.questions.length > 0 ? (
          attempt ? (
            quiz.questions.map((q, i) => {
              const result = attempt.results.find((r) => r.question_id === q.id);
              if (!result) return null;
              return <ResultCard index={i} key={q.id} question={q} result={result} />;
            })
          ) : (
            <>
              {quiz.questions.map((q, i) => (
                <AnswerCard
                  answer={answers[q.id] ?? ""} index={i} key={q.id}
                  onChange={(val) => setAnswers((prev) => ({ ...prev, [q.id]: val }))}
                  question={q}
                />
              ))}
              <div style={{ padding: "0.5rem 0" }}>
                <button
                  className="button" disabled={!allAnswered || isSubmitting}
                  onClick={handleSubmit} type="button" style={{ width: "100%" }}
                >
                  {isSubmitting ? "批改中…" : allAnswered ? "提交答案" : `还有 ${quiz.questions.length - answeredCount} 题未作答`}
                </button>
              </div>
            </>
          )
        ) : isLoading ? (
          <div className="empty">生成中，请稍候…</div>
        ) : null}
      </section>
    </div>
  );
}
