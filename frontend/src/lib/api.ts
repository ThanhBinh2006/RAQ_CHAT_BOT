const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Helper to get auth headers ──────────────────────────────
function getHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = typeof window !== "undefined" ? localStorage.getItem("raq_token") : null;
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Inject API keys and model config into headers for CopilotKit/LLM
  if (typeof window !== "undefined") {
    const keys = localStorage.getItem("raq_api_keys");
    const models = localStorage.getItem("raq_model_config");
    if (keys) {
      const parsed = JSON.parse(keys);
      if (parsed.gemini) headers["X-Gemini-Key"] = parsed.gemini;
      if (parsed.groq) headers["X-Groq-Key"] = parsed.groq;
      if (parsed.openai) headers["X-OpenAI-Key"] = parsed.openai;
      if (parsed.anthropic) headers["X-Anthropic-Key"] = parsed.anthropic;
    }
    if (models) {
      const parsed = JSON.parse(models);
      if (parsed.supervisor) headers["X-Supervisor-Model"] = parsed.supervisor;
      if (parsed.generator) headers["X-Generator-Model"] = parsed.generator;
      if (parsed.evaluator) headers["X-Evaluator-Model"] = parsed.evaluator;
      if (parsed.synthesizer) headers["X-Synthesizer-Model"] = parsed.synthesizer;
    }
  }
  return headers;
}

// ── Generic API functions ───────────────────────────────────
export async function apiFetch<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...getHeaders(), ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Lỗi không xác định" }));
    throw new Error(err.detail || `API Error ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Library API ─────────────────────────────────────────────
export interface Library {
  id: string;
  name: string;
  description?: string;
  icon_or_color?: string;
  total_documents: number;
  created_at: string;
}

export const libraryApi = {
  list: () => apiFetch<Library[]>("/api/libraries"),
  create: (data: { name: string; description?: string; icon_or_color?: string }) =>
    apiFetch<Library>("/api/libraries", { method: "POST", body: JSON.stringify(data) }),
  get: (id: string) => apiFetch<Library>(`/api/libraries/${id}`),
  delete: (id: string) => apiFetch(`/api/libraries/${id}`, { method: "DELETE" }),
};

// ── Session API ─────────────────────────────────────────────
export interface Session {
  id: string;
  library_id: string;
  title?: string;
  created_at: string;
  updated_at: string;
}

export const sessionApi = {
  list: (libraryId: string) => apiFetch<Session[]>(`/api/libraries/${libraryId}/sessions`),
  create: (libraryId: string, title?: string) =>
    apiFetch<Session>(`/api/libraries/${libraryId}/sessions`, {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  delete: (libraryId: string, sessionId: string) =>
    apiFetch(`/api/libraries/${libraryId}/sessions/${sessionId}`, { method: "DELETE" }),
};

// ── Document API ────────────────────────────────────────────
export interface Document {
  id: string;
  library_id: string;
  file_name: string;
  total_pages?: number;
  status: string;
  created_at: string;
}

export interface IngestionProgress {
  document_id: string;
  file_name: string;
  status: string;
  total_chunks: number;
  processed_chunks: number;
  progress_percent: number;
  error_message?: string;
}

export const documentApi = {
  list: (libraryId: string) => apiFetch<Document[]>(`/api/documents/library/${libraryId}`),
  upload: async (libraryId: string, file: File) => {
    const formData = new FormData();
    formData.append("library_id", libraryId);
    formData.append("file", file);

    const token = localStorage.getItem("raq_token");
    const res = await fetch(`${API_BASE}/api/documents/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload thất bại" }));
      throw new Error(err.detail);
    }
    return res.json() as Promise<Document>;
  },
  progress: (docId: string) => apiFetch<IngestionProgress>(`/api/documents/${docId}/progress`),
  delete: (docId: string) => apiFetch(`/api/documents/${docId}`, { method: "DELETE" }),
};

// ── Quiz API ────────────────────────────────────────────────
export interface QuizQuestion {
  id?: string;
  order_index?: number;
  question_text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  correct_answer: "A" | "B" | "C" | "D";
  explanation?: string;
  source_page?: number;
}

export interface Quiz {
  id: string;
  title?: string;
  description?: string;
  total_questions: number;
  is_edited_by_user: boolean;
  questions: QuizQuestion[];
}

export const quizApi = {
  create: (data: { library_id: string; title: string; questions: QuizQuestion[]; is_edited_by_user?: boolean }) =>
    apiFetch<Quiz>("/api/quizzes", { method: "POST", body: JSON.stringify(data) }),
  get: (id: string) => apiFetch<Quiz>(`/api/quizzes/${id}`),
  update: (id: string, data: { library_id: string; title: string; questions: QuizQuestion[] }) =>
    apiFetch<Quiz>(`/api/quizzes/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  listByLibrary: (libraryId: string) => apiFetch<Quiz[]>(`/api/quizzes/library/${libraryId}`),
};
