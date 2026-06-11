import Link from "next/link";
import { StatusPill } from "@/components/status-pill";

const features = [
  {
    href: "/documents/upload",
    title: "上传 PDF",
    body: "支持最大 50 MB 的 PDF，上传后自动解析、切片并向量化。",
  },
  {
    href: "/documents",
    title: "资料问答",
    body: "基于向量检索回答问题，回答附带来源页码。",
  },
  {
    href: "/documents",
    title: "总结 & Quiz",
    body: "一键生成结构化总结和自测题目，答题后自动更新掌握度。",
  },
  {
    href: "/review",
    title: "复习计划",
    body: "根据掌握度自动调度复习时间：未掌握 2 天、学习中 5 天、已掌握 14 天。",
  },
  {
    href: "/profile",
    title: "学习画像",
    body: "追踪所有知识点的答题记录与掌握度趋势。",
  },
];

export default function HomePage() {
  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <StatusPill>Phase 1 MVP</StatusPill>
          <h1>AI 学习助手工作台</h1>
          <p>上传 PDF → 问答 / 总结 / Quiz → 掌握度追踪 → 复习计划</p>
        </div>
        <div className="actions">
          <Link className="button" href="/documents/upload">
            上传 PDF
          </Link>
          <Link className="button secondary" href="/documents">
            查看资料
          </Link>
        </div>
      </header>

      <section className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))" }}>
        {features.map((item) => (
          <Link className="card" href={item.href} key={item.title} style={{ cursor: "pointer" }}>
            <h2>{item.title}</h2>
            <p>{item.body}</p>
          </Link>
        ))}
      </section>

      <section className="panel">
        <h2>快速开始</h2>
        <ol style={{ margin: "0.5rem 0 0", paddingLeft: "1.4rem", lineHeight: 2, color: "var(--muted)" }}>
          <li>确认 Ollama 已启动（<code>ollama serve</code>）并下载了 <code>deepseek-r1:1.5b</code> 和 <code>nomic-embed-text</code></li>
          <li>启动后端：<code>cd apps/api && .venv/Scripts/python.exe -m uvicorn app.main:app --reload</code></li>
          <li>上传一份 PDF，等待状态变为 <strong>ready</strong></li>
          <li>点击文档卡片，进入问答 / 总结 / Quiz</li>
        </ol>
      </section>
    </div>
  );
}
