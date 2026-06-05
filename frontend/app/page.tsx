"use client";

import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Loader2, PlayCircle, RefreshCw, ShieldAlert, Sparkles } from "lucide-react";
import { api, API_BASE_URL } from "@/lib/api";
import type { AnalyzeTopItem, DailyReview, ReviewStats, SystemStatus, WatchlistItem } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { MetricCard } from "@/components/metric-card";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { ErrorState, EmptyState } from "@/components/error-state";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { Toast } from "@/components/toast";
import { WatchlistTable } from "@/components/data-table";
import { formatNumber, todayISO } from "@/lib/utils";

const actions = [
  ["market refresh", api.marketRefresh],
  ["history refresh", () => api.historyRefresh(120)],
  ["signals generate", api.signalsGenerate],
  ["scores generate", api.scoresGenerate],
  ["capital-flow verification", () => api.capitalFlowVerification(20)],
  ["AI analyze-top", () => api.analyzeTop(10)],
] as const;

export default function DashboardPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [top, setTop] = useState<WatchlistItem[]>([]);
  const [enhanced, setEnhanced] = useState<WatchlistItem[]>([]);
  const [aiItems, setAiItems] = useState<AnalyzeTopItem[]>([]);
  const [review, setReview] = useState<Partial<DailyReview>>({});
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [loading, setLoading] = useState<string>("");
  const [pageLoading, setPageLoading] = useState(true);
  const [success, setSuccess] = useState<string>("");
  const [error, setError] = useState<string>("");

  async function load() {
    setError(""); setPageLoading(true);
    try {
      const [s, t, e, r, st] = await Promise.all([api.status(), api.watchlistTop(20), api.enhancedTop(20), api.getDailyReview(todayISO()), api.reviewStats(30)]);
      setStatus(s); setTop(t); setEnhanced(e); setReview(r); setStats(st);
    } catch (err) { setError(String((err as Error).message || err)); }
    finally { setPageLoading(false); }
  }

  async function runAction(label: string, fn: () => Promise<unknown>) {
    setLoading(label); setSuccess(""); setError("");
    try {
      const result = await fn();
      if (label === "AI analyze-top") setAiItems(((result as { items?: AnalyzeTopItem[] }).items || []));
      setSuccess(`${label} completed`);
      await load();
    } catch (err) { setError(String((err as Error).message || err)); }
    finally { setLoading(""); }
  }

  useEffect(() => { load(); }, []);

  const realCount = enhanced.filter((x) => x.capital_flow_source === "real_eastmoney").length;
  const sinaVolumeCount = enhanced.filter((x) => x.capital_flow_source === "sina_volume_amount").length;
  const aiAnalyzed = aiItems.length || enhanced.filter((x) => Number(x.ai_adjustment || x.news_alpha_adjustment || 0) !== 0).length;
  const statChart = stats ? [{ name: "Win%", value: stats.win_rate * 100 }, { name: "Discipline", value: stats.average_discipline_score }, { name: "PnL", value: stats.average_pnl }, { name: "Drawdown", value: Math.abs(stats.max_drawdown) }] : [];
  const riskNotes = [`sina_volume_amount: ${sinaVolumeCount}`, `real_eastmoney: ${realCount}`, `API: ${API_BASE_URL}`];

  return (
    <div className="space-y-6">
      <Toast message={success} type="success" onClose={() => setSuccess("")} />
      <Toast message={error} type="error" onClose={() => setError("")} />
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div><h1 className="text-3xl font-bold tracking-tight">交易员工作台</h1><p className="text-sm text-slate-500">Bloomberg-style density · Linear clarity · Notion workflow</p></div>
        <Button variant="outline" onClick={load} disabled={pageLoading}><RefreshCw className="mr-2 h-4 w-4" />刷新状态</Button>
      </div>
      <ErrorState error={error} />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="今日候选数" value={top.length} subtitle={status?.data_source || "watchlist candidates"} tone="info" />
        <MetricCard title="Enhanced Top 数量" value={enhanced.length} subtitle={`${realCount} real / ${sinaVolumeCount} sina`} tone={sinaVolumeCount ? "info" : "positive"} />
        <MetricCard title="AI 已分析数量" value={aiAnalyzed} subtitle="News Alpha calibrated" tone={aiAnalyzed ? "positive" : "warning"} icon={<Sparkles className="h-4 w-4" />} />
        <MetricCard title="今日复盘状态" value={review.status || "none"} subtitle={review.review_date || todayISO()} tone={review.status === "completed" ? "positive" : review.status === "pending" ? "warning" : "neutral"} />
      </div>
      <SectionCard title="一键运行 Pipeline" description="所有按钮直接请求后端；loading、success、error 状态独立展示。">
        <div className="flex flex-wrap gap-3">{actions.map(([label, fn]) => <Button key={label} disabled={!!loading} onClick={() => runAction(label, fn)}>{loading === label ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PlayCircle className="mr-2 h-4 w-4" />}{label}</Button>)}</div>
      </SectionCard>
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <SectionCard title="Enhanced Watchlist Top10" description="Sticky header / rank medals / score bars / accordion details">
          {pageLoading ? <LoadingSkeleton rows={8} /> : <WatchlistTable rows={enhanced.slice(0, 10)} enhanced />}
        </SectionCard>
        <div className="space-y-6">
          <SectionCard title="今日市场状态" description="System / data / agent snapshot">
            <div className="space-y-3"><StatusBadge tone={status ? "success" : "warning"} label={status?.env || "loading"} /><StatusBadge tone={realCount ? "success" : "warning"} label={realCount ? "capital flow verified" : "capital flow pending"} /><StatusBadge tone={aiAnalyzed ? "success" : "warning"} label={aiAnalyzed ? "AI alpha active" : "AI alpha pending"} /></div>
          </SectionCard>
          <SectionCard title="AI News Alpha 摘要" description="Latest analyze-top state">
            {aiItems.length ? <div className="space-y-2 text-sm">{aiItems.slice(0, 5).map((x) => <div key={x.code} className="rounded-lg border border-white/10 bg-white/[0.03] p-3"><div className="flex justify-between"><span className="font-mono text-cyan-200">{x.code}</span><span>{formatNumber(x.news_alpha_adjustment ?? x.ai_adjustment)}</span></div><div className="mt-1 text-xs text-slate-500">{x.news_alpha_summary || x.ai_reasons}</div></div>)}</div> : <EmptyState title="AI 尚未分析" description="点击 AI analyze-top 后展示摘要。" />}
          </SectionCard>
          <SectionCard title="风险提示" description="Proxy / data / execution warnings"><div className="space-y-2">{riskNotes.map((x) => <div key={x} className="flex items-center gap-2 rounded-lg bg-yellow-500/10 p-2 text-sm text-yellow-100"><ShieldAlert className="h-4 w-4" />{x}</div>)}</div></SectionCard>
        </div>
      </div>
      <SectionCard title="最近30天复盘统计趋势" description="聚合指标 Recharts 可视化">
        {stats ? <div className="h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={statChart}><CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.2)" /><XAxis dataKey="name" stroke="#94a3b8" /><YAxis stroke="#94a3b8" /><Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", color: "#fff" }} /><Bar dataKey="value" fill="#14b8a6" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div> : <LoadingSkeleton rows={4} />}
      </SectionCard>
    </div>
  );
}
