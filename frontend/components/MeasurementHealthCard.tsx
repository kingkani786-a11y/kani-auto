"use client";
// MEASUREMENT HEALTH (owner, 2026-07-23, item #1). Pure display of
// opportunity_metrics.report()'s measurement_health block (the #0 stuck-
// episode fix's own tally) — no new logic here, just the read.
//
// Note on "status": open_episodes alone is NOT the health signal — dozens of
// episodes legitimately open mid-session is normal operation, not a defect.
// status is DEGRADED only when episodes are open AND already past the
// reaper's own stale threshold (the actual #0 failure mode) — see
// opportunity_metrics.py's measurement_health docstring for the full reasoning.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function MeasurementHealthCard() {
  const [mh, setMh] = useState<any>(null);
  useEffect(() => {
    const load = () => api.opportunityMetrics().then((r: any) => setMh(r?.measurement_health)).catch(() => {});
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);
  if (!mh) return null;

  const healthy = mh.status === "HEALTHY";

  return (
    <div className={`panel border ${healthy ? "border-terminal-border/60" : "border-terminal-warn/50 bg-terminal-warn/5"}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="panel-title mb-0">Measurement Health</div>
        <span className={`text-xs font-bold ${healthy ? "text-terminal-bull" : "text-terminal-warn"}`}>
          {healthy ? "✅ HEALTHY" : "⚠️ DEGRADED"}
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
        <div>
          <div className={`text-lg font-bold tabular-nums ${mh.open_stale > 0 ? "text-terminal-warn" : "text-white"}`}>
            {mh.open_episodes}{mh.open_stale > 0 ? ` (${mh.open_stale} stale)` : ""}
          </div>
          <div className="text-[10px] text-terminal-muted">Open Episodes</div>
        </div>
        <div>
          <div className="text-lg font-bold tabular-nums text-white">{mh.recovered_today}</div>
          <div className="text-[10px] text-terminal-muted">Recovered</div>
        </div>
        <div>
          <div className="text-lg font-bold tabular-nums text-white">{mh.dropped_today}</div>
          <div className="text-[10px] text-terminal-muted">Dropped</div>
        </div>
        <div>
          <div className={`text-lg font-bold ${healthy ? "text-terminal-bull" : "text-terminal-warn"}`}>{mh.status}</div>
          <div className="text-[10px] text-terminal-muted">Status</div>
        </div>
      </div>
      <div className="text-[10px] text-terminal-muted mt-2 pt-1.5 border-t border-terminal-border/40">{mh.note}</div>
    </div>
  );
}
