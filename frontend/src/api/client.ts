// Thin typed API client used by every feature.
import type {
  BlockCreate,
  BlockRead,
  BlockUpdate,
  ChatRequest,
  ChatResponse,
  GapSummary,
  GoalCreate,
  GoalRead,
  LogCreate,
  LogRead,
  PatternRead,
  Period,
  PlanRequest,
  PlanResponse,
  UserRead,
} from "./types";

const TOKEN_KEY = "bogi_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`/api${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // auth
  login: (email: string) =>
    req<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  me: () => req<UserRead>("/auth/me"),

  // blocks (calendar / planning)
  listBlocks: (start?: string, end?: string) => {
    const q = new URLSearchParams();
    if (start) q.set("start", start);
    if (end) q.set("end", end);
    return req<BlockRead[]>(`/blocks?${q.toString()}`);
  },
  createBlock: (body: BlockCreate) =>
    req<BlockRead>("/blocks", { method: "POST", body: JSON.stringify(body) }),
  updateBlock: (id: number, body: BlockUpdate) =>
    req<BlockRead>(`/blocks/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteBlock: (id: number) => req<void>(`/blocks/${id}`, { method: "DELETE" }),
  planDay: (body: PlanRequest) =>
    req<PlanResponse>("/blocks/plan", { method: "POST", body: JSON.stringify(body) }),

  // accountability (reality)
  listLogs: (start?: string, end?: string) => {
    const q = new URLSearchParams();
    if (start) q.set("start", start);
    if (end) q.set("end", end);
    return req<LogRead[]>(`/logs?${q.toString()}`);
  },
  createLog: (body: LogCreate) =>
    req<LogRead>("/logs", { method: "POST", body: JSON.stringify(body) }),
  unaccountedBlocks: () => req<BlockRead[]>("/logs/unaccounted"),

  // data bank
  summary: (period: Period, anchor?: string) => {
    const q = new URLSearchParams({ period });
    if (anchor) q.set("anchor", anchor);
    return req<GapSummary>(`/databank/summary?${q.toString()}`);
  },

  // coach
  chat: (body: ChatRequest) =>
    req<ChatResponse>("/coach/chat", { method: "POST", body: JSON.stringify(body) }),
  getConversation: (id: number) => req<ChatResponse>(`/coach/conversations/${id}`),

  // patterns (beta)
  listPatterns: () => req<PatternRead[]>("/patterns"),
  analyzePatterns: () => req<PatternRead[]>("/patterns/analyze", { method: "POST" }),

  // goals
  listGoals: () => req<GoalRead[]>("/goals"),
  createGoal: (body: GoalCreate) =>
    req<GoalRead>("/goals", { method: "POST", body: JSON.stringify(body) }),
  deleteGoal: (id: number) => req<void>(`/goals/${id}`, { method: "DELETE" }),
};
