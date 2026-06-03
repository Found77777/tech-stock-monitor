import type { AIReviewSummary, AnalyzeTopItem, DailyReview, PlanDrift, ReviewStats, SystemStatus, TradeLog, TradePlan, WatchlistItem } from "./types";

const DEFAULT_BASE_URL = "http://127.0.0.1:8000";
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_BASE_URL;

type RequestOptions = Omit<RequestInit, "body"> & { body?: unknown; query?: Record<string, string | number | boolean | undefined | null> };

function withQuery(path: string, query?: RequestOptions["query"]) {
  const url = new URL(path, API_BASE_URL);
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  });
  return url.toString();
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, query, headers, ...rest } = options;
  const res = await fetch(withQuery(path, query), {
    ...rest,
    headers: { "Content-Type": "application/json", ...(headers || {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  const data = text ? safeJson(text) : null;
  if (!res.ok) {
    const detail = typeof data === "object" && data && "detail" in data ? JSON.stringify((data as { detail: unknown }).detail) : text;
    throw new Error(`${res.status} ${res.statusText}: ${detail || "API request failed"}`);
  }
  return data as T;
}

function safeJson(text: string): unknown {
  try { return JSON.parse(text); } catch { return text; }
}

export const api = {
  status: () => apiRequest<SystemStatus>("/"),
  health: () => apiRequest<SystemStatus>("/health"),
  marketRefresh: () => apiRequest<unknown>("/market/refresh", { method: "POST" }),
  historyRefresh: (days = 120) => apiRequest<unknown>("/history/refresh", { method: "POST", query: { days } }),
  signalsGenerate: () => apiRequest<unknown>("/signals/generate", { method: "POST" }),
  scoresGenerate: () => apiRequest<unknown>("/scores/generate", { method: "POST" }),
  capitalFlowVerification: (topN = 20, forceRefresh = false) => apiRequest<{ results: WatchlistItem[]; real_count?: number; fallback_count?: number }>("/verification/capital-flow-top", { method: "POST", query: { top_n: topN, force_refresh: forceRefresh } }),
  analyzeTop: (topN = 10) => apiRequest<{ items: AnalyzeTopItem[] }>("/agent/analyze-top", { method: "POST", body: { top_n: topN, rerank: true } }),
  watchlistTop: (limit = 20) => apiRequest<WatchlistItem[]>("/watchlist/top", { query: { limit } }),
  enhancedTop: (limit = 20) => apiRequest<WatchlistItem[]>("/watchlist/enhanced-top", { query: { limit } }),
  getDailyReview: (date: string) => apiRequest<Partial<DailyReview>>(date ? `/api/review/daily/${date}` : "/api/review/daily/"),
  saveDailyReview: (review: DailyReview) => apiRequest<DailyReview>("/api/review/daily", { method: "POST", body: review }),
  getTradePlan: (date: string) => apiRequest<Partial<TradePlan>>(`/api/review/trade-plan/${date}`),
  saveTradePlan: (plan: TradePlan) => apiRequest<TradePlan>("/api/review/trade-plan", { method: "POST", body: plan }),
  listTradeLogs: (date: string) => apiRequest<TradeLog[]>(`/api/review/trades/${date}`),
  createTradeLog: (log: TradeLog) => apiRequest<TradeLog>("/api/review/trades", { method: "POST", body: log }),
  planDrift: (date: string) => apiRequest<PlanDrift>("/api/review/plan-drift", { query: { trade_date: date } }),
  reviewStats: (days = 30) => apiRequest<ReviewStats>("/api/review/stats", { query: { days } }),
  aiReviewSummary: (date: string) => apiRequest<AIReviewSummary>("/api/review/ai-summary", { method: "POST", body: { review_date: date } }),
};
