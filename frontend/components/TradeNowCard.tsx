"use client";
// 🟢 TRADE NOW — the ONE box a trader needs to decide in 2-3 seconds (owner
// UX request, 2026-07-21). Pure re-presentation of the Decision Contract's
// already-computed fields — no new logic, no second gate. "Radar observes,
// engine decides" — this card only makes the engine's own decision loud and
// legible. Big text, color, one screen.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

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

  const headColor = buy ? "text-terminal-bull" : "text-terminal-warn";
  const headBg = buy ? "border-terminal-bull/60 bg-terminal-bull/10" : "border-terminal-warn/40 bg-terminal-warn/5";
  const headIcon = buy ? "🟢" : c.action === "EXIT" ? "🔴" : "⏸";

  return (
    <section className={`panel border-2 ${headBg} space-y-3`}>
      <div className="flex items-center justify-between">
        <div className="text-xl sm:text-2xl font-bold flex items-center gap-2">
          <span>{headIcon}</span>
          <span className={headColor}>{c.action || "WAIT"}</span>
        </div>
        {grade && (
          <div className="text-right">
            <div className={`text-2xl font-bold ${n >= 4 ? "text-terminal-bull" : n === 3 ? "text-terminal-warn" : "text-terminal-bear"}`}>{grade}</div>
            <div className="text-xs text-terminal-warn tracking-wide">{stars(n)}</div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
        <div>
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

      {buy && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center border-t border-terminal-border pt-2">
          <div><div className="text-sm font-semibold tabular-nums text-white">{fmt(c.entry)}</div><div className="text-[9px] text-terminal-muted">Entry</div></div>
          <div><div className="text-sm font-semibold tabular-nums text-terminal-bear">{fmt(c.exit_plan?.stop_loss)}</div><div className="text-[9px] text-terminal-muted">SL</div></div>
          <div><div className="text-sm font-semibold tabular-nums text-terminal-bull">{fmt(c.exit_plan?.target1)}</div><div className="text-[9px] text-terminal-muted">T1</div></div>
          <div><div className="text-sm font-semibold tabular-nums text-terminal-bull">{fmt(c.exit_plan?.target2)}</div><div className="text-[9px] text-terminal-muted">T2</div></div>
          <div><div className="text-sm font-semibold tabular-nums text-terminal-bull">{fmt(c.exit_plan?.target3)}</div><div className="text-[9px] text-terminal-muted">T3</div></div>
        </div>
      )}

      {/* Alignment checklist — informational only, NOT a second gate */}
      <div className="flex flex-wrap gap-2 text-[11px] border-t border-terminal-border pt-2">
        <span className={`px-1.5 py-0.5 rounded border ${tr.wave_direction ? "text-terminal-bull border-terminal-bull/40" : "text-terminal-muted border-terminal-border"}`}>
          {tr.wave_direction ? "🌊" : "○"} Wave {tr.wave_direction ? tr.wave_direction.toUpperCase() : "—"}
        </span>
        <span className={`px-1.5 py-0.5 rounded border ${tr.premium_strength === "Strong" ? "text-terminal-bull border-terminal-bull/40" : tr.premium_strength === "Moderate" ? "text-terminal-warn border-terminal-warn/40" : "text-terminal-muted border-terminal-border"}`}>
          {tr.premium_strength ? "⚡" : "○"} Premium {tr.premium_strength || "—"}
        </span>
        <span className={`px-1.5 py-0.5 rounded border ${tr.risk_approved ? "text-terminal-bull border-terminal-bull/40" : "text-terminal-bear border-terminal-bear/40"}`}>
          {tr.risk_approved ? "✓" : "✕"} Risk Gate
        </span>
      </div>

      <div>
        <div className="text-[10px] font-semibold text-terminal-muted uppercase tracking-wide mb-0.5">{buy ? "Reason" : "Why not"}</div>
        <ul className="text-xs text-gray-200 space-y-0.5">
          {(c.why || []).slice(0, 5).map((w: string, i: number) => (
            <li key={i} className="flex gap-1.5"><span className={buy ? "text-terminal-bull" : "text-terminal-warn"}>{buy ? "✓" : "▸"}</span>{w}</li>
          ))}
        </ul>
      </div>

      <div className="text-[10px] text-terminal-muted border-t border-terminal-border pt-1.5">
        Move probability (Big/Medium/Small) not yet available — needs more black-box history. Radar observes, the engine decides; this card only explains the decision already made.
      </div>
    </section>
  );
}
