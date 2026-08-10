"use client";
// ENTRY EVIDENCE BOARD (owner, 2026-08-10) — "எந்த அடிப்படையில entry வந்தாலும்
// உடனே முன்னாடி dashboard-ல தெரியுற மாதிரி": wherever price sits today on its
// opening-range fib ladder, joined against the 894-setup / 1,230-day
// historical study, visible at a glance.
//
// EVIDENCE ONLY — never a BUY/SELL call, never a second decision surface.
// The Hero card (TradeNowCard) remains the ONLY decision surface (Rule 11,
// "One Hero -> One Decision"). This board explains and locates; it never
// verdicts. The historical study's own conclusion is shown verbatim:
// preferred_level is NONE — no fib level is validated. Every historical
// number here carries its own sample size / confidence interval so a thin
// cell can never read like a strong one.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

function fmt(n: number | null | undefined, d = 2) {
  return n === null || n === undefined || Number.isNaN(n) ? "—" : n.toFixed(d);
}

export function EntryEvidenceBoard({ symbol = "NIFTY" }: { symbol?: string }) {
  const [b, setB] = useState<any>(null);
  useEffect(() => {
    const load = () => api.entryEvidence?.(symbol).then(setB).catch(() => {});
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, [symbol]);
  if (!b) return null;

  const live = b.live || {};
  const hist = b.historical || {};
  const byLevel: Record<string, any> = {};
  for (const r of hist.by_level || []) byLevel[String(r.fib_level)] = r;
  const nextLevel = live.next_level_below != null ? String(live.next_level_below) : null;
  const nextRow = nextLevel ? byLevel[nextLevel] : null;

  return (
    <section className="panel">
      <div className="panel-title flex items-center gap-2">
        <span>🎯 Entry Evidence Board</span>
        <span className="text-[10px] px-1.5 py-0.5 rounded border border-terminal-warn/50 text-terminal-warn">
          EVIDENCE ONLY
        </span>
      </div>

      <div className="text-xs text-terminal-muted mb-3 leading-relaxed">
        Where {symbol} sits today on its opening-range fib ladder, joined against{" "}
        {hist.setups_studied ?? "—"} historical setups. Never a BUY/SELL call — the
        Hero card above is the only decision. {hist.verdict?.why}
      </div>

      {!live.available ? (
        <div className="text-sm text-terminal-muted mb-3">
          <span className="font-bold">No live setup yet</span> — {live.reason}
        </div>
      ) : live.bias === "NO_BREAKOUT_YET" ? (
        <div className="text-sm text-terminal-muted mb-3">
          Opening range {fmt(live.opening_range?.low)}–{fmt(live.opening_range?.high)} formed;
          no breakout beyond it yet today.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-2 text-xs mb-3">
            <div>
              <span className="stat-label">Bias </span>
              <span className={`stat-value ${live.bias === "CALL" ? "text-terminal-bull" : "text-terminal-bear"}`}>
                {live.bias}
              </span>
            </div>
            <div>
              <span className="stat-label">Spot </span>
              <span className="stat-value font-mono">{fmt(live.spot)}</span>
            </div>
            <div>
              <span className="stat-label">OR </span>
              <span className="font-mono">{fmt(live.opening_range?.low)}–{fmt(live.opening_range?.high)}</span>
            </div>
            <div>
              <span className="stat-label">Breakout extreme </span>
              <span className="font-mono">{fmt(live.breakout_extreme)}</span>
            </div>
          </div>

          {nextLevel && (
            <div className="rounded-lg border border-terminal-border/60 p-3 mb-3">
              <div className="text-xs stat-label mb-1">NEXT FIB LEVEL BELOW (if retracement continues)</div>
              <div className="flex items-baseline gap-3 mb-2">
                <span className="text-2xl font-mono font-bold">{fmt(live.next_level_price)}</span>
                <span className="text-sm text-terminal-muted">fib {nextLevel}</span>
              </div>
              {nextRow && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 text-xs">
                  <div><span className="stat-label">Reach % </span>{fmt(nextRow.reach_pct, 1)}%</div>
                  <div>
                    <span className="stat-label">T1|touch </span>
                    {fmt(nextRow.t1_given_touch, 1)}%
                    <span className="text-terminal-muted"> [{fmt(nextRow.t1_ci?.[0], 0)}-{fmt(nextRow.t1_ci?.[1], 0)}]</span>
                  </div>
                  <div><span className="stat-label">mean R </span>{fmt(nextRow.mean_R, 3)}</div>
                  <div><span className="stat-label">n </span>{nextRow.n ?? "—"}</div>
                </div>
              )}
            </div>
          )}

          <div className="text-xs stat-label mb-1">CONFIRMATION AT CURRENT BAR</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs mb-3">
            {[
              ["Rejection bar", live.confirmation_now?.rejection_bar],
              ["VWAP supports", live.confirmation_now?.vwap_supports],
              ["Supertrend agrees", live.confirmation_now?.supertrend_agrees],
            ].map(([label, val]) => (
              <div key={label as string} className="flex items-center gap-1.5">
                <span>{val === true ? "✓" : val === false ? "✗" : "○"}</span>
                <span className="text-terminal-muted">{label}</span>
              </div>
            ))}
            <div><span className="stat-label">RSI </span>{fmt(live.confirmation_now?.rsi, 1)}</div>
            <div><span className="stat-label">ATR </span>{fmt(live.confirmation_now?.atr)}</div>
            <div>
              <span className="stat-label">Pattern </span>
              {(live.confirmation_now?.candle_patterns || []).filter(Boolean).join(", ") || "none"}
            </div>
          </div>
        </>
      )}

      <div className="text-xs stat-label mb-1">HISTORICAL EVIDENCE PER LEVEL ({hist.setups_studied ?? "—"} setups)</div>
      <table className="w-full text-xs font-mono mb-1">
        <thead>
          <tr className="stat-label text-left">
            <th className="pb-1 font-normal">Fib</th>
            <th className="pb-1 font-normal text-right">Reach%</th>
            <th className="pb-1 font-normal text-right">T1|touch [CI]</th>
            <th className="pb-1 font-normal text-right">mean R</th>
            <th className="pb-1 font-normal text-right">n</th>
          </tr>
        </thead>
        <tbody>
          {(hist.by_level || []).map((r: any) => (
            <tr
              key={r.fib_level}
              className={`border-t border-terminal-border/40 ${
                nextLevel === String(r.fib_level) ? "bg-terminal-warn/10" : ""
              }`}
            >
              <td className="py-1 text-terminal-muted">{r.fib_level}</td>
              <td className="py-1 text-right">{fmt(r.reach_pct, 1)}%</td>
              <td className="py-1 text-right">
                {fmt(r.t1_given_touch, 1)}%
                <span className="text-terminal-muted text-[10px]">
                  {" "}[{fmt(r.t1_ci?.[0], 0)}-{fmt(r.t1_ci?.[1], 0)}]
                </span>
              </td>
              <td className="py-1 text-right">{fmt(r.mean_R, 3)}</td>
              <td className="py-1 text-right text-terminal-muted">{r.n ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="text-[11px] text-terminal-muted leading-relaxed border-t border-terminal-border/40 pt-2">
        <b>No level is validated.</b> Win rate tracks R:R almost perfectly inversely; a
        data-fitted zone LOST to a plain fixed level out-of-sample. Read mean R with its
        n — a single level is a candidate, never a rule. Index points only, no costs
        modelled, not option-premium P&L. Gate: {hist.verdict?.gate}.
      </div>
    </section>
  );
}
