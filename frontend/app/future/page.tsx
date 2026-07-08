"use client";
// AI FUTURE — Scenario Simulation · Next-Move Probability · Time-to-Event.
// Reads the forward-intelligence already streamed in layers (no new fetch).
// Probabilities only — never a guarantee of direction, tops or bottoms.

import { useMarket } from "@/lib/store";

const fmt = (n?: number | null) => (n == null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: 1 }));

function ProbBar({ b, r, s }: { b: number; r: number; s: number }) {
  return (
    <div className="flex h-3 rounded overflow-hidden bg-terminal-bg text-[8px] font-bold">
      <div className="bg-terminal-bull/70 flex items-center justify-center" style={{ width: `${b}%` }}>{b > 12 ? `${b}%` : ""}</div>
      <div className="bg-terminal-border flex items-center justify-center" style={{ width: `${r}%` }}>{r > 12 ? `${r}%` : ""}</div>
      <div className="bg-terminal-bear/70 flex items-center justify-center" style={{ width: `${s}%` }}>{s > 12 ? `${s}%` : ""}</div>
    </div>
  );
}

export default function FuturePage() {
  const { layers, status } = useMarket();
  const f = (layers as any)?.future;

  if (status && !status.connected) return <div className="panel text-sm text-terminal-muted">Connect to see AI Future intelligence.</div>;
  if (!f) return <div className="panel text-sm text-terminal-muted">Forward intelligence loads with the first analysis cycle.</div>;

  const sc = f.scenarios || {};
  const nm = f.next_move || {};
  const te = f.time_to_event || {};

  return (
    <div className="space-y-4 max-w-4xl mx-auto">
      <div className="text-[11px] text-terminal-muted">Probability-based scenarios — not predictions. Primary: <span className="text-terminal-accent font-bold">{String(sc.primary || "—").toUpperCase()}</span></div>

      {/* Scenario Simulation */}
      <section className="panel">
        <div className="panel-title">Scenario Simulation</div>
        {["bullish", "range", "bearish"].map((k) => {
          const v = sc[k] || {};
          const tone = k === "bullish" ? "text-terminal-bull" : k === "bearish" ? "text-terminal-bear" : "text-terminal-muted";
          return (
            <div key={k} className="flex items-center gap-3 py-1.5 border-t border-terminal-border/40 text-sm">
              <span className={`w-20 font-bold uppercase ${tone}`}>{k}</span>
              <span className="font-mono text-lg w-14">{v.probability ?? "—"}%</span>
              <span className="text-[11px] text-terminal-muted flex-1">{v.note}</span>
              <span className="text-[11px] text-terminal-muted">conf {v.confidence ?? "—"}% · invalidation {fmt(typeof v.invalidation === "number" ? v.invalidation : null) || v.invalidation}</span>
            </div>
          );
        })}
      </section>

      {/* Next-Move Probability */}
      <section className="panel">
        <div className="panel-title">Next-Move Probability</div>
        <div className="space-y-2">
          {["5m", "15m", "30m", "60m"].map((h) => (
            nm[h] ? (
              <div key={h} className="flex items-center gap-3">
                <span className="w-10 text-xs font-mono text-terminal-muted">{h}</span>
                <div className="flex-1"><ProbBar b={nm[h].bullish} r={nm[h].range} s={nm[h].bearish} /></div>
              </div>
            ) : null
          ))}
          <div className="flex gap-4 text-[10px] text-terminal-muted mt-1">
            <span><span className="inline-block w-2 h-2 bg-terminal-bull/70 rounded-sm mr-1" />Bullish</span>
            <span><span className="inline-block w-2 h-2 bg-terminal-border rounded-sm mr-1" />Range</span>
            <span><span className="inline-block w-2 h-2 bg-terminal-bear/70 rounded-sm mr-1" />Bearish</span>
          </div>
        </div>
      </section>

      {/* Probability Roadmap — projected price per horizon */}
      {Array.isArray(f.roadmap) && f.roadmap.length > 0 && (
        <section className="panel">
          <div className="panel-title">Probability Roadmap (projected, not guaranteed)</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            {f.roadmap.map((r: any) => (
              <div key={r.horizon}>
                <div className="stat-label">{r.horizon}</div>
                <div className={`stat-value font-mono ${r.bias === "up" ? "text-terminal-bull" : r.bias === "down" ? "text-terminal-bear" : ""}`}>
                  {fmt(r.projected)}
                </div>
                <div className="text-[10px] text-terminal-muted">{r.probability}%</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Time to Event */}
      <section className="panel">
        <div className="panel-title">Time-to-Event (estimates)</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div><div className="stat-label">Breakout ETA</div><div className="stat-value">{te.breakout?.eta_min != null ? `~${te.breakout.eta_min}m` : "—"}</div><div className="text-[10px] text-terminal-muted">conf {te.breakout?.confidence ?? "—"}%</div></div>
          <div><div className="stat-label">Profit Booking ETA</div><div className="stat-value">{te.profit_booking?.eta_min != null ? `~${te.profit_booking.eta_min}m` : "—"}</div><div className="text-[10px] text-terminal-muted">conf {te.profit_booking?.confidence ?? "—"}%</div></div>
          <div><div className="stat-label">Reversal ETA</div><div className="stat-value">{te.reversal?.eta_min != null ? `~${te.reversal.eta_min}m` : "—"}</div><div className="text-[10px] text-terminal-muted">conf {te.reversal?.confidence ?? "—"}%</div></div>
          <div><div className="stat-label">Trend Exhaustion</div><div className={`stat-value ${te.trend_exhaustion?.likely ? "text-terminal-warn" : "text-terminal-bull"}`}>{te.trend_exhaustion?.likely ? "Likely" : "Not yet"}</div><div className="text-[10px] text-terminal-muted">conf {te.trend_exhaustion?.confidence ?? "—"}%</div></div>
        </div>
      </section>
    </div>
  );
}
