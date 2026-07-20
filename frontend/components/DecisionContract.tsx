"use client";
// 📜 DECISION CONTRACT — V2.1's unifier: entry/hold/exit as one object.
// Trimmed 2026-07-21 (owner follow-up): TradeNowCard (Level 1) already shows
// grade/confidence/RR/risk/entry-SL-targets/why — showing all of it again
// here was "Paragraph"-heavy duplication. This card's job now is ONLY the
// four fields she asked for: ENTRY / STOP / TARGET / EXIT IF. Still derived,
// still read-only — the user executes manually, the system never places orders.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const fmt = (n: any) => (typeof n === "number" ? n.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "—");

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
  const exitIf = (c.invalidations || []).find((v: string) => !v.startsWith("Kill Switch")) || c.invalidations?.[0];

  return (
    <section className="panel space-y-2">
      <div className="flex items-center justify-between">
        {/* No verdict badge here (owner 2026-07-21: one verdict, one place).
            This card said "⏸ WAIT" while the hero said "🔴 NO TRADE" — the same
            state in two different words on one screen. The hero owns the
            verdict; this card owns the entry/stop/target contract only. */}
        <h2 className="text-sm font-semibold text-white">📜 Decision Contract</h2>
      </div>

      {buy ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
          <div><div className="text-sm font-semibold tabular-nums text-white">{fmt(c.entry)}</div><div className="text-[9px] text-terminal-muted">ENTRY</div></div>
          <div><div className="text-sm font-semibold tabular-nums text-terminal-bear">{fmt(c.exit_plan?.stop_loss)}</div><div className="text-[9px] text-terminal-muted">STOP</div></div>
          <div><div className="text-sm font-semibold tabular-nums text-terminal-bull">{fmt(c.exit_plan?.target1)}</div><div className="text-[9px] text-terminal-muted">TARGET</div></div>
          <div className="col-span-2 sm:col-span-1"><div className="text-[11px] font-semibold text-white truncate" title={exitIf}>{exitIf || "—"}</div><div className="text-[9px] text-terminal-muted">EXIT IF</div></div>
        </div>
      ) : (
        // Deliberately does NOT repeat the hero's reason line — on a WAIT the
        // dashboard was printing "No published reason — engine idle" twice,
        // once here and once in Trade Now (owner 2026-07-21: one verdict, one
        // place). There is no entry/stop/target to contract when standing aside.
        <div className="text-xs text-terminal-muted">No active contract — entry, stop and targets appear when the engine arms a trade.</div>
      )}
    </section>
  );
}
