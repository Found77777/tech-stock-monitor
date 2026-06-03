"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DailyReview } from "@/lib/types";
import { todayISO, splitList } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Alert } from "@/components/ui/alert";
import { SectionCard } from "@/components/section-card";
import { ScoreSlider } from "@/components/form-controls";
import { ErrorState } from "@/components/error-state";
import { Toast } from "@/components/toast";

const emptyReview = (date = todayISO()): DailyReview => ({ review_date: date, status: "completed", market_score: 0, market_environment: "", emotion_score: 0, execution_score: 0, discipline_score: 0, daily_pnl: 0, max_drawdown: 0, largest_winner: "", largest_loser: "", mistakes: [], good_decisions: [], lessons_learned: [], tomorrow_plan: "" });

export default function DailyReviewPage() {
  const [form, setForm] = useState<DailyReview>(emptyReview());
  const [loading, setLoading] = useState(false); const [success, setSuccess] = useState(""); const [error, setError] = useState("");
  const afterClose = new Date().getHours() >= 15;
  async function load(date = form.review_date) { setLoading(true); setError(""); setSuccess(""); try { const data = await api.getDailyReview(date); setForm({ ...emptyReview(date), ...data }); } catch (err) { setError(String((err as Error).message || err)); } finally { setLoading(false); } }
  async function save() { setLoading(true); setError(""); setSuccess(""); try { await api.saveDailyReview(form); setSuccess("复盘已保存"); } catch (err) { setError(String((err as Error).message || err)); } finally { setLoading(false); } }
  useEffect(() => { load(todayISO()); }, []);
  const setNum = (k: keyof DailyReview, v: string) => setForm((f) => ({ ...f, [k]: Number(v) }));
  return <div className="space-y-6"><Toast message={success} onClose={() => setSuccess("")} /><Toast message={error} type="error" onClose={() => setError("")} /><div><h1 className="text-3xl font-bold">Daily Review</h1><p className="text-slate-500">专业盘后复盘：市场、执行、情绪纪律、错误复盘、明日计划。</p></div>{afterClose && form.status === "pending" && <Alert className="border-yellow-500/50 bg-yellow-500/15 text-yellow-100">15:30 后检测到 pending 复盘草稿，请完善并保存。</Alert>}<ErrorState error={error} />
    <div className="grid gap-6 xl:grid-cols-2">
      <SectionCard title="市场环境" description="Market Environment"><div className="grid gap-4"><label>review_date<Input value={form.review_date} onChange={(e) => setForm({ ...form, review_date: e.target.value })} onBlur={() => load(form.review_date)} /></label><label>status<Input value={form.status || "completed"} onChange={(e) => setForm({ ...form, status: e.target.value })} /></label><ScoreSlider label="market_score" value={form.market_score} onChange={(v) => setForm({ ...form, market_score: v })} /><label>market_environment<Textarea value={form.market_environment} onChange={(e) => setForm({ ...form, market_environment: e.target.value })} /></label></div></SectionCard>
      <SectionCard title="交易执行" description="Execution & PnL"><div className="grid gap-4 md:grid-cols-2"><ScoreSlider label="execution_score" value={form.execution_score} onChange={(v) => setForm({ ...form, execution_score: v })} /><label>daily_pnl<Input type="number" value={form.daily_pnl} onChange={(e) => setNum("daily_pnl", e.target.value)} /></label><label>max_drawdown<Input type="number" value={form.max_drawdown} onChange={(e) => setNum("max_drawdown", e.target.value)} /></label><label>largest_winner<Input value={form.largest_winner} onChange={(e) => setForm({ ...form, largest_winner: e.target.value })} /></label><label>largest_loser<Input value={form.largest_loser} onChange={(e) => setForm({ ...form, largest_loser: e.target.value })} /></label></div></SectionCard>
      <SectionCard title="情绪纪律" description="Emotion / Discipline"><div className="grid gap-4 md:grid-cols-2"><ScoreSlider label="emotion_score" value={form.emotion_score} onChange={(v) => setForm({ ...form, emotion_score: v })} /><ScoreSlider label="discipline_score" value={form.discipline_score} onChange={(v) => setForm({ ...form, discipline_score: v })} /></div></SectionCard>
      <SectionCard title="错误复盘" description="Mistakes & Lessons"><div className="grid gap-4"><label>mistakes<Textarea value={form.mistakes.join("\n")} onChange={(e) => setForm({ ...form, mistakes: splitList(e.target.value) })} /></label><label>good_decisions<Textarea value={form.good_decisions.join("\n")} onChange={(e) => setForm({ ...form, good_decisions: splitList(e.target.value) })} /></label><label>lessons_learned<Textarea value={form.lessons_learned.join("\n")} onChange={(e) => setForm({ ...form, lessons_learned: splitList(e.target.value) })} /></label></div></SectionCard>
    </div>
    <SectionCard title="明日计划" description="Tomorrow Plan"><Textarea value={form.tomorrow_plan} onChange={(e) => setForm({ ...form, tomorrow_plan: e.target.value })} /><div className="mt-4"><Button onClick={save} disabled={loading}>{loading ? "保存中..." : "保存复盘"}</Button></div></SectionCard>
  </div>;
}
