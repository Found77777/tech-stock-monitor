import { AlertTriangle, Inbox } from "lucide-react";
import { Alert } from "@/components/ui/alert";

export function ErrorState({ error }: { error?: string }) {
  if (!error) return null;
  return <Alert className="border-red-500/40 bg-red-500/10 text-red-100"><div className="flex gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><pre className="whitespace-pre-wrap font-sans text-sm">{error}</pre></div></Alert>;
}

export function EmptyState({ title = "暂无数据", description = "请先运行后端流程或刷新页面。" }: { title?: string; description?: string }) {
  return <div className="flex min-h-[160px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-8 text-center"><Inbox className="mb-3 h-8 w-8 text-slate-500" /><div className="font-medium text-slate-300">{title}</div><div className="mt-1 text-sm text-slate-500">{description}</div></div>;
}
