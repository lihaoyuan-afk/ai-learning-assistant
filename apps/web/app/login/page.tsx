"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL, clearDemoToken, getDemoToken, loginUser, registerUser, setDemoToken } from "@/lib/api";

type Tab = "login" | "register" | "demo";

export default function LoginPage() {
  const [tab, setTab] = useState<Tab>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [demoPassword, setDemoPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (getDemoToken()) router.replace("/");
  }, [router]);

  function resetForm() {
    setError("");
    setEmail("");
    setPassword("");
    setDemoPassword("");
  }

  async function handleAccountSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) return;
    setLoading(true);
    setError("");
    try {
      const fn = tab === "register" ? registerUser : loginUser;
      const { access_token } = await fn(email, password);
      setDemoToken(access_token);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败，请重试");
    } finally {
      setLoading(false);
    }
  }

  async function handleDemoSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!demoPassword) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/documents`, {
        headers: { Authorization: `Bearer ${demoPassword}` },
      });
      if (res.ok) {
        setDemoToken(demoPassword);
        router.replace("/");
      } else if (res.status === 401) {
        setError("密码错误，请重试");
        clearDemoToken();
      } else {
        setError(`登录失败（${res.status}）`);
      }
    } catch {
      setError("无法连接到服务器，请检查网络");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 w-full max-w-sm">
        <h1 className="text-xl font-semibold text-gray-900 mb-1">AI 学习助手</h1>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 mt-4 bg-gray-100 rounded-lg p-1">
          {(["login", "register", "demo"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); resetForm(); }}
              className={`flex-1 py-1.5 text-sm rounded-md transition-colors ${
                tab === t
                  ? "bg-white shadow-sm font-medium text-gray-900"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {t === "login" ? "登录" : t === "register" ? "注册" : "访问密码"}
            </button>
          ))}
        </div>

        {tab !== "demo" ? (
          <form onSubmit={handleAccountSubmit} className="space-y-3">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="邮箱"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={tab === "register" ? "密码（至少 6 位）" : "密码"}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {error && <p className="text-sm text-red-500">{error}</p>}
            <button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {loading ? "请稍候…" : tab === "register" ? "注册并登录" : "登录"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleDemoSubmit} className="space-y-3">
            <p className="text-sm text-gray-500">使用管理员设置的访问密码进入演示模式。</p>
            <input
              type="password"
              value={demoPassword}
              onChange={(e) => setDemoPassword(e.target.value)}
              placeholder="访问密码"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
            {error && <p className="text-sm text-red-500">{error}</p>}
            <button
              type="submit"
              disabled={loading || !demoPassword}
              className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {loading ? "验证中…" : "进入"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
