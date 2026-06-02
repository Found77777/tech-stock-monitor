import { StatusBadge } from "@/components/status-badge";

export function SourceBadge({ source }: { source?: string }) {
  if (source === "real_eastmoney") return <StatusBadge tone="success" label="verified real_eastmoney" />;
  if (source === "proxy_fallback") return <StatusBadge tone="warning" label="proxy fallback" />;
  return <StatusBadge tone="neutral" label={source || "unknown"} />;
}
