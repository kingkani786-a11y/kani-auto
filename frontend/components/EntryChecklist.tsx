"use client";
// PHASE 2/3/8 — Live Entry Checklist + Fire Score + WHY-NOT. Shows each
// confirmation PASS/WAITING/FAIL with remaining distance, the fire-score band,
// and exact reasons when there's no trade. Derivation-only display.

import { useMarket } from "@/lib/store";

const stTone = (s: string) =>
  s === "PASS" ? "text-terminal-bull" : s === "FAIL" ? "text-terminal-bear" : "text-terminal-warn";
const bandTone = (b?: string) =>
  b === "BUY NOW" ? "text-terminal-bull" : b === "ARMED" || b === "PREPARE" ? "text-terminal-warn" : "text-terminal-muted";

export function EntryChecklist() {
  const { decision } = useMarket();
  const ec = (decision as any)?.entry_checklist;
  if (!ec?.ready) return null;

  return (
    <div className="panel">
      <div className="flex items-center justify-between mb-2">
        <div className="panel-title mb-0">Live Entry Checklist — {ec.passed}/{ec.total} confirmed</div>
        <span className={`text-sm font-bold ${bandTone(ec.fire_band)}`}>
          {ec.fire_band} · {ec.fire_score}/100
        </span>
      </div>

      <div className="grid sm:grid-cols-2 gap-x-5 gap-y-1">
        {ec.checklist.map((c: any) => (
          <div key={c.item} className="flex items-center justify-between text-xs border-b border-terminal-border/20 py-1">
            <span className="text-gray-300">{c.item}</span>
            <span className="flex items-center gap-2">
              <span className="font-mono text-terminal-muted">{c.score}</span>
              {c.remaining > 0 && <span className="text-[10px] text-terminal-muted">+{c.remaining}</span>}
              <span className={`font-bold w-16 text-right ${stTone(c.status)}`}>{c.status}</span>
            </span>
          </div>
        ))}
      </div>

      {!ec.is_trade && ec.why_not?.length > 0 && (
        <div className="mt-3 pt-2 border-t border-terminal-border/40">
          <div className="stat-label text-terminal-bear mb-1">WHY NO TRADE</div>
          <ul className="text-[11px] text-gray-300 space-y-0.5">
            {ec.why_not.map((w: string, i: number) => (
              <li key={i} className="flex gap-1.5"><span className="text-terminal-bear">▸</span>{w}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="text-[10px] text-terminal-muted mt-2">{ec.note}</div>
    </div>
  );
}
