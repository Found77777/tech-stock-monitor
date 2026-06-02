"use client";

import { Input } from "@/components/ui/input";
import { ScoreBar } from "@/components/score-bar";

export function ScoreSlider({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <label className="space-y-2 rounded-lg border border-white/10 bg-white/[0.03] p-3">
      <div className="flex justify-between text-sm"><span>{label}</span><span className="font-mono text-cyan-200">{value}</span></div>
      <Input type="range" min={0} max={100} value={value} onChange={(e) => onChange(Number(e.target.value))} />
      <ScoreBar value={value} />
    </label>
  );
}
