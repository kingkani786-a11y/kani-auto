"use client";
// V16 — 🚀 SCALPING TOOL card (Trading mode, per user's dashboard mockup).
// Shows the strike the AI is watching + entry details WHILE PREPARING, so the
// trader knows in advance which strike and at what levels entry will trigger.
// Display-only: preparing levels/strike come from the same backend math as a
// live signal (signal.preparing_levels + strike_queue). Never a BUY by itself.

import { useEffect, useRef } from "react";
import { useMarket } from "@/lib/store";

// Regime playbook — same static advice map used by Research's EntryFirstDeck
const REGIME_PLAY: Record<string, { best: string; avoid: string }> = {
  TRENDING: { best: "Trend pullback entries", avoid: "Counter-trend fades" },
  HIGH_MOMENTUM: { best: "Momentum / breakout", avoid: "Mean-reversion" },
  RANGE_BOUND: { best: "Fade extremes", avoid: "Breakout chasing" },
  VOLATILE: { best: "Wait / reduce size", avoid: "Aggressive scalping" },
  LOW_MOMENTUM: { best: "Wait", avoid: "Forcing trades" },
  EXPIRY_PINNING: { best: "Wait", avoid: "Aggressive scalping" },
};
const STAGES = ["PREPARING", "READY", "ENTRY", "RUNNING", "EXIT"];

export function ScalpingTool() {
  const { decision, signal, layers, exitIntel } = useMarket();
  const d: any = decision || {};
  const s: any = signal || {};
  const L: any = layers || {};

  const gate = d.execution_gate || {};
  const isBuy = gate.final_decision === "BUY CALL" || gate.final_decision === "BUY PUT";
  // live plan when trading, preparing plan while the gate holds
  const lv: any = isBuy
    ? { entry: d.entry, stop_loss: d.stop_loss, target1: d.target1, target2: d.target2, target3: d.target3, direction: s.direction }
    : s.preparing_levels;
  if (!lv?.entry) return null;

  const sq = (d.strike_queue || [])[0];
  const ec = d.entry_checklist || {};
  const prob = L.probability || {};
  const ps = d.position_sizing || {};

  // V20 ② — premium momentum: observed change of the displayed premium over
  // the last ~12 updates (client-side; resets when the best strike changes)
  const premHist = useRef<{ key: string; vals: number[] }>({ key: "", vals: [] });
  useEffect(() => {
    if (sq?.premium == null) return;
    const key = `${sq.strike}${sq.type}`;
    if (premHist.current.key !== key) premHist.current = { key, vals: [] };
    const v = premHist.current.vals;
    if (v[v.length - 1] !== sq.premium) { v.push(Number(sq.premium)); if (v.length > 12) v.shift(); }
  }, [sq?.premium, sq?.strike, sq?.type]);
  const pv = premHist.current.vals;
  const premChg = pv.length >= 3 && pv[0] ? ((pv[pv.length - 1] - pv[0]) / pv[0]) * 100 : null;
  const runner = (L.intelligence as any)?.expansion?.runner_probability;

  // V20 — volatility band from India VIX (standard bands; hidden if VIX absent)
  const vix = L.vix_correlation?.vix;
  const volBand = vix == null ? null : vix < 12 ? "LOW" : vix < 15 ? "MEDIUM" : vix < 20 ? "HIGH" : "EXTREME";
  // V20 — liquidity pressure from the existing order-flow score (0-100 buy-side)
  const flow = Number(L.order_flow?.score);
  // V20 — trade-life stage from existing states (RUNNING only with a live trade)
  const etStatus = (d.signal_maturity?.entry_trigger || {}).status;
  const inTrade = Boolean((exitIntel as any)?.in_trade || (exitIntel as any)?.active);
  const stage = inTrade ? "RUNNING" : isBuy ? "ENTRY"
    : ["ARMED", "READY", "FIRE NOW"].includes(etStatus) ? "READY" : "PREPARING";
  const play = REGIME_PLAY[L.regime?.regime as string];
  const volRow = (ec.checklist || []).find((c: any) => c.item === "Volume Profile");
  const status = isBuy ? "READY" : "PREPARING";
  const dir = lv.direction === "BULL" ? "BULLISH" : lv.direction === "BEAR" ? "BEARISH" : "";
  const pts = (t?: number) => (t == null || lv.entry == null ? "" : ` (${Math.abs(t - lv.entry).toFixed(1)} pts)`);
  const fmt = (n?: number | null) => (n == null ? "—" : Number(n).toLocaleString("en-IN"));

  return (
    <div className={`panel border ${isBuy ? "border-terminal-bull/50" : "border-terminal-accent/40"} py-3`}>
      <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
        <span className="font-bold tracking-wider text-terminal-accent">🚀 SCALPING TOOL</span>
        <span className="flex items-center gap-2">
          {(() => {
            // V19 §2 — trade style suited to the tape; §9 — risk grade
            const style = (d.execution_card || {}).trade_style;
            const styleReason = (d.execution_card || {}).style_reason;
            const cap = (L.capital_protection || {}).category;
            return (
              <>
                {style ? (
                  <span title={styleReason} className="px-2 py-0.5 rounded text-[11px] font-bold border border-terminal-accent/50 text-terminal-accent">
                    {style}
                  </span>
                ) : null}
                {cap ? (
                  <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${
                    cap === "SAFE" || cap === "LOW" ? "border-terminal-bull/50 text-terminal-bull"
                    : cap === "CRITICAL" || cap === "HIGH" ? "border-terminal-bear/50 text-terminal-bear"
                    : "border-terminal-warn/50 text-terminal-warn"}`}>
                    RISK {cap}
                  </span>
                ) : null}
                {volBand ? (
                  <span title={`India VIX ${vix}`} className={`px-2 py-0.5 rounded text-[11px] font-bold border ${
                    volBand === "LOW" ? "border-terminal-bull/50 text-terminal-bull"
                    : volBand === "MEDIUM" ? "border-terminal-warn/50 text-terminal-warn"
                    : "border-terminal-bear/50 text-terminal-bear"}`}>
                    VOL {volBand}
                  </span>
                ) : null}
              </>
            );
          })()}
          <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${isBuy ? "bg-terminal-bull text-black" : "border border-terminal-warn/50 text-terminal-warn"}`}>
            {status}
          </span>
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* left — best strike (or underlying levels for chain-less instruments) */}
        <div>
          <div className="stat-label mb-0.5">Best Strike {isBuy ? "" : "(preparing)"}</div>
          {sq ? (
            <>
              <div className={`font-mono font-black text-3xl leading-tight ${lv.direction === "BULL" ? "text-terminal-bull" : "text-terminal-bear"}`}>
                {sq.strike} {sq.type}
                {sq.moneyness ? <span className="ml-2 align-middle text-[11px] font-bold px-1.5 py-0.5 rounded border border-terminal-border text-terminal-muted">{sq.moneyness}</span> : null}
              </div>
              <div className="text-[12px] text-terminal-muted mt-1">
                Premium <span className="font-mono text-gray-200">₹{sq.premium ?? "—"}</span>
                {premChg != null && Math.abs(premChg) >= 0.3 ? (
                  <span className={`font-mono ${premChg > 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
                    {" "}{premChg > 0 ? "↑" : "↓"} {premChg > 0 ? "+" : ""}{premChg.toFixed(1)}%
                  </span>
                ) : null}
                {volRow?.status === "PASS" ? <span className="text-terminal-bull"> · Vol ↑</span> : null}
                {sq.prob_itm ? <> · ITM <span className="font-mono text-gray-200">{Math.round(sq.prob_itm)}%</span></> : null}
                {ps.lot_size ? <> · Lot <span className="font-mono text-gray-200">{ps.lot_size}</span></> : null}
                {sq.spread_pct != null ? <> · Spread <span className="font-mono text-gray-200">{sq.spread_pct}%</span></> : null}
              </div>
              {sq.premium_sl != null && (
                <div className="text-[12px] mt-1.5">
                  <span className="stat-label mr-1">Premium Plan</span>
                  <span className="font-mono">₹{sq.premium} → </span>
                  <span className="font-mono text-terminal-bear">SL ₹{sq.premium_sl}</span>
                  <span className="font-mono text-terminal-bull"> · T1 ₹{sq.premium_t1} · T2 ₹{sq.premium_t2} · T3 ₹{sq.premium_t3}</span>
                  {(() => {
                    const pf: any = (d as any).premium_forecast;
                    const p60 = pf?.ready ? pf.forecasts?.["60m"]?.premium : null;
                    return p60 ? <span className="text-terminal-muted"> · exp (60m) ₹{p60}</span> : null;
                  })()}
                </div>
              )}
              {/* V25 — Smart Premium line: observed trend + forecast expansion/decay/IV */}
              {(() => {
                const pf: any = (d as any).premium_forecast;
                const trend = premChg == null ? null
                  : premChg >= 2 ? "↑ fast" : premChg >= 0.5 ? "↑ medium"
                  : premChg <= -0.5 ? "↓ falling" : "flat";
                if (!trend && !pf?.ready) return null;
                return (
                  <div className="text-[11px] text-terminal-muted mt-1">
                    {trend ? <>Premium trend <span className={premChg! >= 0.5 ? "text-terminal-bull" : premChg! <= -0.5 ? "text-terminal-bear" : "text-gray-300"}>{trend}</span></> : null}
                    {pf?.ready ? <> · exp expansion <span className="text-terminal-bull">+{pf.expected_expansion_pct}%</span> · theta/decay <span className="text-terminal-bear">−{pf.expected_decay_pct}%</span> · IV-crush risk {pf.iv_crush_risk}%</> : null}
                  </div>
                );
              })()}
            </>
          ) : (
            <div className="text-[12px] text-terminal-muted">
              No option chain for this instrument — underlying levels below.
            </div>
          )}
          {dir && (
            <div className={`inline-block mt-2 px-2 py-1 rounded text-[11px] font-bold border ${
              lv.direction === "BULL" ? "border-terminal-bull/50 text-terminal-bull" : "border-terminal-bear/50 text-terminal-bear"}`}>
              {dir} SETUP
            </div>
          )}
        </div>

        {/* right — entry details */}
        <div className="text-[12px] space-y-1">
          <div className="stat-label">Entry Details {isBuy ? "" : "(AI preparing)"}</div>
          <div className="flex justify-between"><span className="text-terminal-muted">Entry</span><span className="font-mono">{fmt(lv.entry)}</span></div>
          <div className="flex justify-between"><span className="text-terminal-muted">Stop Loss</span><span className="font-mono text-terminal-bear">{fmt(lv.stop_loss)}{pts(lv.stop_loss)}</span></div>
          <div className="flex justify-between"><span className="text-terminal-muted">T1 / T2 / T3</span>
            <span className="font-mono text-terminal-bull">{fmt(lv.target1)} / {fmt(lv.target2)} / {fmt(lv.target3)}</span></div>
          {prob.expected_move != null && (
            <div className="flex justify-between"><span className="text-terminal-muted">Expected Move</span>
              <span className="font-mono">{prob.expected_move} pts</span></div>)}
          {prob.prob_success != null && (
            <div className="flex justify-between"><span className="text-terminal-muted">Probability</span>
              <span className="font-mono">{prob.prob_success}%</span></div>)}
          {s.dynamic_confidence != null && (
            <div className="flex justify-between"><span className="text-terminal-muted">Confidence</span>
              <span className="font-mono">{s.dynamic_confidence}%</span></div>)}
          {lv.reward_risk ? (
            <div className="flex justify-between"><span className="text-terminal-muted">R : R</span>
              <span className="font-mono">1 : {lv.reward_risk}</span></div>) : null}
          {runner != null ? (
            <div className="flex justify-between"><span className="text-terminal-muted">Runner prob</span>
              <span className="font-mono">{Math.round(runner)}%</span></div>) : null}
        </div>
      </div>

      {/* V20 — trade-life stage + playbook + liquidity pressure (one row set) */}
      <div className="mt-2 pt-2 border-t border-terminal-border/50 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px]">
        <span>
          {STAGES.map((s, i) => (
            <span key={s}>
              <span className={s === stage ? "font-bold text-terminal-accent" : "text-terminal-muted/60"}>{s}</span>
              {i < STAGES.length - 1 ? <span className="text-terminal-muted/40"> → </span> : null}
            </span>
          ))}
        </span>
        {Number.isFinite(flow) && (
          <span className="flex items-center gap-1.5">
            <span className="stat-label">Flow</span>
            <span className="inline-block w-16 h-1.5 rounded-full bg-terminal-bear/40 overflow-hidden align-middle">
              <span className="block h-full bg-terminal-bull" style={{ width: `${flow}%` }} />
            </span>
            <span className="font-mono text-terminal-bull">{Math.round(flow)}%</span>
            <span className="text-terminal-muted">buy</span>
          </span>
        )}
        {play && (
          <span className="text-terminal-muted">
            Playbook: <span className="text-gray-200">{play.best}</span> · avoid {play.avoid.toLowerCase()}
          </span>
        )}
        {/* V23 — regime meter: one-glance regime + strength (regime.score) */}
        {L.regime?.score != null && (
          <span className="flex items-center gap-1.5">
            <span className="stat-label">{String(L.regime.regime ?? "").replace(/_/g, " ")}</span>
            <span className="inline-block w-16 h-1.5 rounded-full bg-terminal-bg overflow-hidden align-middle">
              <span className={`block h-full ${L.regime.score >= 70 ? "bg-terminal-bull" : L.regime.score >= 45 ? "bg-terminal-warn" : "bg-terminal-bear"}`}
                style={{ width: `${Math.round(L.regime.score)}%` }} />
            </span>
            <span className="font-mono">{Math.round(L.regime.score)}%</span>
          </span>
        )}
      </div>

      {/* V17 — position size, known in advance (from Settings capital + risk%) */}
      {ps.qty > 0 && (
        <div className="mt-2 pt-2 border-t border-terminal-border/50 text-[12px]">
          <span className="stat-label mr-2">Qty</span>
          <span className="font-mono font-bold">{ps.lots != null ? `${ps.lots} lot${ps.lots > 1 ? "s" : ""} (${ps.qty})` : ps.qty}</span>
          <span className="text-terminal-muted"> · Risk ₹{Number(ps.risk_amount).toLocaleString("en-IN")} ({ps.risk_pct}%)
            · Capital req ₹{Number(ps.capital_required).toLocaleString("en-IN")}
            {ps.expected_profit_t1 != null ? <> · at T1 <span className="text-terminal-bull">+₹{Number(ps.expected_profit_t1).toLocaleString("en-IN")}</span></> : null}
            {ps.preparing ? " · if this setup fires" : ""}</span>
        </div>
      )}
      {ps.ready && ps.qty === 0 && ps.per_lot_risk ? (
        <div className="mt-2 pt-2 border-t border-terminal-border/50 text-[12px] text-terminal-bear">
          ⚠ 1 lot risks ₹{Number(ps.per_lot_risk).toLocaleString("en-IN")} — above your {ps.risk_pct}% budget. Reduce risk or skip.
        </div>
      ) : null}

      {/* V30 — Commander Brief: the whole plan as ONE sentence (real fields only) */}
      {sq?.premium_sl != null && (
        <div className="mt-2 pt-2 border-t border-terminal-border/50 text-[12px] text-gray-200">
          🎖 <span className="font-semibold">{isBuy ? "BUY" : "PLAN"}: {sq.strike} {sq.type} @ ₹{sq.premium}</span>
          <span className="text-terminal-muted"> → book ~70% at T1 </span><span className="font-mono text-terminal-bull">₹{sq.premium_t1}</span>
          <span className="text-terminal-muted"> → runner to T3 </span><span className="font-mono text-terminal-bull">₹{sq.premium_t3}</span>
          <span className="text-terminal-muted"> · SL </span><span className="font-mono text-terminal-bear">₹{sq.premium_sl}</span>
          {ps.lots ? <span className="text-terminal-muted"> · {ps.lots} lot{ps.lots > 1 ? "s" : ""}</span> : null}
          {!isBuy ? <span className="text-terminal-warn"> · fires only if the gate opens</span> : null}
        </div>
      )}

      {/* V30 — today's risk budget (facts from paper trades) */}
      {(() => {
        const rb: any = (d as any).risk_budget;
        return rb && rb.trades_today > 0 ? (
          <div className="mt-1 text-[11px] text-terminal-muted">
            Today: {rb.trades_today} trade{rb.trades_today > 1 ? "s" : ""} · realized{" "}
            <span className={`font-mono ${rb.realized_pnl >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
              {rb.realized_pnl >= 0 ? "+" : ""}₹{Number(rb.realized_pnl).toLocaleString("en-IN")} ({rb.realized_pct}%)
            </span>
          </div>
        ) : null;
      })()}

      {/* V22 — Entry Queue: NOW / NEXT / WATCH from live strike statuses */}
      {(d.strike_queue || []).length > 0 && (() => {
        const q = d.strike_queue as any[];
        const now = q.find((x) => x.status === "READY");
        const rest = q.filter((x) => x !== now);
        const label = (x: any) => `${x.strike} ${x.type}`;
        return (
          <div className="mt-2 pt-2 border-t border-terminal-border/50 text-[11px]">
            <span className="stat-label mr-2">Entry Queue</span>
            <span className="font-mono">
              NOW <span className={now ? "text-terminal-bull font-bold" : "text-terminal-muted"}>{now ? label(now) : "none"}</span>
              {rest[0] ? <span className="text-terminal-muted"> · NEXT <span className="text-gray-200">{label(rest[0])}</span></span> : null}
              {rest[1] ? <span className="text-terminal-muted"> · WATCH <span className="text-gray-200">{label(rest[1])}</span></span> : null}
            </span>
          </div>
        );
      })()}

      {/* V17 — Strike Watch: top-3 preparing strikes */}
      {(d.strike_queue || []).length > 1 && (
        <div className="mt-2 pt-2 border-t border-terminal-border/50 text-[11px]">
          <span className="stat-label mr-2">Strike Watch</span>
          {(d.strike_queue || []).slice(0, 5).map((q: any, i: number) => (
            <span key={i} className="font-mono mr-4">
              <span className={q.type === "CE" ? "text-terminal-bull" : "text-terminal-bear"}>{q.strike} {q.type}</span>
              <span> {"🔥".repeat(Math.max(1, Math.min(5, q.stars || 1)))}</span>
              <span className="text-terminal-muted"> {q.moneyness ?? ""}{q.score != null ? ` · AI ${Math.round(q.score)}` : ""} · {q.status?.toLowerCase()}{q.prob_itm ? ` · ITM ${Math.round(q.prob_itm)}%` : ""}</span>
            </span>
          ))}
        </div>
      )}

      {/* AI will buy when — the exact missing confirmations (honest triggers) */}
      {!isBuy && (ec.waiting_for || []).length > 0 && (
        <div className="mt-2 pt-2 border-t border-terminal-border/50 text-[11px]">
          <span className="stat-label mr-2">AI will buy when</span>
          {(ec.waiting_for || []).slice(0, 4).map((w: string, i: number) => (
            <span key={i} className="text-terminal-warn font-mono mr-3">○ {w}</span>
          ))}
        </div>
      )}
    </div>
  );
}
