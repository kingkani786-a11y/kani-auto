"use client";
// ⚙ EXECUTION DETAIL — candle clock, position sizing, entry window, signal
// truth. Trimmed 2026-07-21 (owner: "மூன்றும் ஒரே விஷயத்தைச் சொல்கின்றன" —
// this card, Trade Light, and Decision Contract were each independently
// re-announcing the same BUY/WAIT/AVOID verdict in different words, which
// is exactly the "no single Master Decision" confusion she flagged). The
// decision itself now lives in ONE place — TradeNowCard's Trade Light, fed
// by decision_contract.py, which as of this same pass now ALSO reconciles
// against execution_gate (this card's own source) so the two can no longer
// silently disagree. This card no longer restates the verdict — it only
// adds execution detail a trader wouldn't get from the hero: candle time
// left, position size/risk ₹, entry-window countdown, signal truth %.

import { useEffect, useState } from "react";
import { useMarket } from "@/lib/store";

const MANDATORY = ["Trend", "Structure", "OI", "Institutional", "Risk"];
const TF_SEC: Record<string, number> = { "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800, "1H": 3600 };
const TF_LABEL: Record<string, string> = { "1m": "1 Minute", "3m": "3 Minute", "5m": "5 Minute", "15m": "15 Minute", "30m": "30 Minute", "1H": "1 Hour" };

export function LiveCandleCommand({ tf = "5m" }: { tf?: string }) {
  const { decision, layers, wsOk } = useMarket();
  const d: any = decision || {};
  const L: any = layers || {};
  const gate = d.execution_gate;
  const ec = d.entry_checklist || {};
  const sm = d.signal_maturity || {};
  const et = sm.entry_trigger || {};
  const mp = d.market_path || {};

  // live ticking: entry-window countdown + candle clock (display math only)
  const [now, setNow] = useState(Date.now());
  const [winBase, setWinBase] = useState<{ at: number; sec: number | null }>({ at: Date.now(), sec: null });
  useEffect(() => { setWinBase({ at: Date.now(), sec: et.window_remaining_sec ?? null }); }, [et.window_remaining_sec]);
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);

  if (!gate?.ready || !sm?.ready) return null;

  const tfs = TF_SEC[tf] || 300;
  const elapsed = Math.floor(now / 1000) % tfs;
  const candleProgress = Math.round((elapsed / tfs) * 100);
  const candleLeft = tfs - elapsed;
  const mmss = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  const winLeft = winBase.sec == null ? null : Math.max(0, winBase.sec - Math.floor((now - winBase.at) / 1000));

  // ONE traffic light + ONE action (from the authoritative gate — no new logic)
  const fd = gate.final_decision;
  const isBuy = fd === "BUY CALL" || fd === "BUY PUT";
  const hardBlocked = (gate.blocking_reasons || []).some((r: string) =>
    /kill switch|safe mode|data quality/i.test(r)) || et.status === "ENTRY CLOSED";
  const light = isBuy ? "READY" : hardBlocked ? "AVOID"
    : ["ARMED", "READY", "FIRE NOW"].includes(et.status) ? "PREPARE" : "WAIT";

  const rows = (ec.checklist || []).filter((c: any) => MANDATORY.includes(c.item));
  const power = Math.round(((ec.fire_score ?? 0) + (sm.maturity_score ?? 0)) / 2);
  const bias = L.trend?.direction === "BULL" ? "Bullish" : L.trend?.direction === "BEAR" ? "Bearish" : "Neutral";
  const strength = rows.find((c: any) => c.item === "Trend")?.score ?? "—";
  const od = mp.overall_direction || {};
  const fmt = (n?: number | null) => (n == null ? "—" : Number(n).toLocaleString("en-IN"));

  return (
    <div className={`panel border-2 ${light === "READY" ? "border-terminal-bull/60" : light === "AVOID" ? "border-terminal-bear/50" : "border-terminal-warn/40"} py-4`}>
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <h2 className="text-sm font-semibold text-white">⚙ Execution Detail <span className="text-[10px] text-terminal-muted">(decision is the Trade Light above — this is supporting detail only)</span></h2>
        {(() => {
          const t = d.ai_trust;
          return t?.score != null ? (
            <span title={t.note} className={`px-2 py-1 rounded-md text-[11px] font-bold border ${
              t.score >= 80 ? "border-terminal-bull/50 text-terminal-bull"
              : t.score >= 60 ? "border-terminal-warn/50 text-terminal-warn"
              : "border-terminal-bear/50 text-terminal-bear"}`}>
              TRUST {t.score}%
            </span>
          ) : null;
        })()}
      </div>

      {/* current candle: tf · bias · strength · candle countdown + progress */}
      <div className="flex items-center gap-3 mb-2 text-[12px] flex-wrap">
        <span className="text-terminal-muted">{TF_LABEL[tf] || tf} Candle</span>
        <span className={bias === "Bullish" ? "text-terminal-bull" : bias === "Bearish" ? "text-terminal-bear" : "text-terminal-muted"}>{bias}</span>
        <span className="text-terminal-muted">Strength <span className="font-mono text-gray-200">{strength}%</span></span>
        <span className="ml-auto font-mono">{mmss(candleLeft)} left</span>
      </div>
      <div className="h-1.5 rounded-full bg-terminal-bg overflow-hidden mb-3">
        <div className="h-full bg-terminal-accent" style={{ width: `${candleProgress}%` }} />
      </div>

      {/* 3 — V20 AI Master Score (ONE score; components stay in Research) */}
      {(() => {
        const ms = d.master_score;
        const val = ms?.score ?? power;
        const col = val >= 80 ? "bg-terminal-bull" : val >= 60 ? "bg-yellow-500"
          : val >= 40 ? "bg-orange-500" : "bg-terminal-bear";
        return (
          <div className="flex items-center gap-3 mb-3" title={ms?.note}>
            <span className="stat-label w-24">AI Master Score</span>
            <div className="flex-1 h-3 rounded-full bg-terminal-bg overflow-hidden">
              <div className={`h-full ${col}`} style={{ width: `${val}%` }} />
            </div>
            <span className="font-mono text-sm text-right">{val}</span>
            {ms?.stars ? <span className="text-[11px]">{"★".repeat(ms.stars)}{"☆".repeat(5 - ms.stars)}</span> : null}
          </div>
        );
      })()}

      {/* V12 §10 position sizing (decision-support; from Settings capital+risk%) —
          unique to this card, not shown anywhere else. */}
      {(() => {
        const ps: any = d.position_sizing;
        if (!ps?.ready || !isBuy) return null;
        return ps.qty > 0 ? (
          <div className="text-[13px] mb-3">
            <span className="stat-label mr-2">Qty</span>
            <span className="font-mono font-bold">{ps.lots != null ? `${ps.lots} lot${ps.lots > 1 ? "s" : ""} (${ps.qty})` : ps.qty}</span>
            <span className="text-terminal-muted"> · Risk ₹{fmt(ps.risk_amount)} ({ps.risk_pct}%) · Capital req ₹{fmt(ps.capital_required)}</span>
          </div>
        ) : ps.per_lot_risk ? (
          <div className="text-[13px] mb-3 text-terminal-bear">
            ⚠ 1 lot risks ₹{fmt(ps.per_lot_risk)} — above your {ps.risk_pct}% budget. Reduce risk or skip.
          </div>
        ) : null;
      })()}

      {/* Entry Window + Bull/Bear/Range — unique to this card (Best Strike and
          the pass/fail Confirmations list now live once, in TradeNowCard). */}
      <div className="grid grid-cols-2 gap-3 mb-3 text-[12px]">
        <div><div className="stat-label">Entry Window</div>
          <div className={`font-mono ${winLeft !== null && winLeft <= 0 ? "text-terminal-bear font-bold" : ""}`}>
            {winLeft == null ? "—" : winLeft <= 0 ? "ENTRY CLOSED" : `${mmss(winLeft)} left`}</div></div>
        <div><div className="stat-label">Bull / Bear / Range</div>
          <div className="font-mono"><span className="text-terminal-bull">{od.up ?? "—"}</span> / <span className="text-terminal-bear">{od.down ?? "—"}</span> / <span className="text-terminal-warn">{od.range ?? "—"}</span></div></div>
      </div>

      {/* V40 §1 — signal truth split, front and centre (from signal_maturity) */}
      {sm.false_signal_probability != null && !hardBlocked && (
        <div className="text-[11px] mt-1.5">
          <span className="stat-label mr-2">Signal truth</span>
          <span className="text-terminal-bull font-mono">true {100 - sm.false_signal_probability}%</span>
          <span className="text-terminal-muted"> / </span>
          <span className={`font-mono ${sm.false_signal_probability >= 35 ? "text-terminal-bear" : "text-terminal-muted"}`}>
            false {sm.false_signal_probability}%</span>
          <span className="text-terminal-muted/70"> · calibrates against real outcomes as validation grows</span>
        </div>
      )}

      {/* V22 — AI-is-working line: real state only (WS + checklist counts) */}
      <div className="text-[10px] text-terminal-muted mt-2 flex items-center gap-1.5">
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${wsOk ? "bg-terminal-bull animate-pulse" : "bg-terminal-bear"}`} />
        {wsOk
          ? `AI working live — ${ec.passed ?? 0}/${ec.total ?? 0} layers confirmed, re-evaluating every cycle`
          : "Live link down — data may be stale"}
      </div>
    </div>
  );
}
