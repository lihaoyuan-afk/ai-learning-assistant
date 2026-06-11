import type { ReactNode } from "react";

type Variant = "default" | "success" | "warning" | "danger";

function variantForStatus(status: string): Variant {
  if (status === "ready" || status === "就绪") return "success";
  if (status === "failed" || status === "解析失败") return "danger";
  if (status === "processing" || status === "解析中…") return "warning";
  return "default";
}

const VARIANT_STYLE: Record<Variant, React.CSSProperties> = {
  default: {},
  success: { background: "var(--color-success-bg, #dcfce7)", color: "var(--color-success, #16a34a)" },
  warning: { background: "#fef3c7", color: "#92400e" },
  danger: { background: "var(--color-danger-bg, #fee2e2)", color: "var(--color-danger, #c0392b)" },
};

export function StatusPill({ children }: { children: ReactNode }) {
  const text = typeof children === "string" ? children : "";
  const style = VARIANT_STYLE[variantForStatus(text)];
  return (
    <span className="status" style={style}>
      {children}
    </span>
  );
}
