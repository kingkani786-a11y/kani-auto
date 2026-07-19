"use client";
// 📜 DECISION CONTRACT — V2.1's unifier. One card, one language: the action,
// its WHY (Rule 11), invalidations and exit plan live together. BUY or WAIT,
// the contract always explains itself. Derived; the user executes manually.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function DecisionContract() {
  const [c, setC] = useState<any>(null);
  useEffect(() => {
    const load = () => api.decisionContract().then(setC).catch(() => {});
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);
  if (!c) return null;

  const buy = c.is_trade;
  const head = buy
    ? { t: `🟢 ${c.action}`, cls: "text-terminal-bull border-terminal-bull/50 bg-terminal-bull/10" }
    : { t: `⏸ ${c.action || "WAIT"}`, cls: "text-terminal-warn border-terminal-warn/40 bg-terminal-warn/5" };

  return (
    <section className="panel space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">📜 Decision Contract <span className="text-[10px] text-terminal-muted">(entry · hold · exit — one logic)</span></h2>
        <span className={`text-[12px] font-bold px-2 py-0.5 rounded border ${head.cls}`}>{head.t}</span>
      </div>

      {/* Rule 11 — explain before execute (BUY and WAIT alike) */}
      <div>
        <div className="text-[10px] font-semibold text-terminal-muted uppercase tracking-wide mb-0.5">{buy ? "Why buy" : "Why wait"}</div>
        <ul className="text-[11px] text-gray-200 space-y-0.5">
          {(c.why || []).map((w: string, i: number) => (
            <li key={i} className="flex gap-1.5"><span className={buy ? "text-terminal-bull" : "text-terminal-warn"}>▸</span>{w}</li>
          ))}
        </ul>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center border-t border-terminal-border pt-2">
        <div><div className="text-sm font-semibold tabular-nums text-white">{c.confidence ?? "—"}{typeof c.confidence === "number" ? "%" : ""}</div><div className="text-[9px] text-terminal-muted">Confidence</div></div>
        <div><div className="text-sm font-semibold tabular-nums text-white">{c.reward_risk ? `1:${c.reward_risk}` : "—"}</div><div className="text-[9px] text-terminal-muted">R:R</div></div>
        <div><div className="text-sm font-semibold text-white truncate" title={String(c.expected_move ?? "")}>{c.expected_move ?? "—"}</div><div className="text-[9px] text-terminal-muted">Expected move</div></div>
        <div><div className="text-sm font-semibold tabular-nums text-white">{c.entry ?? "—"}</div><div className="text-[9px] text-terminal-muted">Entry ref</div></div>
      </div>

      {/* Invalidations — the pre-stated contract terms */}
      <div className="border border-terminal-bear/30 rounded p-2">
        <div className="text-[10px] font-semibold text-terminal-bear uppercase tracking-wide mb-0.5">Invalidation — exit IF</div>
        <ul className="text-[11px] text-gray-200 space-y-0.5">
          {(c.invalidations || []).map((v: string, i: number) => (
            <li key={i} className="flex gap-1.5"><span className="text-terminal-bear">✕</span>{v}</li>
          ))}
        </ul>
        <div className="text-[10px] text-terminal-muted mt-1">{c.instruction}</div>
      </div>

      {buy && (
        <div className="text-[11px] text-terminal-muted">
          Exit plan: SL <b className="text-white">{c.exit_plan?.stop_loss ?? "—"}</b>
          {c.exit_plan?.target1 ? <> · T1 <b className="text-white">{c.exit_plan.target1}</b></> : null}
          {c.exit_plan?.trail ? <> · {c.exit_plan.trail}</> : null}
        </div>
      )}

      <div className="text-[10px] text-terminal-muted">{c.note}</div>
    </section>
  );
}
