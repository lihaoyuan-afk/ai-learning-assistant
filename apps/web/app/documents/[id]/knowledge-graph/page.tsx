"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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

type Pos = { x: number; y: number };
type PosMap = Record<string, Pos>;

const W = 900;
const H = 560;

function circleLayout(nodes: KnowledgeNode[]): PosMap {
  const positions: PosMap = {};
  const count = nodes.length;
  if (count === 0) return positions;
  nodes.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / count - Math.PI / 2;
    const rx = (W / 2 - 90) * (count > 6 ? 0.85 : 0.65);
    const ry = (H / 2 - 70) * (count > 6 ? 0.85 : 0.65);
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
  const [positions, setPositions] = useState<PosMap>({});

  // Drag state
  const draggingRef = useRef<string | null>(null);
  const dragOffsetRef = useRef<Pos>({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);

  // Zoom / pan state
  const [viewBox, setViewBox] = useState({ x: 0, y: 0, w: W, h: H });
  const isPanningRef = useRef(false);
  const panStartRef = useRef<Pos>({ x: 0, y: 0 });
  const panOriginRef = useRef<Pos>({ x: 0, y: 0 });

  useEffect(() => {
    getDocument(id).then(setDoc).catch(() => {});
  }, [id]);

  useEffect(() => {
    if (graph) setPositions(circleLayout(graph.nodes));
  }, [graph]);

  async function fetchGraph() {
    setLoading(true);
    setError(null);
    setGraph(null);
    setPositions({});
    setSelected(null);
    try {
      setGraph(await getKnowledgeGraph(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setLoading(false);
    }
  }

  // Convert client coords to SVG coords respecting viewBox
  function clientToSvg(clientX: number, clientY: number): Pos {
    const svg = svgRef.current;
    if (!svg) return { x: clientX, y: clientY };
    const rect = svg.getBoundingClientRect();
    const scaleX = viewBox.w / rect.width;
    const scaleY = viewBox.h / rect.height;
    return {
      x: (clientX - rect.left) * scaleX + viewBox.x,
      y: (clientY - rect.top) * scaleY + viewBox.y,
    };
  }

  const handleNodePointerDown = useCallback(
    (e: React.PointerEvent<SVGGElement>, nodeId: string) => {
      e.stopPropagation();
      draggingRef.current = nodeId;
      const svgPt = clientToSvg(e.clientX, e.clientY);
      const pos = positions[nodeId] ?? { x: 0, y: 0 };
      dragOffsetRef.current = { x: svgPt.x - pos.x, y: svgPt.y - pos.y };
      (e.currentTarget as SVGGElement).setPointerCapture(e.pointerId);
    },
    [positions, viewBox]
  );

  const handleNodePointerMove = useCallback(
    (e: React.PointerEvent<SVGGElement>) => {
      const nodeId = draggingRef.current;
      if (!nodeId) return;
      const svgPt = clientToSvg(e.clientX, e.clientY);
      setPositions((prev) => ({
        ...prev,
        [nodeId]: {
          x: svgPt.x - dragOffsetRef.current.x,
          y: svgPt.y - dragOffsetRef.current.y,
        },
      }));
    },
    [viewBox]
  );

  const handleNodePointerUp = useCallback(() => {
    draggingRef.current = null;
  }, []);

  // Pan: background pointer events
  function handleSvgPointerDown(e: React.PointerEvent<SVGSVGElement>) {
    if (draggingRef.current) return;
    isPanningRef.current = true;
    panStartRef.current = { x: e.clientX, y: e.clientY };
    panOriginRef.current = { x: viewBox.x, y: viewBox.y };
    (e.currentTarget as SVGSVGElement).setPointerCapture(e.pointerId);
  }

  function handleSvgPointerMove(e: React.PointerEvent<SVGSVGElement>) {
    if (!isPanningRef.current || draggingRef.current) return;
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const scaleX = viewBox.w / rect.width;
    const scaleY = viewBox.h / rect.height;
    const dx = (e.clientX - panStartRef.current.x) * scaleX;
    const dy = (e.clientY - panStartRef.current.y) * scaleY;
    setViewBox((vb) => ({ ...vb, x: panOriginRef.current.x - dx, y: panOriginRef.current.y - dy }));
  }

  function handleSvgPointerUp() {
    isPanningRef.current = false;
  }

  function handleWheel(e: React.WheelEvent<SVGSVGElement>) {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 1.1 : 0.9;
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const cx = ((e.clientX - rect.left) / rect.width) * viewBox.w + viewBox.x;
    const cy = ((e.clientY - rect.top) / rect.height) * viewBox.h + viewBox.y;
    setViewBox((vb) => ({
      x: cx - (cx - vb.x) * factor,
      y: cy - (cy - vb.y) * factor,
      w: vb.w * factor,
      h: vb.h * factor,
    }));
  }

  function resetView() {
    setViewBox({ x: 0, y: 0, w: W, h: H });
    if (graph) setPositions(circleLayout(graph.nodes));
  }

  const selectedEdges = selected
    ? (graph?.edges.filter((e) => e.source === selected || e.target === selected) ?? [])
    : [];

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-title">
          <h1>知识图谱</h1>
          <p style={{ opacity: 0.65 }}>{doc?.title} · 拖拽节点 / 滚轮缩放 / 拖拽背景平移</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {graph && (
            <button className="button secondary" onClick={resetView} type="button">
              重置视图
            </button>
          )}
          <button className="button" disabled={loading} onClick={fetchGraph} type="button">
            {loading ? "生成中…" : graph ? "重新生成" : "生成知识图谱"}
          </button>
          <Link className="button secondary" href={`/documents/${id}`}>返回文档</Link>
        </div>
      </header>

      {error && (
        <div className="empty" style={{ color: "var(--color-danger, #c0392b)" }}>{error}</div>
      )}
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
            viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
            style={{ width: "100%", height: "auto", background: "var(--bg, #f8fafc)", cursor: isPanningRef.current ? "grabbing" : "grab", touchAction: "none" }}
            onPointerDown={handleSvgPointerDown}
            onPointerMove={handleSvgPointerMove}
            onPointerUp={handleSvgPointerUp}
            onWheel={handleWheel}
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
              const isHl = selectedEdges.some((e) => e.source === edge.source && e.target === edge.target);
              const mx = (src.x + tgt.x) / 2;
              const my = (src.y + tgt.y) / 2;
              return (
                <g key={i}>
                  <line
                    x1={src.x} y1={src.y} x2={tgt.x} y2={tgt.y}
                    stroke={isHl ? "#3b82f6" : "#cbd5e1"}
                    strokeWidth={isHl ? 2 : 1.2}
                    markerEnd="url(#arrowhead)"
                    strokeOpacity={isHl ? 1 : 0.6}
                  />
                  <text x={mx} y={my - 4} textAnchor="middle" fontSize="10" fill={isHl ? "#2563eb" : "#64748b"} fontWeight={isHl ? 600 : 400}>
                    {edge.label}
                  </text>
                </g>
              );
            })}

            {/* Nodes (draggable) */}
            {graph.nodes.map((node) => {
              const pos = positions[node.id];
              if (!pos) return null;
              const color = NODE_COLORS[node.type] ?? "#6b7280";
              const isSel = node.id === selected;
              return (
                <g
                  key={node.id}
                  style={{ cursor: "move" }}
                  onClick={() => setSelected(isSel ? null : node.id)}
                  onPointerDown={(e) => handleNodePointerDown(e, node.id)}
                  onPointerMove={handleNodePointerMove}
                  onPointerUp={handleNodePointerUp}
                >
                  <circle
                    cx={pos.x} cy={pos.y} r={isSel ? 36 : 28}
                    fill={color} fillOpacity={isSel ? 1 : 0.85}
                    stroke={isSel ? "#1e3a8a" : "white"} strokeWidth={isSel ? 3 : 2}
                  />
                  <text
                    x={pos.x} y={pos.y + 4}
                    textAnchor="middle" fontSize="11" fill="white" fontWeight={600}
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
              <span key={type} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: color, display: "inline-block" }} />
                {type}
              </span>
            ))}
            <span style={{ opacity: 0.55, marginLeft: "auto" }}>点击节点高亮关联边 · 拖拽重排</span>
          </div>
        </section>
      )}

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
