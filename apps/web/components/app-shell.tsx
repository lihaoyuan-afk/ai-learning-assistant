"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const navItems = [
  { href: "/", label: "工作台" },
  { href: "/documents", label: "资料" },
  { href: "/documents/upload", label: "上传" },
  { href: "/search", label: "全局搜索" },
  { href: "/review", label: "复习" },
  { href: "/profile", label: "画像" },
];

function isActive(href: string, pathname: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(href + "/");
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <strong>AgentLearn</strong>
          <span>Learning OS</span>
        </div>
        <nav className="nav" aria-label="主导航">
          {navItems.map((item) => (
            <Link
              href={item.href}
              key={item.href}
              aria-current={isActive(item.href, pathname) ? "page" : undefined}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
