"use client";
// Phase 14 — Execution Lock banner (owner, 2026-07-23, item #3: renamed from
// "Kill Switch" for display only — the internal `killSwitch` state/identifier,
// and every backend field name under it, are UNCHANGED; see lib/labels.ts).
// Capital-protection veto, top of dashboard. Display only: it reflects the
// FORCE-WAIT state the backend already computed.

import { useMarket } from "@/lib/store";
import { displayReasons } from "@/lib/labels";

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

  const reasons: string[] = displayReasons(active ? killSwitch.reasons : killSwitch.caution);

  return (
    <div className={`panel border ${tone} py-3`}>
      {active ? (
        // Exact owner-specified banner (2026-07-23): the layer-separation
        // proof stated as a plain status grid, not prose — "Analysis LIVE /
        // Radar LIVE / AI LIVE / Execution BLOCKED" is the Two-Layer Law
        // (155/155 episodes recorded 2026-07-22 while this was active all day).
        <div className="mb-2 pb-2 border-b border-terminal-border/40">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-terminal-bear animate-pulse" />
            <span className="text-sm font-bold tracking-wider text-terminal-bear">
              🔴 EXECUTION LOCK ACTIVE
            </span>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[11px] font-semibold pl-4">
            <div className="text-terminal-bull">Analysis&nbsp; : LIVE</div>
            <div className="text-terminal-bull">Radar&nbsp;&nbsp;&nbsp;&nbsp; : LIVE</div>
            <div className="text-terminal-bull">AI&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; : LIVE</div>
            <div className="text-terminal-bear">Execution: BLOCKED</div>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-[11px] font-semibold text-terminal-bull mb-2 pb-2 border-b border-terminal-border/40">
          <span className="w-2 h-2 rounded-full bg-terminal-bull animate-pulse" />
          AI ANALYSING — market read, radar, thinking & opportunities all running.
        </div>
      )}
      {!active && (
        <div className="flex items-center gap-2 mb-1.5">
          <span className={`w-2.5 h-2.5 rounded-full ${dot}`} />
          <span className={`text-sm font-bold tracking-wider ${label}`}>
            EXECUTION CAUTION — {level}
          </span>
        </div>
      )}
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
