"use client";

import { useState } from "react";
import { CheckCircle2, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import type { PlanDrift } from "@/lib/types";
import { todayISO, formatNumber } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { SectionCard } from "@/components/section-card";
import { ErrorState, EmptyState } from "@/components/error-state";
import { Toast } from "@/components/toast";

function DisciplineGauge({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  const bg = `conic-gradient(${pct >= 80 ? "#10b981" : pct >= 60 ? "#eab308" : "#ef4444"} ${pct * 3.6}deg, #1e293b 0deg)`;
  return <div className="mx-auto grid h-48 w-48 place-items-center rounded-full p-3" style={{ background: bg }}><div className="grid h-full w-full place-items-center rounded-full bg-slate-950"><div className="text-center"><div className="text-4xl font-bold">{formatNumber(score, 0)}</div><div className="text-xs uppercase tracking-widest text-slate-500">discipline</div></div></div></div>;
}

export default function PlanDriftPage() {
  const [date, setDate] = useState(todayISO()); const [data, setData] = useState<PlanDrift | null>(null);
  const [loading, setLoading] = useState(false); const [error, setError] = useState(""); const [success, setSuccess] = useState("");
  async function load() { setLoading(true); setError(""); setSuccess(""); try { setData(await api.planDrift(date)); setSuccess("偏差分析已更新"); } catch (err) { setError(String((err as Error).message || err)); } finally { setLoading(false); } }
  return <div className="space-y-6"><Toast message={success} onClose={() => setSuccess("")} /><Toast message={error} type="error" onClose={() => setError("")} /><div><h1 className="text-3xl font-bold">Plan Drift</h1><p className="text-slate-500">计划 vs 执行偏差分析，纪律分仪表盘与违规清单。</p></div><ErrorState error={error} /><SectionCard title="查询日期" description="选择交易日分析 trade_plan 与 trade_log"><div className="flex flex-wrap gap-3"><Input className="max-w-xs" value={date} onChange={(e) => setDate(e.target.value)} /><Button onClick={load} disabled={loading}>{loading ? "分析中..." : "分析偏差"}</Button></div></SectionCard>{data ? <div className="grid gap-6 xl:grid-cols-[320px_1fr]"><Card className="border-white/10 bg-slate-950/70"><CardContent className="p-6"><DisciplineGauge score={data.discipline_score} /></CardContent></Card><SectionCard title="重点摘要" description={data.summary}>{data.violations.length === 0 ? <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-5 text-emerald-100"><CheckCircle2 className="mb-2 h-6 w-6" />无明显纪律偏差，计划执行一致。</div> : <div className="space-y-3">{data.violations.map((v, i) => <div key={i} className="rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-red-100"><div className="flex items-center gap-2 font-semibold"><ShieldAlert className="h-4 w-4" />{v.type} · {v.symbol}</div><div className="mt-1 text-sm">{v.message} · severity {v.severity}</div></div>)}</div>}</SectionCard></div> : <EmptyState title="尚未运行偏差分析" description="选择日期后点击分析偏差。" />}</div>;
}
