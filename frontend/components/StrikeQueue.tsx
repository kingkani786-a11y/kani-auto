"use client";
// Phase A — Strike Queue. READY / WATCH / PREPARING strikes with star rating,
// so the best strike is visible before BUY. Derivation-only display.

import { useMarket } from "@/lib/store";

const statusTone = (s: string) =>
  s === "READY" ? "text-terminal-bull" : s === "WATCH" ? "text-terminal-warn" : "text-terminal-muted";

export function StrikeQueue() {
  const { decision } = useMarket();
  const q = (decision as any)?.strike_queue;
  if (!q?.length) return null;

  return (
    <div className="panel">
      <div className="panel-title">Strike Queue</div>
      <div className="space-y-1.5">
        {q.map((s: any, i: number) => (
          <div key={i} className="flex items-center justify-between text-xs">
            <span className={`w-20 font-bold ${statusTone(s.status)}`}>{s.status}</span>
            <span className="w-24 font-mono">{s.strike} {s.type}</span>
            <span className="w-16 font-mono text-terminal-muted">₹{s.premium ?? "—"}</span>
            <span className="w-20 text-terminal-warn">{"★".repeat(s.stars)}{"☆".repeat(5 - s.stars)}</span>
            <span className="w-12 text-right font-mono text-terminal-muted">{s.score}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
