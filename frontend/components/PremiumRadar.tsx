"use client";
// ⚡ Premium Radar — the option BUYER's live view (Execution Visibility Upgrade).
// Always-on ATM±N tracking so a premium's BIRTH → EXPANSION → RUNNER is visible
// from the first minute. Deterministic (Dhan LTP/Volume/OI); NOT the decision
// path; runner score is a declared blend, not a calibrated probability. The
// engine gate decides trades.
//
// Zone-grouped (owner UX review, 2026-07-21): the old layout showed the same
// strike in Leaders + Watchlist + the raw table (2-3x each) — "இதனால்
// மனிதருக்கு குழப்பம்" (this confuses a human). Now each strike appears once,
// bucketed by its own runner_score into 🟢 BUY / 🟠 PREPARE / 🟡 WATCH zones
// (⚪ Ignore collapsed to a count) — same thresholds as her own worked
// examples (Runner 82→BUY, 52→PREPARE, 31→WATCH). Zone is a pure relabel of
// runner_score, computed server-side; it groups the opportunity list, it is
// NOT a trade authorization — only Decision Contract + Risk Approval say BUY.

import { Fragment, useEffect, useState } from "react";
import { api } from "@/lib/api";

const stars = (n: number) => "★".repeat(n) + "☆".repeat(5 - n);
const phaseTone: Record<string, string> = {
  BUILDING: "text-terminal-bull", RUNNER_BUILDING: "text-terminal-warn",
  RUNNER_CONFIRMED: "text-terminal-bear",
};

function ZoneStrikeRow({ m }: { m: any }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] py-0.5">
      <span className="text-white font-semibold">{m.strike} {m.type}</span>
      <span className="tabular-nums">₹{m.premium} <span className={m.rise_pct >= 0 ? "text-terminal-bull" : "text-terminal-bear"}>{m.rise_pct >= 0 ? "+" : ""}{m.rise_pct}%</span></span>
      <span className="text-terminal-warn">{stars(m.stars)} <span className="text-terminal-muted">{m.star_label}</span></span>
      <span className="text-terminal-muted">Runner {m.runner_score} · {m.runner_band}</span>
      <span className={phaseTone[m.phase?.code] || ""}>{m.phase?.dot} {m.phase?.label}</span>
      {m.coil?.state && m.coil.state !== "NONE" && (
        <span className="text-terminal-accent">{m.coil.dot} {m.coil.state}</span>
      )}
    </div>
  );
}

const ZONE_STYLE: Record<string, string> = {
  buy: "border-terminal-bull/40", prepare: "border-terminal-warn/40", watch: "border-terminal-warn/20",
};
const ZONE_TITLE: Record<string, string> = {
  buy: "🟢 BUY ZONE", prepare: "🟠 PREPARE ZONE", watch: "🟡 WATCH ZONE",
};

export function PremiumRadar({ advanced = false }: { advanced?: boolean }) {
  const [d, setD] = useState<any>(null);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => {
    const load = () => api.premiumRadar(8).then(setD).catch(() => {});
    load(); const t = setInterval(load, 4000); return () => clearInterval(t);
  }, []);

  const movers: any[] = (d?.movers || []).filter((m: any) => m.runner_score > 0);
  const zones = d?.zones || { buy: [], prepare: [], watch: [], ignore_count: 0 };
  const missed: any[] = d?.missed || [];

  return (
    <section className="panel space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">⚡ Premium Radar <span className="text-[10px] text-terminal-muted">(option buyer · live)</span></h2>
        {d && <span className="text-[10px] text-terminal-muted">{d.tracked} strikes tracked</span>}
      </div>

      {/* Flow so nobody mistakes an early signal for a buy signal */}
      <div className="text-[10px] text-terminal-muted flex flex-wrap items-center gap-1">
        Early Warning <span className="text-terminal-accent">→</span> Spring <span className="text-terminal-accent">→</span> Hot Now <span className="text-terminal-accent">→</span> BUY Candidate <span className="text-terminal-accent">→</span> Engine Verification <span className="text-terminal-accent">→</span> <span className="text-terminal-bull font-semibold">BUY</span>
      </div>

      {!d ? <div className="text-xs text-terminal-muted">Loading…</div>
        : movers.length === 0 ? (
          <div className="text-xs text-terminal-muted">
            No premium movement yet. Fills live during market hours — each strike's
            premium, velocity, phase and runner score appear as a move is born.
          </div>
        ) : (
          <>
            {/* 🟢🟠🟡 Zone-grouped opportunity list — one card per strike */}
            {(["buy", "prepare", "watch"] as const).map((z) =>
              zones[z]?.length > 0 ? (
                <div key={z} className={`border rounded p-2 space-y-0.5 ${ZONE_STYLE[z]}`}>
                  <div className="text-[11px] font-semibold text-white">{ZONE_TITLE[z]} <span className="text-terminal-muted font-normal">({zones[z].length})</span></div>
                  {zones[z].map((m: any, i: number) => <ZoneStrikeRow key={i} m={m} />)}
                </div>
              ) : null
            )}
            {zones.ignore_count > 0 && (
              <div className="text-[11px] text-terminal-muted">⚪ Ignore — {zones.ignore_count} strike{zones.ignore_count === 1 ? "" : "s"} with no meaningful move (collapsed)</div>
            )}

            {/* 🏁 BIG MOVERS (ran ≥30%) — each tagged by whether the radar
                actually caught it EARLY, caught it LATE, or truly missed it.
                This reconciles with the Capture Score (only ✗ = a real miss). */}
            {missed.length > 0 && (
              <div className="border border-terminal-border rounded p-2 space-y-1">
                <div className="text-[11px] font-semibold text-white">🏁 BIG MOVERS TODAY <span className="text-terminal-muted font-normal">(ran ≥30% — badge = latest run; day totals in 🏆 Capture Score)</span></div>
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
                      <span className="text-terminal-muted tabular-nums">+{m.missed_points} pts ({m.peak_rise_pct > 300 && m.from_low > 0 ? `${(m.peak_premium / m.from_low).toFixed(1)}×` : `${m.peak_rise_pct}%`})</span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* full diagnostic table — click a row for its premium ladder.
                Engineer tool (raw vel/accel/OI% columns) → Advanced only;
                the Zone cards above already carry what a trader needs. */}
            {advanced && <div className="overflow-x-auto">
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
            </div>}
          </>
        )}
      <div className="text-[10px] text-terminal-muted">
        Phase 🟢 Building (0–30%) · 🟠 Growing (30–70%) · 🔴 Exploding (70%+). Runner score is a declared signal blend, not a calibrated win-probability. Radar observes; the engine decides trades.
      </div>
    </section>
  );
}
