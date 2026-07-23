"use client";
// CALIBRATION WATCH (owner, 2026-07-23, item #4). Observational display only —
// calibration scoring logic is FROZEN this session. Surfaces the pre-registered
// 2026-07-22 trigger (peak confidence >=70 while calibration stays flat = a
// real jam, not a correctly-conservative range-bound day) so it no longer
// needs a manual re-trace every time it recurs. Reads calibration_watch.py's
// report() as-is — no threshold is changed here or by this card.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function CalibrationWatchCard() {
  const [r, setR] = useState<any>(null);
  useEffect(() => {
    const load = () => api.calibrationWatch?.().then(setR).catch(() => {});
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, []);
  if (!r || r.peak_confidence == null) return null;

  const watch = r.status === "WATCH";

  return (
    <div className={`panel border ${watch ? "border-terminal-warn/60 bg-terminal-warn/5" : "border-terminal-border/60"}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="panel-title mb-0">Calibration Watch</div>
        <span className={`text-xs font-bold ${watch ? "text-terminal-warn" : "text-terminal-bull"}`}>
          {watch ? "⚠️ WATCH" : "✅ OK"}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3 text-center">
        <div>
          <div className="text-lg font-bold tabular-nums text-white">{r.peak_confidence}</div>
          <div className="text-[10px] text-terminal-muted">Peak Confidence</div>
        </div>
        <div>
          <div className="text-lg font-bold tabular-nums text-white">{r.calibration_score ?? "—"}</div>
          <div className="text-[10px] text-terminal-muted">Calibration</div>
        </div>
        <div>
          <div className="text-lg font-bold tabular-nums text-white">{r.difference ?? "—"}</div>
          <div className="text-[10px] text-terminal-muted">Difference</div>
        </div>
      </div>
      <div className="text-[10px] text-terminal-muted mt-2 pt-1.5 border-t border-terminal-border/40">{r.note}</div>
    </div>
  );
}
