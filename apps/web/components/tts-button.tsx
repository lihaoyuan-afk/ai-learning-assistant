"use client";

import { useRef, useState } from "react";
import { API_BASE_URL, getDemoToken } from "@/lib/api";

type Props = {
  text: string;
  className?: string;
};

export function TTSButton({ text, className }: Props) {
  const [state, setState] = useState<"idle" | "loading" | "playing" | "error">("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);

  async function handleClick() {
    if (state === "playing") {
      audioRef.current?.pause();
      setState("idle");
      return;
    }
    if (state === "loading") return;

    setState("loading");
    const token = getDemoToken();
    try {
      const res = await fetch(`${API_BASE_URL}/tts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ text }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `TTS 失败（${res.status}）`);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onended = () => {
        setState("idle");
        URL.revokeObjectURL(url);
      };
      audio.onerror = () => {
        setState("error");
        URL.revokeObjectURL(url);
      };

      await audio.play();
      setState("playing");
    } catch (err) {
      setState("error");
      setTimeout(() => setState("idle"), 3000);
      console.warn("TTS error:", err instanceof Error ? err.message : err);
    }
  }

  const label =
    state === "loading" ? "加载中…"
    : state === "playing" ? "停止朗读"
    : state === "error" ? "朗读不可用"
    : "朗读";

  return (
    <button
      onClick={handleClick}
      disabled={state === "loading"}
      title={label}
      className={className}
      style={{
        background: "none",
        border: `1px solid ${state === "error" ? "#e74c3c" : state === "playing" ? "#2563eb" : "var(--border, #ddd)"}`,
        borderRadius: "6px",
        cursor: state === "loading" ? "wait" : "pointer",
        color: state === "error" ? "#e74c3c" : state === "playing" ? "#2563eb" : "var(--text-muted, #888)",
        fontSize: "0.75rem",
        padding: "0.25rem 0.6rem",
        lineHeight: 1.5,
        display: "inline-flex",
        alignItems: "center",
        gap: "0.3rem",
        transition: "all 0.15s",
      }}
    >
      {state === "playing" ? "⏹" : state === "loading" ? "⏳" : "🔊"} {label}
    </button>
  );
}
