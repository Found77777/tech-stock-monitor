import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type StatusTone = "success" | "warning" | "danger" | "neutral" | "info";

const toneClass: Record<StatusTone, string> = {
  success: "border-emerald-500/50 bg-emerald-500/15 text-emerald-200 shadow-[0_0_20px_rgba(16,185,129,.08)]",
  warning: "border-yellow-500/50 bg-yellow-500/15 text-yellow-100 shadow-[0_0_20px_rgba(234,179,8,.08)]",
  danger: "border-red-500/50 bg-red-500/15 text-red-100 shadow-[0_0_20px_rgba(239,68,68,.08)]",
  neutral: "border-slate-500/50 bg-slate-500/15 text-slate-200",
  info: "border-cyan-500/50 bg-cyan-500/15 text-cyan-100 shadow-[0_0_20px_rgba(6,182,212,.08)]",
};

export function StatusBadge({ label, tone = "neutral", className }: { label: string; tone?: StatusTone; className?: string }) {
  return <Badge className={cn("gap-1.5 font-mono uppercase tracking-wide", toneClass[tone], className)}><span className="h-1.5 w-1.5 rounded-full bg-current" />{label}</Badge>;
}
