"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, X } from "lucide-react";
import { api } from "@/lib/api";
import type { TradePlan } from "@/lib/types";
import { todayISO } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Alert } from "@/components/ui/alert";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import { Toast } from "@/components/toast";

type PlannedTrade = { symbol?: string; action?: string; note?: string };
const emptyPlan = (date = todayISO()): TradePlan => ({ trade_date: date, watch_symbols: [], focus_sectors: [], market_view: "", bull_case: "", bear_case: "", max_position: 0, planned_trades: [], risk_notes: [] });

function TagInput({ values, onChange, placeholder }: { values: string[]; onChange: (v: string[]) => void; placeholder: string }) {
  const [text, setText] = useState("");
  function add() { const v = text.trim(); if (v && !values.includes(v)) onChange([...values, v]); setText(""); }
  return <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3"><div className="mb-2 flex flex-wrap gap-2">{values.map((x) => <Badge key={x} className="border-cyan-500/30 bg-cyan-500/10 text-cyan-100">{x}<button className="ml-2" onClick={() => onChange(values.filter((v) => v !== x))}><X className="h-3 w-3" /></button></Badge>)}</div><div className="flex gap-2"><Input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }} placeholder={placeholder} /><Button type="button" variant="secondary" onClick={add}>添加</Button></div></div>;
}

export default function TradePlanPage() {
  const [form, setForm] = useState<TradePlan>(emptyPlan()); const [planned, setPlanned] = useState<PlannedTrade[]>([]);
  const [loading, setLoading] = useState(false); const [success, setSuccess] = useState(""); const [error, setError] = useState("");
  async function load(date = form.trade_date) { setLoading(true); setError(""); setSuccess(""); try { const data = await api.getTradePlan(date); const next = { ...emptyPlan(date), ...data }; setForm(next); setPlanned((next.planned_trades as PlannedTrade[]) || []); } catch (err) { setError(String((err as Error).message || err)); } finally { setLoading(false); } }
  async function save() { setLoading(true); setError(""); setSuccess(""); try { await api.saveTradePlan({ ...form, planned_trades: planned }); setSuccess("盘前计划已保存"); } catch (err) { setError(String((err as Error).message || err)); } finally { setLoading(false); } }
  useEffect(() => { load(todayISO()); }, []);
  return <div className="space-y-6"><Toast message={success} onClose={() => setSuccess("")} /><Toast message={error} type="error" onClose={() => setError("")} /><div><h1 className="text-3xl font-bold">Trade Plan</h1><p className="text-slate-500">盘前计划：标签化标的/板块，动态计划交易，风险卡片。</p></div><ErrorState error={error} />
    <div className="grid gap-6 xl:grid-cols-2">
      <SectionCard title="核心计划" description="Date / View / Position"><div className="grid gap-4"><label>trade_date<Input value={form.trade_date} onChange={(e) => setForm({ ...form, trade_date: e.target.value })} onBlur={() => load(form.trade_date)} /></label><label>max_position<Input type="number" value={form.max_position} onChange={(e) => setForm({ ...form, max_position: Number(e.target.value) })} /></label><label>market_view<Textarea value={form.market_view} onChange={(e) => setForm({ ...form, market_view: e.target.value })} /></label></div></SectionCard>
      <SectionCard title="关注池" description="Tag input"><div className="space-y-4"><TagInput values={form.watch_symbols} onChange={(watch_symbols) => setForm({ ...form, watch_symbols })} placeholder="输入股票代码后回车" /><TagInput values={form.focus_sectors} onChange={(focus_sectors) => setForm({ ...form, focus_sectors })} placeholder="输入板块后回车" /></div></SectionCard>
      <SectionCard title="牛熊推演" description="Scenario planning"><div className="grid gap-4"><label>bull_case<Textarea value={form.bull_case} onChange={(e) => setForm({ ...form, bull_case: e.target.value })} /></label><label>bear_case<Textarea value={form.bear_case} onChange={(e) => setForm({ ...form, bear_case: e.target.value })} /></label></div></SectionCard>
      <SectionCard title="风险卡片" description="Risk notes"><Alert className="mb-3 border-yellow-500/40 bg-yellow-500/10 text-yellow-100">盘中执行前必须核对风险卡片，避免计划外交易。</Alert><TagInput values={form.risk_notes} onChange={(risk_notes) => setForm({ ...form, risk_notes })} placeholder="输入风险备注" /></SectionCard>
    </div>
    <SectionCard title="Planned Trades 动态列表" description="无需手写 JSON"><div className="space-y-3">{planned.map((t, i) => <div key={i} className="grid gap-2 rounded-lg border border-white/10 bg-white/[0.03] p-3 md:grid-cols-[1fr_1fr_2fr_auto]"><Input placeholder="symbol" value={t.symbol || ""} onChange={(e) => setPlanned((p) => p.map((x, idx) => idx === i ? { ...x, symbol: e.target.value } : x))} /><Input placeholder="action" value={t.action || "buy"} onChange={(e) => setPlanned((p) => p.map((x, idx) => idx === i ? { ...x, action: e.target.value } : x))} /><Input placeholder="note" value={t.note || ""} onChange={(e) => setPlanned((p) => p.map((x, idx) => idx === i ? { ...x, note: e.target.value } : x))} /><Button variant="destructive" onClick={() => setPlanned((p) => p.filter((_, idx) => idx !== i))}><Trash2 className="h-4 w-4" /></Button></div>)}<Button variant="secondary" onClick={() => setPlanned((p) => [...p, { symbol: "", action: "buy", note: "" }])}><Plus className="mr-2 h-4 w-4" />新增计划交易</Button><div><Button className="mt-4" onClick={save} disabled={loading}>{loading ? "保存中..." : "保存计划"}</Button></div></div></SectionCard>
  </div>;
}
