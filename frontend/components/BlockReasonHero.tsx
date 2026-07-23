"use client";
// BLOCK REASON HERO (owner, 2026-07-23, item #2 — most-requested feature).
// "MOVE DETECTED / ENTRY BLOCKED / WHY" instead of a bare NO TRADE — the
// highest-visual-priority card, top of dashboard. Pure re-presentation of
// decision_contract.py's block_reason_hero (itself just eg.blocking_reasons,
// the gate's own verdict) — no new gate, no new logic, no second decision.
// Only the DISPLAY label is renamed (Kill Switch -> Execution Lock, item #3);
// the backend reason string stays in its raw form until this last step.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { displayReason } from "@/lib/labels";

export function BlockReasonHero() {
  const [c, setC] = useState<any>(null);
  useEffect(() => {
    const load = () => api.decisionContract().then(setC).catch(() => {});
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  const h = c?.block_reason_hero;
  if (!h?.active) return null;   // quiet market, nothing moving -> no hero, not a permanent banner

  return (
    <div className="panel border-2 border-terminal-warn/60 bg-terminal-warn/5 space-y-1.5">
      <div className="flex items-center gap-2 text-sm font-bold text-terminal-warn tracking-wide">
        <span>🔥</span>
        <span>MOVE DETECTED: {h.strike} {h.type}</span>
      </div>
      <div className="text-lg font-bold text-terminal-bear tracking-wider">⛔ ENTRY BLOCKED</div>
      <div className="text-xs text-gray-200">
        <span className="text-terminal-muted">Reason:</span> {displayReason(h.reason) || "—"}
      </div>
      <div className="flex items-center gap-4 text-[11px] pt-1 border-t border-terminal-border/40">
        <span className={h.execution_lock === "ACTIVE" ? "text-terminal-bear font-semibold" : "text-terminal-bull"}>
          Execution Lock: {h.execution_lock}
        </span>
        <span className="text-terminal-muted">
          Manual Entry Available: {h.manual_entry_available ? "Yes" : "No"}
        </span>
      </div>
    </div>
  );
}
