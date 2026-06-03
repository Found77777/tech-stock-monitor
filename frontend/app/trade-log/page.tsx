"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { TradeLog } from "@/lib/types";
import { formatNumber, todayISO } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { StatusPanel } from "@/components/status-panel";

const emptyLog = (date = todayISO()): TradeLog => ({ trade_date: date, symbol: "", action: "buy", quantity: 0, entry_price: 0, exit_price: 0, pnl: 0, planned_trade: false, actual_reason: "", result_score: 0, notes: "" });
export default function TradeLogPage() {
  const [form, setForm] = useState<TradeLog>(emptyLog()); const [rows, setRows] = useState<TradeLog[]>([]);
  const [loading, setLoading] = useState(false); const [success, setSuccess] = useState(""); const [error, setError] = useState("");
  async function load(date = form.trade_date) { setLoading(true); setError(""); setSuccess(""); try { setRows(await api.listTradeLogs(date)); } catch (err) { setError(String((err as Error).message || err)); } finally { setLoading(false); } }
  async function save() { setLoading(true); setError(""); setSuccess(""); try { await api.createTradeLog(form); setSuccess("交易日志已新增"); setForm(emptyLog(form.trade_date)); await load(form.trade_date); } catch (err) { setError(String((err as Error).message || err)); } finally { setLoading(false); } }
  useEffect(() => { load(todayISO()); }, []);
  const setNum = (k: keyof TradeLog, v: string) => setForm((f) => ({ ...f, [k]: Number(v) }));
  return <div className="space-y-6"><div><h1 className="text-3xl font-bold">Trade Log</h1><p className="text-muted-foreground">记录真实交易执行，供纪律偏差与每日复盘使用。</p></div><StatusPanel loading={loading ? "loading..." : ""} success={success} error={error} /><Card><CardHeader><CardTitle>新增交易记录</CardTitle></CardHeader><CardContent className="grid gap-4 md:grid-cols-3"><label>trade_date<Input value={form.trade_date} onChange={(e) => setForm({ ...form, trade_date: e.target.value })} onBlur={() => load(form.trade_date)} /></label><label>symbol<Input value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })} /></label><label>action<Input value={form.action} onChange={(e) => setForm({ ...form, action: e.target.value })} /></label><label>quantity<Input type="number" value={form.quantity} onChange={(e) => setNum("quantity", e.target.value)} /></label><label>entry_price<Input type="number" value={form.entry_price} onChange={(e) => setNum("entry_price", e.target.value)} /></label><label>exit_price<Input type="number" value={form.exit_price} onChange={(e) => setNum("exit_price", e.target.value)} /></label><label>pnl<Input type="number" value={form.pnl} onChange={(e) => setNum("pnl", e.target.value)} /></label><label>result_score<Input type="number" value={form.result_score} onChange={(e) => setNum("result_score", e.target.value)} /></label><label className="flex items-center gap-2 pt-6"><input type="checkbox" checked={form.planned_trade} onChange={(e) => setForm({ ...form, planned_trade: e.target.checked })} /> planned_trade</label><label className="md:col-span-3">actual_reason<Textarea value={form.actual_reason} onChange={(e) => setForm({ ...form, actual_reason: e.target.value })} /></label><label className="md:col-span-3">notes<Textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></label><div className="md:col-span-3"><Button onClick={save} disabled={loading}>新增交易</Button></div></CardContent></Card><Card><CardHeader><CardTitle>当日交易日志</CardTitle></CardHeader><CardContent><Table><THead><TR><TH>symbol</TH><TH>action</TH><TH>qty</TH><TH>entry</TH><TH>exit</TH><TH>pnl</TH><TH>planned</TH><TH>reason</TH></TR></THead><TBody>{rows.map((r) => <TR key={r.id}><TD className="font-mono text-cyan-200">{r.symbol}</TD><TD>{r.action}</TD><TD>{formatNumber(r.quantity, 0)}</TD><TD>{formatNumber(r.entry_price)}</TD><TD>{formatNumber(r.exit_price)}</TD><TD className={r.pnl >= 0 ? "text-emerald-300" : "text-red-300"}>{formatNumber(r.pnl)}</TD><TD>{r.planned_trade ? "Y" : "N"}</TD><TD>{r.actual_reason}</TD></TR>)}</TBody></Table></CardContent></Card></div>;
}
