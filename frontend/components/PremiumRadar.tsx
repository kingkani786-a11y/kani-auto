"use client";
// ⚡ Premium Radar — the option BUYER's live view (Execution Visibility Upgrade).
// Always-on ATM±N tracking so a premium's BIRTH → EXPANSION → RUNNER is visible
// from the first minute. Three macro-phases (🟢 Building / 🟠 Runner Building /
// 🔴 Runner Confirmed), Live Premium Leaders, and a per-strike price ladder.
// Deterministic (Dhan LTP/Volume/OI); NOT the decision path; runner score is a
// declared blend, not a calibrated probability. The engine gate decides trades.

import { Fragment, useEffect, useState } from "react";
import { api } from "@/lib/api";

const stars = (n: number) => "★".repeat(n) + "☆".repeat(5 - n);
const phaseTone: Record<string, string> = {
  BUILDING: "text-terminal-bull", RUNNER_BUILDING: "text-terminal-warn",
  RUNNER_CONFIRMED: "text-terminal-bear",
};

export function PremiumRadar() {
  const [d, setD] = useState<any>(null);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => {
    const load = () => api.premiumRadar(8).then(setD).catch(() => {});
    load(); const t = setInterval(load, 4000); return () => clearInterval(t);
  }, []);

  const movers: any[] = (d?.movers || []).filter((m: any) => m.runner_score > 0);
  const leaders = (d?.leaders?.length ? d.leaders : movers).slice(0, 3);
  const watchlist: any[] = d?.watchlist || [];
  const missed: any[] = d?.missed || [];
  const chk = (b: boolean) => (b ? "☑" : "☐");

  return (
    <section className="panel space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">⚡ Premium Radar <span className="text-[10px] text-terminal-muted">(option buyer · live)</span></h2>
        {d && <span className="text-[10px] text-terminal-muted">{d.tracked} strikes tracked</span>}
      </div>

      {!d ? <div className="text-xs text-terminal-muted">Loading…</div>
        : movers.length === 0 ? (
          <div className="text-xs text-terminal-muted">
            No premium movement yet. Fills live during market hours — each strike's
            premium, velocity, phase and runner score appear as a move is born.
          </div>
        ) : (
          <>
            {/* 🔥 LIVE PREMIUM LEADERS — which option is running right now */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {leaders.map((m: any, i: number) => (
                <div key={i} className="border border-terminal-border rounded p-2">
                  <div className="flex items-center justify-between">
                    <span className="text-white text-sm">{["①","②","③"][i]} {m.strike} {m.type}</span>
                    <span className="text-terminal-warn text-[11px]">{stars(m.stars)}</span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-lg font-bold tabular-nums">₹{m.premium}</span>
                    <span className={`text-xs tabular-nums ${m.rise_pct >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>{m.rise_pct >= 0 ? "+" : ""}{m.rise_pct}%</span>
                  </div>
                  <div className={`text-[11px] ${phaseTone[m.phase?.code] || ""}`}>{m.phase?.dot} {m.phase?.label} · {m.runner_score}</div>
                </div>
              ))}
            </div>

            {/* ⏳ NEXT OPPORTUNITY — building strikes to watch before they run */}
            {watchlist.length > 0 && (
              <div className="border border-terminal-border rounded p-2 space-y-1">
                <div className="text-[11px] font-semibold text-terminal-bull">⏳ WATCHLIST — building (watch before it runs)</div>
                {watchlist.map((m, i) => (
                  <div key={i} className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px]">
                    <span className="text-white">{m.strike} {m.type}</span>
                    <span className="tabular-nums">₹{m.premium} <span className="text-terminal-bull">+{m.rise_pct}%</span></span>
                    <span className="text-terminal-muted">Runner {m.runner_score}</span>
                    <span className="text-terminal-muted">{chk(m.checklist.premium_rising)} Premium {chk(m.checklist.velocity)} Velocity {chk(m.checklist.volume)} Volume {chk(m.checklist.oi)} OI</span>
                  </div>
                ))}
              </div>
            )}

            {/* 🏁 BIG MOVERS (ran ≥30%) — each tagged by whether the radar
                actually caught it EARLY, caught it LATE, or truly missed it.
                This reconciles with the Capture Score (only ✗ = a real miss). */}
            {missed.length > 0 && (
              <div className="border border-terminal-border rounded p-2 space-y-1">
                <div className="text-[11px] font-semibold text-white">🏁 BIG MOVERS TODAY <span className="text-terminal-muted font-normal">(ran ≥30% — caught or missed)</span></div>
                {missed.map((m, i) => {
                  const badge = m.caught === "EARLY"
                    ? { t: "✓ caught early", c: "text-terminal-bull border-terminal-bull/40" }
                    : m.caught === "LATE"
                    ? { t: "◐ caught late", c: "text-terminal-warn border-terminal-warn/40" }
                    : { t: "✗ missed", c: "text-terminal-bear border-terminal-bear/40" };
                  return (
                    <div key={i} className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px]">
                      <span className={`px-1 rounded border ${badge.c}`}>{badge.t}</span>
                      <span className="text-white">{m.strike} {m.type}</span>
                      <span className="tabular-nums">₹{m.from_low} → ₹{m.peak_premium}</span>
                      <span className="text-terminal-muted tabular-nums">+{m.missed_points} pts ({m.peak_rise_pct}%)</span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* full table — click a row for its premium ladder */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="text-terminal-muted text-[10px]">
                  <tr className="text-left"><th className="py-1">Strike</th><th>Premium</th><th>▲%</th><th>Vel</th><th>Accel</th><th>OI%</th><th>Phase</th><th>Runner</th></tr>
                </thead>
                <tbody>
                  {movers.map((m, i) => {
                    const key = `${m.strike}${m.type}`;
                    return (
                      <Fragment key={key}>
                        <tr className="border-t border-terminal-border cursor-pointer hover:bg-terminal-border/20" onClick={() => setOpen(open === key ? null : key)}>
                          <td className="py-1 text-white whitespace-nowrap">{m.strike} {m.type}</td>
                          <td className="tabular-nums">₹{m.premium}</td>
                          <td className={`tabular-nums ${m.rise_pct >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>{m.rise_pct >= 0 ? "+" : ""}{m.rise_pct}%</td>
                          <td className="tabular-nums">{m.velocity}</td>
                          <td className={`tabular-nums ${m.accel > 0 ? "text-terminal-bull" : m.accel < 0 ? "text-terminal-bear" : ""}`}>{m.accel > 0 ? "+" : ""}{m.accel}</td>
                          <td className="tabular-nums">{m.oi_pct >= 0 ? "+" : ""}{m.oi_pct}%</td>
                          <td className={phaseTone[m.phase?.code] || ""}>{m.phase?.dot}</td>
                          <td className="whitespace-nowrap"><span className="text-terminal-warn">{stars(m.stars)}</span> <span className="text-terminal-muted tabular-nums">{m.runner_score}</span></td>
                        </tr>
                        {open === key && m.ladder && (
                          <tr className="bg-terminal-border/10">
                            <td colSpan={8} className="py-1.5 px-2">
                              <div className="flex flex-wrap items-center gap-1 text-[11px]">
                                <span className="text-terminal-muted mr-1">Ladder:</span>
                                {m.ladder.map((s: any, j: number) => (
                                  <span key={j} className="whitespace-nowrap">
                                    <span className="text-terminal-muted">{s.t}</span> <span className="text-white tabular-nums">₹{s.p}</span>
                                    {j < m.ladder.length - 1 && <span className="text-terminal-muted mx-1">→</span>}
                                  </span>
                                ))}
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      <div className="text-[10px] text-terminal-muted">
        Phase 🟢 Building (0–30%) · 🟠 Runner Building (30–70%) · 🔴 Runner Confirmed (70%+). Runner score is a declared signal blend, not a calibrated win-probability. Radar observes; the engine decides trades.
      </div>
    </section>
  );
}
