"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getDocument, getKnowledgeGraph } from "@/lib/api";
import type { DocumentRead, KnowledgeGraph, KnowledgeNode } from "@/lib/types";

const NODE_COLORS: Record<string, string> = {
  concept: "#3b82f6",
  term: "#8b5cf6",
  method: "#10b981",
  theory: "#f59e0b",
};

const W = 800;
const H = 500;

function layoutNodes(nodes: KnowledgeNode[]): Record<string, { x: number; y: number }> {
  const positions: Record<string, { x: number; y: number }> = {};
  const count = nodes.length;
  if (count === 0) return positions;
  nodes.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / count - Math.PI / 2;
    const rx = (W / 2 - 80) * (count > 6 ? 0.85 : 0.65);
    const ry = (H / 2 - 60) * (count > 6 ? 0.85 : 0.65);
    positions[n.id] = {
      x: W / 2 + rx * Math.cos(angle),
      y: H / 2 + ry * Math.sin(angle),
    };
  });
  return positions;
}

export default function KnowledgeGraphPage() {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<DocumentRead | null>(null);
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => { getDocument(id).then(setDoc).catch(() => {}); }, [id]);

  async function fetchGraph() {
    setLoading(true); setError(null); setGraph(null);
    try {
      setGraph(await getKnowledgeGraph(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setLoading(false);
    }
  }

  const positions = graph ? layoutNodes(graph.nodes) : {};
  const selectedEdges = selected
    ? graph?.edges.filter((e) => e.source === selected || e.target === selected) ?? []
    : [];

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <h1>知识图谱</h1>
          <p style={{ opacity: 0.65 }}>{doc?.title}</p>
        </div>
        <div className="actions">
          <button className="button" disabled={loading} onClick={fetchGraph}>
            {loading ? "生成中…" : graph ? "重新生成" : "生成知识图谱"}
          </button>
          <Link className="button secondary" href={`/documents/${id}`}>返回文档</Link>
        </div>
      </header>

      {error && <div className="empty" style={{ color: "var(--color-danger, #c0392b)" }}>{error}</div>}

      {!graph && !loading && (
        <div className="empty">
          <p>点击「生成知识图谱」，AI 将分析文档内容，提取核心概念和它们之间的关系。</p>
        </div>
      )}

      {loading && <div className="empty">正在分析文档，提取概念关系…</div>}

      {graph && graph.nodes.length === 0 && (
        <div className="empty">未能提取到知识节点，请尝试重新生成。</div>
      )}

      {graph && graph.nodes.length > 0 && (
        <section className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <svg
            ref={svgRef}
            viewBox={`0 0 ${W} ${H}`}
            style={{ width: "100%", height: "auto", background: "var(--bg, #f8fafc)" }}
          >
            <defs>
              <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#94a3b8" />
              </marker>
            </defs>

            {/* Edges */}
            {graph.edges.map((edge, i) => {
              const src = positions[edge.source];
              const tgt = positions[edge.target];
              if (!src || !tgt) return null;
              const isHighlighted = selectedEdges.some(
                (e) => e.source === edge.source && e.target === edge.target
              );
              const mx = (src.x + tgt.x) / 2;
              const my = (src.y + tgt.y) / 2;
              return (
                <g key={i}>
                  <line
                    x1={src.x} y1={src.y} x2={tgt.x} y2={tgt.y}
                    stroke={isHighlighted ? "#3b82f6" : "#cbd5e1"}
                    strokeWidth={isHighlighted ? 2 : 1.2}
                    markerEnd="url(#arrowhead)"
                    strokeOpacity={isHighlighted ? 1 : 0.6}
                  />
                  <text
                    x={mx} y={my - 4}
                    textAnchor="middle"
                    fontSize="10"
                    fill={isHighlighted ? "#2563eb" : "#64748b"}
                    fontWeight={isHighlighted ? 600 : 400}
                  >
                    {edge.label}
                  </text>
                </g>
              );
            })}

            {/* Nodes */}
            {graph.nodes.map((node) => {
              const pos = positions[node.id];
              if (!pos) return null;
              const color = NODE_COLORS[node.type] ?? "#6b7280";
              const isSelected = node.id === selected;
              return (
                <g
                  key={node.id}
                  style={{ cursor: "pointer" }}
                  onClick={() => setSelected(isSelected ? null : node.id)}
                >
                  <circle
                    cx={pos.x} cy={pos.y} r={isSelected ? 34 : 28}
                    fill={color}
                    fillOpacity={isSelected ? 1 : 0.8}
                    stroke={isSelected ? "#1e3a8a" : "white"}
                    strokeWidth={isSelected ? 3 : 2}
                  />
                  <text
                    x={pos.x} y={pos.y + 4}
                    textAnchor="middle"
                    fontSize="11"
                    fill="white"
                    fontWeight={600}
                    style={{ userSelect: "none", pointerEvents: "none" }}
                  >
                    {node.label.length > 6 ? node.label.slice(0, 6) + "…" : node.label}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Legend */}
          <div style={{ padding: "0.75rem 1rem", borderTop: "1px solid var(--border, #e5e7eb)", display: "flex", gap: "1rem", flexWrap: "wrap", fontSize: "0.8rem" }}>
            {Object.entries(NODE_COLORS).map(([type, color]) => (
              <span key={type} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: color, display: "inline-block" }} />
                {type}
              </span>
            ))}
            <span style={{ opacity: 0.55, marginLeft: "auto" }}>点击节点高亮相关边</span>
          </div>
        </section>
      )}

      {/* Selected node info */}
      {selected && graph && (
        <section className="panel" style={{ marginTop: "0.75rem" }}>
          <p style={{ fontWeight: 600, marginBottom: "0.4rem" }}>
            {graph.nodes.find((n) => n.id === selected)?.label}
          </p>
          {selectedEdges.length === 0 && <p style={{ opacity: 0.55, fontSize: "0.85rem" }}>该节点无关联边</p>}
          {selectedEdges.map((e, i) => (
            <p key={i} style={{ fontSize: "0.85rem", margin: "0.2rem 0", opacity: 0.75 }}>
              {graph.nodes.find((n) => n.id === e.source)?.label}
              <span style={{ margin: "0 0.4rem", opacity: 0.5 }}>—{e.label}→</span>
              {graph.nodes.find((n) => n.id === e.target)?.label}
            </p>
          ))}
        </section>
      )}
    </div>
  );
}
