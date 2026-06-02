"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { AIReviewSummary } from "@/lib/types";
import { todayISO, formatNumber } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { StatusPanel } from "@/components/status-panel";

function ListBlock({ title, items, tone = "slate" }: { title: string; items: string[]; tone?: "green" | "red" | "yellow" | "slate" }) {
  const cls = tone === "green" ? "border-emerald-500/30 bg-emerald-500/10" : tone === "red" ? "border-red-500/30 bg-red-500/10" : tone === "yellow" ? "border-yellow-500/30 bg-yellow-500/10" : "border-slate-500/30 bg-slate-500/10";
  return <Card className={cls}><CardHeader><CardTitle className="text-base">{title}</CardTitle></CardHeader><CardContent><ul className="list-disc space-y-1 pl-5 text-sm">{(items.length ? items : ["暂无"] ).map((x, i) => <li key={i}>{x}</li>)}</ul></CardContent></Card>;
}

export default function AIReviewSummaryPage() {
  const [date, setDate] = useState(todayISO()); const [data, setData] = useState<AIReviewSummary | null>(null);
  const [loading, setLoading] = useState(false); const [error, setError] = useState(""); const [success, setSuccess] = useState("");
  async function run() { setLoading(true); setError(""); setSuccess(""); try { setData(await api.aiReviewSummary(date)); setSuccess("AI复盘总结已生成"); } catch (err) { setError(String((err as Error).message || err)); } finally { setLoading(false); } }
  return <div className="space-y-6"><div><h1 className="text-3xl font-bold">AI Review Summary</h1><p className="text-muted-foreground">调用后端 /api/review/ai-summary 输出结构化复盘建议。</p></div><StatusPanel loading={loading ? "loading..." : ""} success={success} error={error} /><Card><CardContent className="flex flex-wrap gap-3 pt-5"><Input className="max-w-xs" value={date} onChange={(e) => setDate(e.target.value)} /><Button onClick={run} disabled={loading}>生成总结</Button></CardContent></Card>{data && <><div className="flex gap-3"><Badge className="border-cyan-500/40 bg-cyan-500/15 text-cyan-100">discipline {formatNumber(data.discipline_score, 0)}</Badge><Badge className="border-red-500/40 bg-red-500/15 text-red-100">risk {formatNumber(data.risk_score, 0)}</Badge></div><div className="grid gap-4 md:grid-cols-2"><ListBlock title="Strengths" items={data.strengths} tone="green" /><ListBlock title="Weaknesses" items={data.weaknesses} tone="red" /><ListBlock title="Repeated Mistakes" items={data.repeated_mistakes} tone="yellow" /><ListBlock title="Suggestions" items={data.suggestions} /></div></>}</div>;
}
