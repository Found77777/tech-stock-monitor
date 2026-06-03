"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { WatchlistItem } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { WatchlistTable } from "@/components/data-table";
import { StatusPanel } from "@/components/status-panel";

export default function EnhancedWatchlistPage() {
  const [rows, setRows] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  async function load(runAi = false) {
    setLoading(true); setSuccess(""); setError("");
    try {
      if (runAi) {
        const res = await api.analyzeTop(10);
        setRows(res.items.map((x) => ({ ...x, enhanced_rank: x.new_rank, enhanced_score: x.ai_adjusted_score, base_total_score: x.original_score })));
        setSuccess("AI analyze-top refreshed");
      } else {
        setRows(await api.enhancedTop(20));
        setSuccess("Enhanced watchlist refreshed");
      }
    } catch (err) { setError(String((err as Error).message || err)); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);
  return <div className="space-y-6"><div><h1 className="text-3xl font-bold">Enhanced Watchlist</h1><p className="text-muted-foreground">资金流 + AI News Alpha 二次校准列表。</p></div><StatusPanel loading={loading ? "loading..." : ""} success={success} error={error} /><Card><CardHeader><CardTitle>增强榜单</CardTitle><CardDescription>real_eastmoney 绿色；proxy_fallback 黄色提示。</CardDescription><div className="flex gap-3 pt-3"><Button onClick={() => load(false)} disabled={loading}>刷新榜单</Button><Button variant="secondary" onClick={() => load(true)} disabled={loading}>运行 AI Top10</Button></div></CardHeader><CardContent><WatchlistTable rows={rows} enhanced /></CardContent></Card></div>;
}
