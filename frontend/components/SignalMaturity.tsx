"use client";
// PHASE 7 + 6 — Signal Maturity + Entry Trigger panel. Shows whether the setup
// is mature/stable enough to act and the entry-window state. Reads the decision
// slice; derivation-only display.

import { useMarket } from "@/lib/store";

const statusTone = (s?: string) =>
  s === "FIRE NOW" ? "text-terminal-bull" : s === "READY" || s === "ARMED" ? "text-terminal-warn"
  : s === "ENTRY CLOSED" ? "text-terminal-bear" : "text-terminal-muted";
const decayTone = (d?: string) =>
  d === "Strengthening" || d === "Fresh" ? "text-terminal-bull" : d === "Stable" ? "text-terminal-warn"
  : "text-terminal-bear";

const fmtSec = (s?: number | null) =>
  s == null ? "—" : s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`;

export function SignalMaturity() {
  const { decision } = useMarket();
  const sm = (decision as any)?.signal_maturity;
  if (!sm?.ready) return null;
  const et = sm.entry_trigger || {};
  const m = sm.maturity_score || 0;

  return (
    <div className="panel">
      <div className="flex items-center justify-between mb-2">
        <div className="panel-title mb-0">Signal Maturity & Entry Trigger</div>
        <span className={`text-sm font-bold tracking-wider ${statusTone(et.status)}`}>{et.status}</span>
      </div>

      {/* maturity bar */}
      <div className="flex items-center gap-3 mb-2">
        <div className="flex-1 h-2.5 rounded-full bg-terminal-bg overflow-hidden">
          <div className={`h-full ${m >= 61 ? "bg-terminal-bull" : m >= 41 ? "bg-terminal-warn" : "bg-terminal-bear"}`}
               style={{ width: `${m}%` }} />
        </div>
        <span className="font-mono text-sm w-20 text-right">{m}/100</span>
      </div>
      <div className="text-[11px] text-terminal-muted mb-2">
        {sm.stage} · threshold {sm.threshold}{sm.monthly_expiry_mode ? " · EXPIRY PRECISION MODE" : ""}
        {sm.buy_allowed ? "" : " · BUY gated until mature"}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1.5 text-xs">
        <div><div className="stat-label">Age</div><div className="font-mono">{fmtSec(sm.signal_age_sec)}</div></div>
        <div><div className="stat-label">Stability</div><div className="font-mono">{sm.stability}</div></div>
        <div><div className="stat-label">Decay</div><div className={decayTone(sm.decay)}>{sm.decay}</div></div>
        <div><div className="stat-label">Confirms</div><div className="font-mono">{sm.confirmation_count}/{sm.confirmation_total}</div></div>
        <div><div className="stat-label">Window Left</div><div className="font-mono">{fmtSec(et.window_remaining_sec)}</div></div>
        <div><div className="stat-label">Late Risk</div><div className={et.late_entry_risk === "LOW" ? "text-terminal-bull" : et.late_entry_risk === "HIGH" ? "text-terminal-bear" : "text-terminal-warn"}>{et.late_entry_risk}</div></div>
        <div><div className="stat-label">False-Sig Prob</div><div className="font-mono">{sm.false_signal_probability}%</div></div>
        <div><div className="stat-label">Entry Score</div><div className="font-mono">{et.entry_score}</div></div>
      </div>

      {et.remaining_confirmations > 0 && (
        <div className="text-[11px] text-terminal-muted mt-2">
          Missing: {(et.missing_confirmations || []).join(", ")}
        </div>
      )}
    </div>
  );
}
