"use client";
// WARM-UP GATE VISIBILITY (owner audit, 2026-08-05).
//
// The >=60-bar requirement before confluence runs at all already existed
// (market_service.py's _ai_cycle) — a real anti-fabrication gate, not new
// here. What was missing: the gate fired silently, so a freshly switched-to
// instrument with thin broker history showed a blank dashboard with no
// indication why. This banner surfaces the EXISTING gate; it introduces no
// new threshold and changes no decision.

import { useMarket } from "@/lib/store";

export function WarmupBanner() {
  const { status } = useMarket();
  const w = (status as any)?.warmup;
  if (!w || w.ready !== false) return null;

  const pct = Math.min(100, Math.round((w.bars / w.required) * 100));

  return (
    <div className="panel py-2.5 text-[11px] border-terminal-warn/40">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="font-bold tracking-wider text-terminal-warn">
          ⏳ {w.symbol} — ANALYSIS WARMING UP
        </span>
        <span className="text-terminal-muted tabular-nums">{w.bars} / {w.required} bars ({pct}%)</span>
      </div>
      <div className="text-terminal-muted mt-1">
        Waiting for enough historical 1-minute bars from the broker before the
        engine will run at all — this is an existing safety floor (no
        partial/fake analysis below it), not a new restriction. Clears on its
        own once enough bars arrive.
      </div>
    </div>
  );
}
