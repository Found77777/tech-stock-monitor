import { cn, formatNumber } from "@/lib/utils";

export function ScoreBar({ value, max = 100, compact = false }: { value?: number; max?: number; compact?: boolean }) {
  const n = Math.max(0, Math.min(max, Number(value || 0)));
  const pct = max ? (n / max) * 100 : 0;
  const tone = n >= 75 ? "bg-emerald-400" : n >= 55 ? "bg-cyan-400" : n >= 35 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className={cn("min-w-[110px]", compact && "min-w-[80px]")}> 
      <div className="mb-1 flex justify-between text-[11px] text-slate-400"><span>score</span><span>{formatNumber(n, 1)}</span></div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-800"><div className={cn("h-full rounded-full", tone)} style={{ width: `${pct}%` }} /></div>
    </div>
  );
}
