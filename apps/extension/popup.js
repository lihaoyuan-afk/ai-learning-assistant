const DEFAULT_API = "https://ai-learning-api-189424783668.us-central1.run.app";
const POLL_MS = 2500;
const MAX_POLLS = 60; // 2.5 min max

let currentDocId = null;
let pollTimer = null;
let pollCount = 0;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const urlBox      = document.getElementById("urlBox");
const importBtn   = document.getElementById("importBtn");
const statusBox   = document.getElementById("statusBox");
const openBtn     = document.getElementById("openBtn");
const toggleBtn   = document.getElementById("toggleSettings");
const settingsPanel = document.getElementById("settingsPanel");
const apiUrlInput = document.getElementById("apiUrl");
const apiPassInput = document.getElementById("apiPassword");
const saveBtn     = document.getElementById("saveSettings");

// ── Init ──────────────────────────────────────────────────────────────────────
chrome.storage.sync.get(["apiUrl", "apiPassword"], (stored) => {
  apiUrlInput.value  = stored.apiUrl      || DEFAULT_API;
  apiPassInput.value = stored.apiPassword || "";
});

chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  const url = tab?.url || "";
  if (!url || url.startsWith("chrome://") || url.startsWith("about:")) {
    urlBox.textContent = "不支持此页面";
    urlBox.classList.add("no-url");
    return;
  }
  urlBox.textContent = url;
  importBtn.disabled = false;
  importBtn.addEventListener("click", () => startImport(url));
});

// ── Settings ──────────────────────────────────────────────────────────────────
toggleBtn.addEventListener("click", () => {
  settingsPanel.classList.toggle("show");
});

saveBtn.addEventListener("click", () => {
  chrome.storage.sync.set({
    apiUrl: apiUrlInput.value.trim() || DEFAULT_API,
    apiPassword: apiPassInput.value.trim(),
  }, () => {
    saveBtn.textContent = "已保存 ✓";
    setTimeout(() => { saveBtn.textContent = "保存"; }, 1500);
    settingsPanel.classList.remove("show");
  });
});

// ── Import flow ───────────────────────────────────────────────────────────────
function startImport(url) {
  importBtn.disabled = true;
  openBtn.style.display = "none";
  showStatus("info", "正在导入…", "连接知识库中…");

  chrome.storage.sync.get(["apiUrl", "apiPassword"], (stored) => {
    const base    = (stored.apiUrl || DEFAULT_API).replace(/\/$/, "");
    const password = stored.apiPassword || "";
    const headers  = { "Content-Type": "application/json" };
    if (password) headers["Authorization"] = `Bearer ${password}`;

    fetch(`${base}/documents/import-url`, {
      method: "POST",
      headers,
      body: JSON.stringify({ url }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((b) => Promise.reject(b?.detail || `HTTP ${r.status}`));
        return r.json();
      })
      .then((data) => {
        currentDocId = data.document?.id;
        if (!currentDocId) throw new Error("未返回文档 ID");
        showStatus("info", "解析中…", "正在提取内容并生成向量索引，请稍候…");
        pollCount = 0;
        pollTimer = setInterval(() => pollStatus(base, headers), POLL_MS);
      })
      .catch((err) => {
        showStatus("error", "导入失败", String(err));
        importBtn.disabled = false;
      });
  });
}

function pollStatus(base, headers) {
  pollCount++;
  if (pollCount > MAX_POLLS) {
    clearInterval(pollTimer);
    showStatus("error", "超时", "处理时间过长，请前往网站查看文档状态。");
    importBtn.disabled = false;
    return;
  }

  fetch(`${base}/documents/${currentDocId}`, { headers })
    .then((r) => r.json())
    .then((doc) => {
      if (doc.status === "ready") {
        clearInterval(pollTimer);
        showStatus("success", "导入成功 ✓", `「${doc.title}」已就绪，可以开始问答。`);
        openBtn.style.display = "block";
        openBtn.onclick = () => {
          chrome.storage.sync.get(["apiUrl"], (stored) => {
            const frontendBase = (stored.apiUrl || DEFAULT_API).includes("run.app")
              ? "https://web-lac-theta-18.vercel.app"
              : "http://localhost:3000";
            chrome.tabs.create({ url: `${frontendBase}/documents/${currentDocId}` });
          });
        };
      } else if (doc.status === "failed") {
        clearInterval(pollTimer);
        showStatus("error", "解析失败", doc.error_message || "文件可能无法访问或内容为空。");
        importBtn.disabled = false;
      }
      // uploaded/processing → keep polling
    })
    .catch(() => { /* network hiccup, retry */ });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function showStatus(type, title, body) {
  statusBox.className = `status show ${type}`;
  statusBox.innerHTML = `<div class="status-title">${escape(title)}</div>${escape(body)}`;
}

function escape(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
