"use client";

import { useState } from "react";
import { ChevronDown, Medal } from "lucide-react";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { SourceBadge, SourceNotice } from "@/components/source-badge";
import { ScoreBar } from "@/components/score-bar";
import { EmptyState } from "@/components/error-state";
import { cn, formatNumber } from "@/lib/utils";
import type { WatchlistItem } from "@/lib/types";

function parseReasons(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String);
  if (typeof value !== "string") return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.map(String) : [String(parsed)];
  } catch {
    return value ? [value] : [];
  }
}

function RankCell({ rank }: { rank: number }) {
  const podium = rank <= 3;
  return <div className={cn("flex items-center gap-2 font-mono", podium && "font-bold text-yellow-200")}>
    {podium && <Medal className="h-4 w-4" />}
    <span>#{rank}</span>
  </div>;
}

export function WatchlistTable({ rows, enhanced = false }: { rows: WatchlistItem[]; enhanced?: boolean }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  if (!rows.length) return <EmptyState title="暂无榜单数据" description="请先运行 scores generate / capital-flow verification / AI analyze-top。" />;
  return (
    <div className="max-h-[620px] overflow-auto rounded-xl border border-white/10">
      <Table>
        <THead className="sticky top-0 z-10 bg-slate-950/95 backdrop-blur">
          <TR className="hover:bg-transparent">
            <TH>Rank</TH><TH>Code</TH><TH>Name</TH><TH>Base</TH><TH>Flow Adj</TH><TH>Flow Source</TH><TH>News Alpha</TH><TH>Enhanced</TH>{enhanced && <TH>Details</TH>}
          </TR>
        </THead>
        <TBody>
          {rows.map((r, i) => {
            const rank = Number(r.enhanced_rank || r.rank || i + 1);
            const reasons = parseReasons(r.ai_reasons || r.reasons);
            const events = r.top_news_events || [];
            const key = `${r.code}-${i}`;
            const score = Number(r.enhanced_score || 0);
            return (
              <TR key={key} className="group hover:bg-cyan-500/5">
                <TD><RankCell rank={rank} /></TD>
                <TD className="font-mono text-cyan-200">{r.code}</TD>
                <TD className="font-medium text-slate-100">{r.name || "-"}</TD>
                <TD><ScoreBar value={Number(r.base_total_score ?? r.total_score ?? 0)} compact /></TD>
                <TD className={Number(r.capital_flow_adjustment || 0) >= 0 ? "font-mono text-emerald-300" : "font-mono text-red-300"}>{formatNumber(r.capital_flow_adjustment)}</TD>
                <TD><SourceBadge source={r.capital_flow_source} /><SourceNotice source={r.capital_flow_source} /></TD>
                <TD className={Number(r.news_alpha_adjustment ?? r.ai_adjustment ?? 0) >= 0 ? "font-mono text-emerald-300" : "font-mono text-red-300"}>{formatNumber(r.news_alpha_adjustment ?? r.ai_adjustment)}</TD>
                <TD><div className={cn("font-mono text-lg font-semibold", score >= 75 ? "text-emerald-300" : score >= 55 ? "text-cyan-200" : score >= 35 ? "text-yellow-200" : "text-red-300")}>{formatNumber(score)}</div></TD>
                {enhanced && <TD className="min-w-[280px] max-w-lg">
                  <button className="flex w-full items-center justify-between rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-left text-xs text-slate-300 hover:bg-white/[0.06]" onClick={() => setOpen((s) => ({ ...s, [key]: !s[key] }))}>
                    <span>{reasons[0] || events[0]?.title || "展开 reasons / news timeline"}</span><ChevronDown className={cn("h-4 w-4 transition", open[key] && "rotate-180")} />
                  </button>
                  {open[key] && <div className="mt-2 space-y-2 rounded-lg border border-white/10 bg-slate-950/80 p-3">
                    {reasons.map((x, idx) => <div key={idx} className="rounded bg-slate-900/80 p-2 text-xs text-slate-300">{x}</div>)}
                    {events.slice(0, 5).map((e, idx) => <div key={`e-${idx}`} className="border-l-2 border-cyan-500/50 pl-3 text-xs"><div className="font-medium text-cyan-100">{e.event_type || "news"} · {e.impact_direction || "neutral"}</div><div className="text-slate-300">{e.title || "-"}</div><div className="mt-1 text-slate-500">{e.source || "unknown"} · {e.publish_time || "time N/A"} · rel {formatNumber(e.relevance_score, 0)} / imp {formatNumber(e.importance_score, 0)}</div></div>)}
                  </div>}
                </TD>}
              </TR>
            );
          })}
        </TBody>
      </Table>
    </div>
  );
}
