"use client";
// DECISION CHAIN — P1 "Cause -> Consequence collapse" (owner, 2026-08-03).
//
// The problem this exists to fix: Kill Switch, Safe Mode and the Execution
// Gate's own "Data Quality" row each independently derive from the SAME
// underlying facts (data_quality.report().overall, broker cooldown) but
// phrase them differently ("Data quality POOR — feed inconsistent" vs
// "DATA: quality collapsed (POOR)" vs a bare gate row). A trader reading all
// three sees what looks like three separate problems. It's one problem,
// echoed three times. This groups by the stable `reason_tags`/`trigger_tags`
// kill_switch.py and safe_mode.py now emit (additive fields, same index as
// their existing `reasons`/`triggers` strings) and shows each root cause
// ONCE, with a note of which panels are echoing it — then the one final
// decision.
//
// Deliberately narrow scope: this only renders when a SYSTEM-level veto
// (Kill Switch or Safe Mode) is actually active. It does not duplicate
// BlockReasonHero, which explains why a SPECIFIC candidate move was blocked
// (h.reason, singular, tied to a strike) and stays quiet on a calm market
// even if a system veto is active. This panel is the opposite: it is quiet
// exactly when BlockReasonHero might be loud (ordinary per-trade WAIT), and
// only speaks up when the cause is systemic. No new gate, no new logic —
// pure re-grouping of kill_switch/safe_mode/execution_gate's own output.

import { useMarket } from "@/lib/store";

const TAG_LABEL: Record<string, string> = {
  DATA_QUALITY: "Data Quality",
  BROKER_COOLDOWN: "Broker Rate-Limit Cooldown",
  DATA_COMPLETENESS: "Data Completeness",
  CALIBRATION: "Calibration",
  CONSECUTIVE_LOSSES: "Consecutive Losses",
  BROKER_HEALTH: "Broker Health",
  SIGNAL_STALL: "Signal Engine Stall",
};

interface Cause {
  tag: string;
  label: string;
  texts: string[];
  seenIn: string[];
}

export function DecisionChain() {
  const { killSwitch, safeMode, decision } = useMarket();
  const ks = killSwitch as any;
  const sm = safeMode as any;
  const eg = (decision as any)?.execution_gate;

  // Only speak up for a SYSTEM-level veto — see file header for why this is
  // deliberately narrower than "any WAIT".
  if (!ks?.active && !sm?.active) return null;

  const causes = new Map<string, Cause>();
  const touch = (tag: string, text: string, source: string) => {
    const c = causes.get(tag) || { tag, label: TAG_LABEL[tag] || tag, texts: [], seenIn: [] };
    if (!c.texts.includes(text)) c.texts.push(text);
    if (!c.seenIn.includes(source)) c.seenIn.push(source);
    causes.set(tag, c);
  };

  const ksReasons: string[] = ks?.reasons || [];
  const ksTags: string[] = ks?.reason_tags || [];
  ksTags.forEach((tag, i) => touch(tag, ksReasons[i], "Kill Switch"));

  const smTriggers: string[] = sm?.triggers || [];
  const smTags: string[] = sm?.trigger_tags || [];
  smTags.forEach((tag, i) => touch(tag, smTriggers[i], "Safe Mode"));

  // The gate's own "Data Quality" condition row is a THIRD independent voice
  // for the same DATA_QUALITY fact when it isn't passing.
  const dqRow = (eg?.conditions || []).find((c: any) => c.name === "Data Quality");
  if (dqRow && dqRow.status !== "PASS") {
    touch("DATA_QUALITY", dqRow.reason || "feed quality", "Gate");
  }

  const causeList = Array.from(causes.values());
  const echoCount = causeList.reduce((n, c) => n + c.seenIn.length, 0);
  const final = eg?.final_decision || "WAIT";

  return (
    <div className="panel border border-terminal-bear/40 py-2.5 space-y-1.5 text-[11px]">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="font-bold tracking-wider text-terminal-bear">WHY {final}</span>
        <span className="text-terminal-muted">
          {causeList.length} root cause{causeList.length === 1 ? "" : "s"}
          {" -> "}{echoCount} panel echo{echoCount === 1 ? "" : "es"}{" -> "}1 decision
        </span>
      </div>
      <div className="space-y-1">
        {causeList.map((c) => (
          <div key={c.tag} className="flex items-start gap-2 flex-wrap">
            <span className="text-terminal-bear mt-0.5">●</span>
            <span className="font-semibold text-gray-100">{c.label}</span>
            <span className="text-terminal-muted">— {c.texts[0]}</span>
            {c.seenIn.length > 1 && (
              <span className="text-terminal-warn text-[10px]">
                (shown in {c.seenIn.join(" + ")} — same fact)
              </span>
            )}
          </div>
        ))}
      </div>
      <div className="text-[10px] text-terminal-muted pt-1 border-t border-terminal-border/40">
        Groups Kill Switch, Safe Mode and the Gate's own Data Quality row by
        their shared root cause — no new gate, no new logic. Per-trade
        blocking reasons for a specific candidate stay in Block Reason Hero.
      </div>
    </div>
  );
}
