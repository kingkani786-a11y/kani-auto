"use client";
// CALIBRATION WATCH (owner, 2026-07-23, item #4). Observational display only —
// calibration scoring logic is FROZEN this session. Surfaces the pre-registered
// 2026-07-22 trigger (peak confidence >=70 while calibration stays flat = a
// real jam, not a correctly-conservative range-bound day) so it no longer
// needs a manual re-trace every time it recurs. Reads calibration_watch.py's
// report() as-is — no threshold is changed here or by this card.
//
// P2 (2026-08-03, "Calibration explanation, not a countdown") — extends this
// same card with WHY the score is what it is, reading analytics.py's
// _calibration().contributors (additive field, largest error first). Owner's
// explicit scope: explain, never predict. Deliberately does NOT show a
// "needs N more" / "recovers after X" countdown — no such number exists.
// The next settled outcome can move the score either direction depending on
// which bucket it lands in and whether it wins or loses; a countdown would
// be a fabricated prediction.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";

export function CalibrationWatchCard() {
  const { killSwitch } = useMarket();
  const [r, setR] = useState<any>(null);
  const [perf, setPerf] = useState<any>(null);
  useEffect(() => {
    const load = () => api.calibrationWatch?.().then(setR).catch(() => {});
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    const load = () => api.analyticsPerformance?.().then(setPerf).catch(() => {});
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, []);
  if (!r || r.peak_confidence == null) return null;

  const watch = r.status === "WATCH";
  const cal = perf?.calibration;
  const contributors: any[] = cal?.contributors || [];
  const top = contributors[0];
  // Reuses P1's reason_tags (kill_switch.py) rather than re-deriving "is
  // calibration the reason execution is blocked" from scratch — same fact,
  // one source.
  const blockedByCalibration = !!(killSwitch as any)?.active
    && ((killSwitch as any)?.reason_tags || []).includes("CALIBRATION");

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
          <div className="text-[10px] text-terminal-muted">
            Calibration{blockedByCalibration && <span className="text-terminal-bear font-bold"> · BLOCKED</span>}
          </div>
        </div>
        <div>
          <div className="text-lg font-bold tabular-nums text-white">{r.difference ?? "—"}</div>
          <div className="text-[10px] text-terminal-muted">Difference</div>
        </div>
      </div>

      {contributors.length > 0 && (
        <div className="mt-2 pt-2 border-t border-terminal-border/40">
          <div className="text-[10px] font-bold text-terminal-muted uppercase tracking-wide mb-1">
            Largest Errors — which confidence range is dragging the score
          </div>
          <div className="space-y-1">
            {contributors.slice(0, 3).map((c) => (
              <div key={c.bucket} className="flex items-center justify-between text-[11px]">
                <span className="text-gray-200">{c.bucket} bucket</span>
                <span className="text-terminal-muted">
                  Expected {c.midpoint} · Actual {c.win_rate}
                  <span className="text-terminal-warn font-semibold"> · Δ{c.abs_error}</span>
                  <span className="text-terminal-muted"> · n={c.n}</span>
                </span>
              </div>
            ))}
          </div>
          {top && (
            <div className="text-[10px] text-terminal-muted mt-1.5 italic">
              {top.win_rate < top.midpoint
                ? "Forecasts in this confidence range have historically overestimated their win probability."
                : "Forecasts in this confidence range have historically underestimated their win probability."}
            </div>
          )}
        </div>
      )}

      <div className="text-[10px] text-terminal-muted mt-2 pt-1.5 border-t border-terminal-border/40">{r.note}</div>
    </div>
  );
}
