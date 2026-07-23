"use client";
// SECTION 1 + 24 — Execution Control Center + Final Execution Gate. One unified
// panel: the gated final decision + the mandatory conditions and any blocking
// reasons. Derivation-only display (does not mutate the decision pipeline).

import { useMarket } from "@/lib/store";
import { displayLabel, displayReasons } from "@/lib/labels";

const stTone = (s: string) =>
  s === "PASS" ? "text-terminal-bull" : s === "FAIL" ? "text-terminal-bear" : "text-terminal-warn";

export function ExecutionControlCenter() {
  const { decision } = useMarket();
  const d: any = decision || {};
  const eg = d.execution_gate;
  const di = d.intelligence_synthesis || {};
  const sm = d.signal_maturity || {};
  const ec = d.entry_checklist || {};
  if (!eg?.ready) return null;

  const final = eg.final_decision;
  const finalTone = final?.startsWith("BUY") ? "text-terminal-bull"
    : final === "NO TRADE" ? "text-terminal-bear" : "text-terminal-warn";

  return (
    <div className="panel border-terminal-accent/40">
      <div className="panel-title">Execution Control Center — Final Gate</div>

      {/* one decision, key metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 mb-3">
        <div>
          <div className="stat-label">Final Decision</div>
          <div className={`stat-value text-lg ${finalTone}`}>{final}</div>
        </div>
        <div><div className="stat-label">Fire Score</div><div className="stat-value">{ec.fire_score ?? "—"}{ec.fire_band ? ` ${""}` : ""}</div></div>
        <div><div className="stat-label">Entry Grade</div><div className="stat-value">{(di.trade_quality || {}).grade ?? "—"}</div></div>
        <div><div className="stat-label">Confidence</div><div className="stat-value">{di.conviction ?? "—"}%</div></div>
        <div><div className="stat-label">Maturity</div><div className="stat-value">{sm.maturity_score ?? "—"}</div></div>
        <div><div className="stat-label">Gate</div><div className={`stat-value ${eg.gate_passed ? "text-terminal-bull" : "text-terminal-bear"}`}>{eg.gate_passed ? "PASS" : "BLOCKED"}</div></div>
      </div>

      {/* blocking reasons (Section 24) */}
      {!eg.gate_passed && eg.blocking_reasons?.length > 0 && (
        <div className="mb-2 text-xs">
          <span className="text-terminal-bear font-semibold">Blocked by:</span>{" "}
          <span className="text-gray-300">{displayReasons(eg.blocking_reasons).join(" · ")}</span>
          {/* RC1.16.6 — Incident #001 explainability: each blocker's own
              ledger track record — "AI saw it; the rule refused, and this is
              that rule's history." Research display only, never an override. */}
          {Array.isArray(eg.blocker_research) && eg.blocker_research.length > 0 && (
            <div className="mt-1 space-y-0.5">
              {eg.blocker_research.map((r: any, i: number) => (
                <div key={i} className="text-[11px] text-terminal-muted">
                  ▸ {displayLabel(r.module)}:{" "}
                  {r.status === "NO DATA YET" ? "no settled verdicts yet" : (
                    <>
                      saved {r.saved_pct}% / missed {r.missed_pct}%
                      {r.solo_missed_pct != null && <> · solo-missed {r.solo_missed_pct}%</>}
                      {" "}· {r.blocked} blocks · {r.status}
                    </>
                  )}
                  <span className="text-terminal-accent"> · research only — no override</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {!eg.gate_passed && eg.blocking_reasons?.length === 0 && eg.waiting_on?.length > 0 && (
        <div className="mb-2 text-[11px] text-terminal-muted">Waiting on: {eg.waiting_on.map(displayLabel).join(", ")}</div>
      )}

      {/* mandatory conditions grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-4 gap-y-1">
        {(eg.conditions || []).map((c: any) => (
          <div key={c.name} className="flex items-center justify-between text-[11px] border-b border-terminal-border/20 py-0.5">
            <span className="text-terminal-muted">{displayLabel(c.name)}</span>
            <span className={`font-bold ${stTone(c.status)}`}>{c.status}</span>
          </div>
        ))}
      </div>
      <div className="text-[10px] text-terminal-muted mt-2">{eg.note}</div>
    </div>
  );
}
