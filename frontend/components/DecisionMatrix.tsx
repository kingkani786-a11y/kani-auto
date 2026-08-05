"use client";
// P1 — AI Decision Matrix. Renders above the Final Signal: each confirmation
// layer as PASS / FAIL / NEUTRAL with its reason (UI rule: explain every score).
// Plus P3 Institutional Thoughts. Reads layers.intelligence (no new fetch).
//
// Owner Step 6 (Evidence Panel Final, 2026-07-26) trim: this grid is
// evidence-adjacent (per-layer confirmation), so it no longer shows the
// decision wording (dm.decision, e.g. "BUY CE"/"NO TRADE") or the
// institutional-thoughts confidence% number — those belong on the Hero
// (TradeNowCard) only, per Rule 11. The pass/fail grid and behavior
// reasoning stay; only decision/confidence wording was removed.

import { useMarket } from "@/lib/store";

const V_TONE: Record<string, string> = {
  PASS: "text-terminal-bull border-terminal-bull/40 bg-terminal-bull/10",
  FAIL: "text-terminal-bear border-terminal-bear/40 bg-terminal-bear/10",
  NEUTRAL: "text-terminal-muted border-terminal-border bg-terminal-bg",
  "N/A": "text-terminal-muted/60 border-terminal-border/50 bg-terminal-bg opacity-60",
};
const MARK: Record<string, string> = { PASS: "✓", FAIL: "✕", NEUTRAL: "–", "N/A": "N/A" };

export function DecisionMatrix() {
  const { layers, signal } = useMarket();
  const dm = (layers as any)?.intelligence?.decision_matrix;
  const it = (layers as any)?.intelligence?.institutional_thoughts;
  const cal = (signal as any)?.calibration;
  if (!dm?.rows) return null;

  return (
    <section className="panel">
      <div className="panel-title flex items-center justify-between">
        <span>AI Decision Matrix</span>
        <span className="text-xs font-mono">
          <span className="text-terminal-bull">{dm.passed}</span>
          <span className="text-terminal-muted"> / {dm.total} pass</span>
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {dm.rows.map((r: any) => (
          <div key={r.layer} className={`rounded-lg border px-2.5 py-1.5 ${V_TONE[r.verdict] ?? V_TONE.NEUTRAL}`}>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold">{r.layer}</span>
              <span className="text-sm font-bold">{MARK[r.verdict]}</span>
            </div>
            <div className="text-[9px] opacity-70 truncate" title={r.reason}>{r.reason}</div>
          </div>
        ))}
      </div>

      {/* Owner Step 8 (Remove Fake Metrics, 2026-07-26): this is confluence.py's
          5-threshold FORCE-WAIT gate (backend field still named "calibration"
          for compatibility) — an unrelated, declared-threshold computation
          from the REAL, outcome-based calibration_score shown in
          CalibrationWatchCard.tsx ("Calibration Watch"). Labeled "Signal
          Gate" here so the same word "Calibration" doesn't imply these are
          the same thing. */}
      {cal && (
        <div className="mt-3 pt-2 border-t border-terminal-border/50 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px]">
          <span className={`font-bold ${cal.passed ? "text-terminal-bull" : "text-terminal-bear"}`}
            title="Declared 5-threshold gate — not the same as Calibration Watch's outcome-based calibration score.">
            Signal Gate {cal.passed ? "PASS" : "FORCE WAIT"}
          </span>
          {["data_quality", "signal_confidence", "institutional", "market_alignment", "risk_environment"].map((k) => (
            cal[k] ? (
              <span key={k} className={cal[k].pass ? "text-terminal-muted" : "text-terminal-bear"}
                title={cal[k].low_data ? "Chain-less instrument, <30 candles — this 50 is an insufficient-data default, not a computed neutral reading." : undefined}>
                {k.replace(/_/g, " ")} {cal[k].value}{cal[k].pass ? "✓" : `✕(${cal[k].min})`}
                {/* OBS-11 fix (owner, 2026-08-05) — disambiguate a displayed
                    50 that could otherwise mean either "insufficient data"
                    or "genuinely computed neutral". Display-only. */}
                {cal[k].low_data ? <sup className="text-terminal-muted"> (insufficient data)</sup> : null}
              </span>
            ) : null
          ))}
        </div>
      )}

      {it && (
        <div className="mt-3 pt-2 border-t border-terminal-border/50 text-[11px]">
          <span className="stat-label mr-1">Institutions likely:</span>
          {(it.likely || []).map((t: any, i: number) => (
            <span key={i} className="font-mono">
              {t.behaviour}{i < it.likely.length - 1 ? " · " : ""}
            </span>
          ))}
          {(it.not_yet || []).length > 0 && (
            <div className="text-terminal-muted mt-0.5">Not yet: {it.not_yet.join(", ")}</div>
          )}
        </div>
      )}
    </section>
  );
}
