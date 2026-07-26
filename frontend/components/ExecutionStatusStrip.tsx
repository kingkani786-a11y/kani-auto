"use client";
// EXECUTION STATUS STRIP — Step 2 (Hero Dashboard Finalization, 2026-07-26).
// Minimal always-visible execution-gate summary for the top-of-page zone:
// Final Decision + Gate PASS/BLOCKED only. The full conditions grid and
// blocking-reasons/blocker-research detail stay in ExecutionControlCenter
// (Advanced) — this strip never duplicates that content, and never shows a
// "why" (Block Reason Hero already owns WHY HERE, right below this strip).
// Rule 11: this reads execution_gate directly, same source the Hero Card's
// own decisionContract is built from — it does not compute anything new.

import { useMarket } from "@/lib/store";

export function ExecutionStatusStrip() {
  const { decision } = useMarket();
  const eg = (decision as any)?.execution_gate;
  if (!eg?.ready) return null;

  const final = eg.final_decision;
  const finalTone = final?.startsWith("BUY") ? "text-terminal-bull"
    : final === "NO TRADE" ? "text-terminal-bear" : "text-terminal-warn";

  return (
    <div className="panel border border-terminal-border/60 py-2 flex items-center gap-4">
      <span className="text-[10px] text-terminal-muted uppercase tracking-wide">Execution Status</span>
      <span className={`text-sm font-bold ${finalTone}`}>{final}</span>
      <span className={`text-[11px] font-bold px-2 py-0.5 rounded ${eg.gate_passed ? "text-terminal-bull border border-terminal-bull/50" : "text-terminal-bear border border-terminal-bear/50"}`}>
        Gate {eg.gate_passed ? "PASS" : "BLOCKED"}
      </span>
    </div>
  );
}
