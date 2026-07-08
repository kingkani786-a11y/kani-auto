"use client";
// MASTER DECISION — single source of truth at the very top. Exactly ONE state
// (WAIT/ENTER/HOLD/TRAIL/EXIT) from decision.primary_action, a one-line why,
// and a compact AI analyst line. No conflicting decisions shown.

import { useMarket } from "@/lib/store";

const TONE: Record<string, string> = {
  ENTER: "from-terminal-bull/25 to-transparent text-terminal-bull border-terminal-bull/50",
  "RE-ENTER": "from-terminal-bull/25 to-transparent text-terminal-bull border-terminal-bull/50",
  HOLD: "from-terminal-bull/15 to-transparent text-terminal-bull border-terminal-bull/40",
  TRAIL: "from-terminal-accent/20 to-transparent text-terminal-accent border-terminal-accent/50",
  "PARTIAL EXIT": "from-terminal-accent/20 to-transparent text-terminal-accent border-terminal-accent/50",
  "FULL EXIT": "from-terminal-bear/25 to-transparent text-terminal-bear border-terminal-bear/50",
  EXIT: "from-terminal-bear/25 to-transparent text-terminal-bear border-terminal-bear/50",
  PREPARE: "from-terminal-warn/20 to-transparent text-terminal-warn border-terminal-warn/50",
  WATCH: "from-terminal-warn/15 to-transparent text-terminal-warn border-terminal-warn/40",
  WAIT: "from-terminal-warn/15 to-transparent text-terminal-warn border-terminal-warn/40",
};

export function FinalActionBar() {
  const { decision: d, signal, layers } = useMarket();
  const action = d?.primary_action ?? "WAIT";
  const why = d?.reason ?? (signal?.signal === "NO TRADE" ? "No qualifying setup" : "Analyzing…");
  const analyst = (layers as any)?.intelligence?.summary?.whats_happening;
  // S12 — Conviction Meter band from dynamic confidence
  const conv = Math.round(signal?.dynamic_confidence ?? signal?.confidence ?? 0);
  const convBand = conv >= 80 ? "AGGRESSIVE" : conv >= 60 ? "ENTER" : conv >= 40 ? "PREPARE" : conv >= 20 ? "WATCH" : "IGNORE";
  const convTone = conv >= 60 ? "text-terminal-bull" : conv >= 40 ? "text-terminal-warn" : "text-terminal-muted";
  // what to trade (if a trade) — shown small beside the action, never conflicting
  const tradeTag = d?.is_trade && signal?.signal && signal.signal !== "NO TRADE" ? signal.signal : null;

  return (
    <div className={`rounded-xl border bg-gradient-to-r ${TONE[action] ?? TONE.WAIT} px-4 py-3`}>
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-[10px] uppercase tracking-widest opacity-70">Final Action</span>
        <span className="text-3xl font-black font-mono tracking-tight leading-none">{action}</span>
        {tradeTag && <span className="text-sm font-bold font-mono opacity-90">· {tradeTag}</span>}
        {analyst && <span className="ml-auto text-xs opacity-80">{analyst}</span>}
      </div>
      <div className="flex items-center gap-3 mt-1">
        <div className="text-sm opacity-90 flex-1">{why}</div>
        <span className="text-[10px] uppercase tracking-wider opacity-70">Conviction</span>
        <span className={`text-xs font-bold font-mono ${convTone}`}>{conv} · {convBand}</span>
      </div>
    </div>
  );
}
