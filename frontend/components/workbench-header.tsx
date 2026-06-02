"use client";

import { useEffect, useState } from "react";
import { CalendarDays, Clock, RadioTower } from "lucide-react";
import { api } from "@/lib/api";
import type { SystemStatus } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import { todayISO } from "@/lib/utils";

export function WorkbenchHeader() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string>("");
  const [agentOk, setAgentOk] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    Promise.allSettled([api.status(), api.health()]).then(([s, h]) => {
      if (!active) return;
      if (s.status === "fulfilled") setStatus(s.value);
      setAgentOk(h.status === "fulfilled");
      setUpdatedAt(new Date().toLocaleTimeString("zh-CN", { hour12: false }));
    });
    return () => { active = false; };
  }, []);

  return (
    <header className="sticky top-0 z-30 mb-6 rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.3em] text-slate-500">Professional Trading Workbench</div>
          <div className="mt-1 text-lg font-semibold text-slate-100">{status?.app_name || "Tech Stock Monitor"}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <StatusBadge tone={status ? "success" : "warning"} label={status?.env || status?.status || "loading"} />
          <StatusBadge tone={agentOk ? "success" : agentOk === false ? "danger" : "warning"} label={`agent ${agentOk ? "online" : agentOk === false ? "error" : "checking"}`} />
          <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-slate-300"><CalendarDays className="h-3.5 w-3.5" />{todayISO()}</div>
          <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-slate-300"><Clock className="h-3.5 w-3.5" />{updatedAt || "--:--:--"}</div>
          <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-slate-300"><RadioTower className="h-3.5 w-3.5" />{status?.data_source || "data source"}</div>
        </div>
      </div>
    </header>
  );
}
