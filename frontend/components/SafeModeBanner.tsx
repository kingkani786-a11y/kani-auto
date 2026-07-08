"use client";
// PHASE D — Disaster Recovery / Safe Mode banner. Infrastructure failure →
// signals frozen into WAIT. Highest-priority alert, top of the dashboard.

import { useMarket } from "@/lib/store";

export function SafeModeBanner() {
  const { safeMode } = useMarket();
  if (!safeMode?.active) return null;

  return (
    <div className="panel border-2 border-terminal-bear bg-terminal-bear/15 py-3">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="w-2.5 h-2.5 rounded-full bg-terminal-bear animate-pulse" />
        <span className="text-sm font-bold tracking-wider text-terminal-bear">
          🛡 SAFE MODE ACTIVE — SIGNALS FROZEN (WAIT)
        </span>
      </div>
      <ul className="text-xs text-gray-200 space-y-0.5 mb-1.5">
        {(safeMode.triggers || []).map((t: string, i: number) => (
          <li key={i} className="flex gap-2"><span className="text-terminal-bear">▸</span>{t}</li>
        ))}
      </ul>
      <div className="text-[11px] text-terminal-muted">
        Actions: {(safeMode.actions || []).join(" · ")}.
      </div>
      <div className="text-[11px] text-terminal-muted mt-0.5">
        {safeMode.recovery} · Learning, memory & logs preserved.
      </div>
    </div>
  );
}
