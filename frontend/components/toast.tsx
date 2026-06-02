"use client";

import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export function Toast({ message, type = "success", onClose }: { message?: string; type?: "success" | "error" | "info"; onClose?: () => void }) {
  if (!message) return null;
  return (
    <div className={cn("fixed right-5 top-5 z-50 flex max-w-md items-start gap-3 rounded-xl border p-4 text-sm shadow-2xl backdrop-blur", type === "success" && "border-emerald-500/40 bg-emerald-950/90 text-emerald-100", type === "error" && "border-red-500/40 bg-red-950/90 text-red-100", type === "info" && "border-cyan-500/40 bg-cyan-950/90 text-cyan-100")}>
      <div>{message}</div>
      {onClose && <button onClick={onClose} className="text-current/70 hover:text-current"><X className="h-4 w-4" /></button>}
    </div>
  );
}
