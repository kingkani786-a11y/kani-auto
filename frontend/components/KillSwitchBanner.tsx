"use client";
// Phase 14 — Kill Switch banner. Capital-protection veto, top of dashboard.
// Display only: it reflects the FORCE-WAIT state the backend already computed.

import { useMarket } from "@/lib/store";

export function KillSwitchBanner() {
  const { killSwitch } = useMarket();
  if (!killSwitch) return null;

  const active = killSwitch.active;
  const level = killSwitch.level || (active ? "DANGER" : "SAFE");

  // SAFE with no cautions → stay out of the way (don't clutter the view).
  if (!active && (!killSwitch.caution || killSwitch.caution.length === 0)) return null;

  const tone = active
    ? "border-terminal-bear/60 bg-terminal-bear/10"
    : "border-terminal-warn/50 bg-terminal-warn/5";
  const dot = active ? "bg-terminal-bear animate-pulse" : "bg-terminal-warn";
  const label = active ? "text-terminal-bear" : "text-terminal-warn";

  const reasons: string[] = active ? killSwitch.reasons || [] : killSwitch.caution || [];

  return (
    <div className={`panel border ${tone} py-3`}>
      {/* Layer separation: the Risk Engine blocks EXECUTION only. The
          Analysis + Opportunity engines never stop — so we say so, loudly,
          right above the block. (Owner's institutional-desk design.) */}
      <div className="flex items-center gap-2 text-[11px] font-semibold text-terminal-bull mb-2 pb-2 border-b border-terminal-border/40">
        <span className="w-2 h-2 rounded-full bg-terminal-bull animate-pulse" />
        AI ANALYSING — market read, radar, thinking & opportunities all running.
      </div>
      <div className="flex items-center gap-2 mb-1.5">
        <span className={`w-2.5 h-2.5 rounded-full ${dot}`} />
        <span className={`text-sm font-bold tracking-wider ${label}`}>
          {active ? "⚠ EXECUTION BLOCKED — new entries disabled" : `EXECUTION CAUTION — ${level}`}
        </span>
      </div>
      <ul className="text-xs text-gray-200 space-y-0.5 mb-1">
        {reasons.map((r, i) => (
          <li key={i} className="flex gap-2">
            <span className={label}>▸</span>{r}
          </li>
        ))}
      </ul>
      {killSwitch.market_closed_note && (
        <div className="text-[11px] text-terminal-warn/90 mt-1">
          🟡 {killSwitch.market_closed_note}
        </div>
      )}
      {active && killSwitch.recovery_condition && killSwitch.recovery_condition !== "—" && (
        <div className="text-[11px] text-terminal-muted mt-1.5 pt-1.5 border-t border-terminal-border/40">
          <span className="stat-label">Recovery:</span> {killSwitch.recovery_condition}
        </div>
      )}
      {active && (
        <div className="text-[11px] text-terminal-muted mt-1">
          Capital Protection active — only <b className="text-gray-200">execution</b> is held; analysis continues so you never lose visibility. Probabilities, not certainty.
        </div>
      )}
    </div>
  );
}
