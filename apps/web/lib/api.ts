import type {
  ChatResponse,
  DocumentIngestResponse,
  DocumentListResponse,
  DocumentRead,
  ErrorNotebookResponse,
  KnowledgeGraph,
  MasteryResponse,
  QuizAttemptRequest,
  QuizAttemptResponse,
  QuizListResponse,
  QuizResponse,
  ReviewResponse,
  SummaryResponse,
  StudyPlan,
  TokenResponse,
  UserRead,
  WeeklyReport,
} from "@/lib/types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ── Demo auth token (stored in localStorage) ──────────────────────────────────
export function getDemoToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("demo_token");
}
export function setDemoToken(token: string): void {
  localStorage.setItem("demo_token", token);
}
export function clearDemoToken(): void {
  localStorage.removeItem("demo_token");
}
function authHeaders(): Record<string, string> {
  const token = getDemoToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    ...init,
    headers: { ...authHeaders(), ...(init?.headers as Record<string, string> ?? {}) },
  });

  if (response.status === 401) {
    clearDemoToken();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("请先登录");
  }

  if (!response.ok) {
    let detail = `请求失败（${response.status}）`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // keep default message
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function loginUser(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `登录失败（${res.status}）`);
  }
  return res.json() as Promise<TokenResponse>;
}

export async function registerUser(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `注册失败（${res.status}）`);
  }
  return res.json() as Promise<TokenResponse>;
}

export async function getMe(): Promise<UserRead> {
  return request<UserRead>("/auth/me");
}

export async function getDocuments(): Promise<DocumentListResponse> {
  return request<DocumentListResponse>("/documents");
}

export async function getDocument(documentId: string): Promise<DocumentRead> {
  return request<DocumentRead>(`/documents/${documentId}`);
}

export async function uploadDocument(file: File): Promise<DocumentIngestResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<DocumentIngestResponse>("/documents/upload", {
    method: "POST",
    body: formData
  });
}

export async function askDocument(documentId: string, question: string): Promise<ChatResponse> {
  return request<ChatResponse>(`/documents/${documentId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question })
  });
}

export async function summarizeDocument(documentId: string): Promise<SummaryResponse> {
  return request<SummaryResponse>(`/documents/${documentId}/summary`, {
    method: "POST"
  });
}

export async function listQuizzes(documentId: string): Promise<QuizListResponse> {
  return request<QuizListResponse>(`/documents/${documentId}/quiz`);
}

export async function getQuizById(documentId: string, quizId: string): Promise<QuizResponse> {
  return request<QuizResponse>(`/documents/${documentId}/quiz/${quizId}`);
}

export async function createQuiz(documentId: string, numQuestions = 6): Promise<QuizResponse> {
  return request<QuizResponse>(`/documents/${documentId}/quiz`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ num_questions: numQuestions })
  });
}

export async function generateStudyPlan(): Promise<StudyPlan> {
  return request<StudyPlan>("/profile/study-plan", { method: "POST" });
}

export async function submitQuizAttempt(
  documentId: string,
  quizId: string,
  answers: QuizAttemptRequest["answers"]
): Promise<QuizAttemptResponse> {
  return request<QuizAttemptResponse>(
    `/documents/${documentId}/quiz/${quizId}/attempt`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers })
    }
  );
}

export async function getMastery(): Promise<MasteryResponse> {
  return request<MasteryResponse>("/profile/mastery");
}

export async function getReviewToday(): Promise<ReviewResponse> {
  return request<ReviewResponse>("/profile/review/today");
}

export async function deleteDocument(documentId: string): Promise<void> {
  await request<{ message: string }>(`/documents/${documentId}`, {
    method: "DELETE",
  });
}

export async function importDocumentFromUrl(url: string): Promise<DocumentIngestResponse> {
  return request<DocumentIngestResponse>("/documents/import-url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

export async function getErrorNotebook(): Promise<ErrorNotebookResponse> {
  return request<ErrorNotebookResponse>("/profile/error-notebook");
}

export async function scheduleReview(knowledge_point: string): Promise<void> {
  await request<{ message: string }>("/profile/mastery/schedule-review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ knowledge_point }),
  });
}

export async function getWeeklyReport(days = 7): Promise<WeeklyReport> {
  return request<WeeklyReport>(`/profile/weekly-report?days=${days}`);
}

export async function getKnowledgeGraph(documentId: string): Promise<KnowledgeGraph> {
  return request<KnowledgeGraph>(`/documents/${documentId}/knowledge-graph`);
}

export async function* streamSocratic(
  documentId: string,
  payload: { user_answer?: string; history?: HistoryMessage[]; topic?: string }
): AsyncGenerator<StreamEvent> {
  yield* _streamSse(
    `${API_BASE_URL}/documents/${documentId}/chat/socratic/stream`,
    payload
  );
}

export type StreamEvent =
  | { type: "sources"; sources: import("@/lib/types").SourceChunk[] }
  | { type: "token"; content: string }
  | { type: "error"; detail: string }
  | { type: "cached" }
  | { type: "done" };

export type HistoryMessage = { role: "user" | "assistant"; content: string };

async function* _streamSse(url: string, body: object): AsyncGenerator<StreamEvent> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let detail = `请求失败（${response.status}）`;
    try {
      const b = await response.json();
      if (b?.detail) detail = b.detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const json = line.slice(5).trim();
      try {
        yield JSON.parse(json) as StreamEvent;
      } catch { /* malformed event */ }
    }
  }
}

export async function* streamChat(
  documentId: string,
  question: string,
  history: HistoryMessage[] = []
): AsyncGenerator<StreamEvent> {
  yield* _streamSse(
    `${API_BASE_URL}/documents/${documentId}/chat/stream`,
    { question, history }
  );
}

export async function* streamSummary(documentId: string): AsyncGenerator<StreamEvent> {
  yield* _streamSse(
    `${API_BASE_URL}/documents/${documentId}/summary/stream`,
    {}
  );
}

export async function* streamGlobalSearch(
  question: string,
  history: HistoryMessage[] = []
): AsyncGenerator<StreamEvent> {
  yield* _streamSse(`${API_BASE_URL}/search/stream`, { question, history });
}

