import type { ReactNode } from "react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type Tone = "positive" | "negative" | "neutral" | "warning" | "info";

export function MetricCard({ title, value, subtitle, tone = "neutral", icon }: { title: string; value: ReactNode; subtitle?: ReactNode; tone?: Tone; icon?: ReactNode }) {
  const Icon = tone === "positive" ? ArrowUpRight : tone === "negative" ? ArrowDownRight : Minus;
  return (
    <Card className={cn("relative overflow-hidden border-white/10 bg-slate-950/70 shadow-2xl shadow-black/20", tone === "positive" && "ring-1 ring-emerald-500/20", tone === "negative" && "ring-1 ring-red-500/20", tone === "warning" && "ring-1 ring-yellow-500/20", tone === "info" && "ring-1 ring-cyan-500/20")}>
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/60 to-transparent" />
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">{title}</div>
          <div className="rounded-lg border border-white/10 bg-white/5 p-2 text-slate-300">{icon || <Icon className="h-4 w-4" />}</div>
        </div>
        <div className={cn("mt-3 text-3xl font-semibold tracking-tight", tone === "positive" && "text-emerald-300", tone === "negative" && "text-red-300", tone === "warning" && "text-yellow-200", tone === "info" && "text-cyan-200")}>{value}</div>
        {subtitle && <div className="mt-2 text-xs text-slate-500">{subtitle}</div>}
      </CardContent>
    </Card>
  );
}
