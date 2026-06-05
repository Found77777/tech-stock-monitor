import { StatusBadge } from "@/components/status-badge";

export function SourceBadge({ source }: { source?: string }) {
  if (source === "real_eastmoney") return <StatusBadge tone="success" label="真实资金流" />;
  if (source === "efinance_history_bill") return <StatusBadge tone="info" label="efinance历史资金流" />;
  if (source === "sina_volume_amount") return <StatusBadge tone="info" label="Sina量价资金强度" />;
  if (source === "efinance") return <StatusBadge tone="info" label="efinance资金流 / 半真实数据" />;
  if (source === "proxy_estimated" || source === "proxy" || source === "proxy_fallback") return <StatusBadge tone="warning" label="Proxy估算，非真实资金流" />;
  if (source === "unavailable") return <StatusBadge tone="danger" label="资金流不可用" />;
  if (source === "not_verified") return <StatusBadge tone="neutral" label="未验证资金流" />;
  if (source === "none") return <StatusBadge tone="neutral" label="未启用资金流" />;
  return <StatusBadge tone="neutral" label={source || "unknown"} />;
}

export function SourceNotice({ source, confidence, reason }: { source?: string; confidence?: number; reason?: string }) {
  if (source === "proxy_estimated" || source === "proxy" || source === "proxy_fallback") return <div className="mt-1 text-xs text-orange-200">Proxy估算，非真实资金流。</div>;
  if (source === "sina_volume_amount") return <div className="mt-1 text-xs text-cyan-200">Confidence: {confidence ?? "-"}%<br />基于成交额、成交量和价格共振估算，不代表真实主力资金流。{reason ? <><br />{reason}</> : null}</div>;
  if (source === "efinance_history_bill") return <div className="mt-1 text-xs text-cyan-200">Confidence: {confidence ?? "-"}%{reason ? <><br />{reason}</> : null}</div>;
  if (source === "unavailable") return <div className="mt-1 text-xs text-red-200">资金流不可用，本次评分未使用资金流。</div>;
  return null;
}
