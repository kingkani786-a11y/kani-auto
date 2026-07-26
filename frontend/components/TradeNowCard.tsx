"use client";
// 🟢 TRADE NOW — the ONE box a trader needs to decide in 2-3 seconds (owner
// UX request, 2026-07-21). Pure re-presentation of the Decision Contract's
// already-computed fields — no new logic, no second gate. "Radar observes,
// engine decides" — this card only makes the engine's own decision loud and
// legible. Big text, color, one screen.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BuyChecklist } from "@/components/BuyChecklist";

const GRADE_STARS: Record<string, number> = { "A+": 5, A: 4, B: 3, C: 2, D: 1 };
const stars = (n: number) => "★".repeat(n) + "☆".repeat(5 - n);

const fmt = (n: any) => (typeof n === "number" ? n.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "—");

export function TradeNowCard() {
  const [c, setC] = useState<any>(null);
  useEffect(() => {
    const load = () => api.decisionContract().then(setC).catch(() => {});
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);
  if (!c) return null;

  const buy = c.is_trade;
  const grade = c.entry_grade?.grade as string | undefined;
  const n = grade ? GRADE_STARS[grade] ?? 0 : 0;
  const tr = c.trade_readiness || {};
  const pp = c.premium_plan || {};      // option premium — what you actually pay
  const sw = c.strike_why || {};        // why this strike was selected

  const headBg = buy ? "border-terminal-bull/60 bg-terminal-bull/10" : "border-terminal-warn/40 bg-terminal-warn/5";

  // 🚦 AI Trade Light (owner, 2026-07-21) — one color, read without parsing
  // anything. Pure lookup already computed server-side over the engine's own
  // 9-state primary_action; not a second gate.
  const light = c.trade_light || { color: "RED", dot: "🔴", label: "NO TRADE" };
  const lightTone: Record<string, string> = {
    RED: "bg-terminal-bear/15 text-terminal-bear border-terminal-bear/40",
    YELLOW: "bg-terminal-warn/15 text-terminal-warn border-terminal-warn/40",
    GREEN: "bg-terminal-bull/15 text-terminal-bull border-terminal-bull/40",
    BLUE: "bg-sky-500/15 text-sky-400 border-sky-500/40",
    BLACK: "bg-white/10 text-white border-white/30",
  };

  return (
    <section className={`panel border-2 ${headBg} space-y-3`}>
      {/* ONE verdict, stated ONCE (owner 2026-07-21: "ஒரே BUY/WAIT verdict ஒரு
          இடத்தில் மட்டும்"). This card used to print the Trade Light label AND
          a separate action headline — "🔴 NO TRADE" stacked directly above
          "⏸ WAIT" — recreating inside the hero exactly the duplication that
          had just been removed between cards. The Trade Light IS the verdict. */}
      <div className={`flex items-center justify-between rounded border px-3 py-2 ${lightTone[light.color] || lightTone.RED}`}>
        <div className="flex items-center gap-2 text-xl sm:text-2xl font-bold tracking-wide">
          <span>{light.dot}</span>
          <span>{light.label}</span>
        </div>
        {grade && (
          <div className="text-right">
            <div className="text-2xl font-bold leading-none">{grade}</div>
            <div className="text-xs tracking-wide opacity-80">{stars(n)}</div>
          </div>
        )}
      </div>

      {/* BEST STRIKE (owner, 2026-07-21) — the exact instrument the engine
          gated, shown only once a trade is actually armed (honest: never
          invented for a WAIT state). */}
      {c.best_strike?.strike && (
        <div className="text-center text-sm font-bold text-white tracking-wide border-y border-terminal-border py-1">
          BEST STRIKE — {c.best_strike.strike} {c.best_strike.type}
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
        <div title="Declared confidence blend — not a validated/backtested probability.">
          <div className="text-lg font-bold tabular-nums text-white">{c.confidence != null ? `${c.confidence}%` : "—"}</div>
          <div className="text-[10px] text-terminal-muted">Confidence</div>
        </div>
        <div>
          <div className="text-lg font-bold tabular-nums text-white">{c.reward_risk ? `1:${c.reward_risk}` : "—"}</div>
          <div className="text-[10px] text-terminal-muted">R:R</div>
        </div>
        <div>
          <div className={`text-lg font-bold ${tr.risk_approved ? "text-terminal-bull" : "text-terminal-bear"}`}>{tr.risk_approved ? "YES" : "NO"}</div>
          <div className="text-[10px] text-terminal-muted">Risk Approved</div>
        </div>
        <div>
          <div className="text-lg font-bold tabular-nums text-white">{c.ledger_total != null ? `${c.ledger_total}` : "—"}</div>
          <div className="text-[10px] text-terminal-muted">Evidence /100</div>
        </div>
      </div>

      {/* PREMIUM PLAN — what an option buyer actually pays (owner 2026-07-21).
          This row previously rendered exit_plan, which holds UNDERLYING INDEX
          levels: a "7850 PE" card showed "Entry 7,927 · SL 7,944" in NIFTY
          points, readable as the option price. strike_selector publishes both
          separately; the index levels are now demoted to small print and
          explicitly labelled "Underlying".
          Shown whenever a plan exists — NOT only on a BUY — because the owner
          needs to see the opportunity the engine is refusing, not just the
          ones it approves. It is labelled as the engine's plan, never as an
          instruction; nothing here authorises a trade. */}
      {pp?.entry != null && (
        <div className="border-t border-terminal-border pt-2">
          <div className="flex items-baseline justify-between mb-1">
            <span className="text-[10px] font-semibold text-terminal-muted uppercase tracking-wide">
              Premium plan{pp.strike ? ` — ${pp.strike} ${pp.type}` : ""}
            </span>
            {!buy && <span className="text-[10px] text-terminal-warn">engine has NOT approved this</span>}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center">
            <div><div className="text-sm font-semibold tabular-nums text-white">₹{fmt(pp.entry)}</div><div className="text-[9px] text-terminal-muted">Entry</div></div>
            <div><div className="text-sm font-semibold tabular-nums text-terminal-bear">₹{fmt(pp.stop_loss)}</div><div className="text-[9px] text-terminal-muted">SL</div></div>
            <div><div className="text-sm font-semibold tabular-nums text-terminal-bull">₹{fmt(pp.target1)}</div><div className="text-[9px] text-terminal-muted">T1</div></div>
            <div><div className="text-sm font-semibold tabular-nums text-terminal-bull">₹{fmt(pp.target2)}</div><div className="text-[9px] text-terminal-muted">T2</div></div>
            <div><div className="text-sm font-semibold tabular-nums text-terminal-bull">₹{fmt(pp.target3)}</div><div className="text-[9px] text-terminal-muted">T3</div></div>
          </div>
          {pp.underlying?.stop_loss != null && (
            <div className="text-[10px] text-terminal-muted mt-1">
              Underlying (index): SL {fmt(pp.underlying.stop_loss)} · T1 {fmt(pp.underlying.target1)} · T2 {fmt(pp.underlying.target2)} · T3 {fmt(pp.underlying.target3)}
            </div>
          )}
          {sw?.selection_score != null && (
            <div className="text-[10px] text-terminal-muted mt-0.5">
              Why this strike: score {sw.selection_score}
              {sw.spread_pct != null && ` · spread ${sw.spread_pct}%`}
              {sw.prob_itm_pct != null && ` · ITM ${Math.round(sw.prob_itm_pct)}%`}
              {sw.delta != null && ` · Δ ${sw.delta}`}
              {sw.iv != null && ` · IV ${sw.iv}`}
            </div>
          )}
        </div>
      )}

      {/* Alignment chips REMOVED 2026-07-21: Wave / Premium / Risk Gate are
          all three already rows in the BUY checklist directly below, so this
          rendered the same three facts twice, adjacently. */}
      {/* BUY Checklist — rendered from the contract's shared `buy_checklist`
          object, the SAME one AI Thinking renders (owner 2026-07-21). ○ means
          NOT MEASURED (e.g. Structure, pending the Market Structure Engine) —
          deliberately not a ✗, because "can't see it" ≠ "it failed". */}
      <BuyChecklist c={c} />
      {c.why?.[0] && <div className="text-[11px] text-terminal-muted">{c.why[0]}</div>}

      <div className="text-[10px] text-terminal-muted border-t border-terminal-border pt-1.5">
        Move probability (Big/Medium/Small) not yet available — needs more black-box history. Radar observes, the engine decides; this card only explains the decision already made.
      </div>
    </section>
  );
}
