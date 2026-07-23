"use client";
// V3.0 — Missed Winners (simplified). Four numbers + top blocker + review link.
// No paragraphs. Evidence layer — drives calibration, not behaviour.

import Link from "next/link";
import { useMarket } from "@/lib/store";
import { displayLabel } from "@/lib/labels";

export function MissedWinners() {
  const { decision } = useMarket();
  const m = (decision as any)?.missed_winner;
  if (!m?.ready || !m.missed_today) return null;   // hide when none

  return (
    <div className="panel border-terminal-warn/40 py-2.5">
      <div className="flex items-center justify-between flex-wrap gap-x-4 gap-y-1 text-sm">
        {/* RC1.13 — every count carries an explicit scope word, not just the
            first one in the row (doctrine: no unscoped metric on any card) */}
        <span><span className="stat-label">Missed (Today)</span> <span className="font-bold text-terminal-warn">{m.missed_today}</span></span>
        <span><span className="stat-label">Profit Lost (Today)</span> <span className="font-bold text-terminal-bear">+{m.potential_lost_pts ?? 0} pts</span></span>
        <span><span className="stat-label">Largest (Today)</span> <span className="font-mono">+{m.max_missed_pts}</span></span>
        <span><span className="stat-label">Top Blocker (Today)</span> <span className="text-terminal-bear">{displayLabel(m.worst_blocker) ?? "—"}</span></span>
        <Link href="/report-card" className="text-[11px] px-2.5 py-1 rounded border border-terminal-border text-terminal-muted hover:border-terminal-accent hover:text-white">
          Review →
        </Link>
      </div>
    </div>
  );
}
