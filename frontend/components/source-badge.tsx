import { StatusBadge } from "@/components/status-badge";

export function SourceBadge({ source }: { source?: string }) {
  if (source === "real_eastmoney") return <StatusBadge tone="success" label="真实资金流" />;
  if (source === "efinance_history_bill") return <StatusBadge tone="info" label="efinance历史资金流" />;
  if (source === "efinance") return <StatusBadge tone="info" label="efinance资金流 / 半真实数据" />;
  if (source === "proxy_estimated") return <StatusBadge tone="warning" label="估算资金流，非真实" />;
  if (source === "unavailable") return <StatusBadge tone="danger" label="真实资金流不可用" />;
  if (source === "none") return <StatusBadge tone="neutral" label="未启用资金流" />;
  if (source === "proxy_fallback") return <StatusBadge tone="warning" label="legacy proxy fallback" />;
  return <StatusBadge tone="neutral" label={source || "unknown"} />;
}

export function SourceNotice({ source }: { source?: string }) {
  if (source === "proxy_estimated") return <div className="mt-1 text-xs text-orange-200">该资金流为量价估算，不代表真实主力资金流。</div>;
  if (source === "efinance_history_bill") return <div className="mt-1 text-xs text-cyan-200">capital_flow_confidence=70</div>;
  if (source === "unavailable") return <div className="mt-1 text-xs text-red-200">资金流不可用，本次评分未使用资金流。</div>;
  return null;
}
