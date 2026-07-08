"use client";
// LEVEL 2 — "Ready to Trade?" meter. Consolidates Entry Readiness % + the 4-zone
// AI Decision Meter (NOW / WAIT / LATE / AVOID) + a live Entry-Window countdown +
// the remaining blockers. Derivation-only (signal_maturity + entry_checklist).

import { useEffect, useState } from "react";
import { useMarket } from "@/lib/store";

const ZONES = ["NOW", "WAIT", "LATE", "AVOID"] as const;
const zoneTone: Record<string, string> = {
  NOW: "text-terminal-bull", WAIT: "text-terminal-warn", LATE: "text-terminal-warn", AVOID: "text-terminal-bear",
};

export function EntryReadinessMeter() {
  const { decision } = useMarket();
  const d: any = decision || {};
  const sm = d.signal_maturity;
  const ec = d.entry_checklist || {};
  const et = sm?.entry_trigger || {};

  // live-ticking countdown of the entry window
  const [remaining, setRemaining] = useState<number | null>(null);
  useEffect(() => {
    setRemaining(et.window_remaining_sec ?? null);
  }, [et.window_remaining_sec]);
  useEffect(() => {
    if (remaining == null) return;
    const t = setInterval(() => setRemaining((r) => (r == null ? r : Math.max(0, r - 1))), 1000);
    return () => clearInterval(t);
  }, [remaining == null]);

  if (!sm?.ready) return null;

  const readiness = sm.maturity_score ?? 0;
  const status = et.status;
  const zone = status === "FIRE NOW" ? "NOW"
    : status === "ENTRY CLOSED" ? "AVOID"
    : (status === "READY" && et.late_entry_risk === "HIGH") ? "LATE"
    : status === "READY" ? "NOW" : "WAIT";
  const waiting = ec.waiting_for || [];
  const fmtC = (s: number | null) => s == null ? "—" : s <= 0 ? "EXPIRED" : `${Math.floor(s / 60)}m ${s % 60}s`;

  return (
    <div className="panel">
      <div className="flex items-center justify-between mb-2">
        <div className="panel-title mb-0">Ready to Trade?</div>
        <span className="text-[11px] text-terminal-muted">
          Window: <span className={remaining !== null && remaining <= 0 ? "text-terminal-bear" : "font-mono text-gray-200"}>{fmtC(remaining)}</span>
        </span>
      </div>

      {/* readiness bar */}
      <div className="flex items-center gap-3 mb-2">
        <div className="flex-1 h-3 rounded-full bg-terminal-bg overflow-hidden">
          <div className={`h-full ${readiness >= 61 ? "bg-terminal-bull" : readiness >= 41 ? "bg-terminal-warn" : "bg-terminal-bear"}`}
               style={{ width: `${readiness}%` }} />
        </div>
        <span className="font-mono text-sm w-12 text-right">{readiness}%</span>
      </div>

      {/* 4-zone decision meter */}
      <div className="flex gap-1 mb-2">
        {ZONES.map((z) => (
          <div key={z} className={`flex-1 text-center text-[11px] py-1 rounded ${
            zone === z ? `bg-terminal-bg border border-terminal-accent/40 font-bold ${zoneTone[z]}` : "text-terminal-muted"}`}>
            {z}
          </div>
        ))}
      </div>

      {/* remaining blockers */}
      {waiting.length > 0 && (
        <div className="text-[11px] text-terminal-muted">
          Waiting: {waiting.map((w: string) => `□ ${w}`).join("  ")}
        </div>
      )}
    </div>
  );
}
