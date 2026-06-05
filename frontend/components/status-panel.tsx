"use client";

import { Alert } from "@/components/ui/alert";

export function StatusPanel({ loading, success, error }: { loading?: string; success?: string; error?: string }) {
  if (loading) return <Alert className="border-cyan-500/40 bg-cyan-500/10 text-cyan-100">{loading}</Alert>;
  if (success) return <Alert className="border-emerald-500/40 bg-emerald-500/10 text-emerald-100">{success}</Alert>;
  if (error) return <Alert className="border-red-500/40 bg-red-500/10 text-red-100 whitespace-pre-wrap">{error}</Alert>;
  return null;
}
