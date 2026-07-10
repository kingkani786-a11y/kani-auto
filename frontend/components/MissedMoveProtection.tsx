"use client";
// MISSED MOVE PROTECTION — owner-ordered (Incident #001 follow-up):
// the MODE opportunity layer's UI face. Shows live move alerts NEXT TO the
// gate's current state, so a building move is visible even while the
// Decision Layer says WAIT. Pure consumer — reads the alert feed and the
// execution gate; computes nothing (One Source → Many Consumers).
import { useMarket } from "@/lib/store";

const TIER_TONE: Record<string, string> = {
  WATCH: "text-terminal-warn",
  STRONG: "text-terminal-warn",
  MOMENTUM: "text-terminal-accent",
  BREAKOUT: "text-terminal-bull",
  EXPANSION: "text-terminal-bull",
};

export function MissedMoveProtection() {
  const { alerts, decision } = useMarket();
  const moves = (alerts || []).filter((a: any) => a.kind === "MOVE").slice(0, 5);
  const eg = (decision as any)?.execution_gate || {};
  const gate = eg.gate_passed ? "OPEN" : eg.ready ? "WAIT" : "—";
  const blocker = (eg.blocking_reasons || [])[0];

  if (moves.length === 0) return null;   // calm until the opportunity layer speaks

  return (
    <div className="panel border-terminal-warn/40">
      <div className="flex items-baseline justify-between">
        <div className="panel-title">🛰 MISSED MOVE PROTECTION</div>
        <div className="text-[11px] text-terminal-muted">
          opportunity layer · gate decides separately
        </div>
      </div>
      <div className="mt-2 space-y-1.5">
        {moves.map((a: any) => (
          <div key={a.id} className="text-xs flex flex-wrap items-baseline gap-x-2">
            <span className={`font-bold ${TIER_TONE[(a.title || "").split(":")[0]?.replace("🔥 ", "")] ?? "text-terminal-warn"}`}>
              {a.title?.replace("🔥 ", "")}
            </span>
            <span className="text-terminal-muted">{a.body?.split(" · Opportunity layer")[0]}</span>
            <span className="text-terminal-muted">· {a.ts?.split(" ")[1] ?? a.ts}</span>
          </div>
        ))}
      </div>
      <div className="mt-2 pt-2 border-t border-terminal-border/30 text-[11px] flex flex-wrap gap-x-4">
        <span><span className="text-terminal-muted">Entry Gate </span>
          <span className={eg.gate_passed ? "text-terminal-bull font-bold" : "text-terminal-warn font-bold"}>{gate}</span></span>
        {!eg.gate_passed && blocker && (
          <span><span className="text-terminal-muted">Reason </span>{blocker}</span>
        )}
        <span className="text-terminal-muted">
          Move detected without entry ⇒ it lands in the missed-winner / verdict ledger automatically.
        </span>
      </div>
    </div>
  );
}
