"use client";
// V13 sticky Final Signal Banner — the single most visible component. Pure
// presentation: it only restates what the engines already decided (from the
// store), so a trader reads What / Why / Risk in 3 seconds. No logic here.

import { useMarket } from "@/lib/store";
import { RiskBadge } from "@/components/RiskBadge";

const fmt = (n?: number | null) =>
  n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: 2 });

const ACTION_STYLE: Record<string, string> = {
  "BUY CALL": "from-terminal-bull/25 to-terminal-bull/5 text-terminal-bull border-terminal-bull/50",
  "BUY PUT": "from-terminal-bear/25 to-terminal-bear/5 text-terminal-bear border-terminal-bear/50",
  WAIT: "from-terminal-warn/20 to-terminal-warn/5 text-terminal-warn border-terminal-warn/50",
  "NO TRADE": "from-terminal-border/30 to-transparent text-terminal-muted border-terminal-border",
};

function Field({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div className="text-center px-2">
      <div className="text-[9px] uppercase tracking-wider text-terminal-muted">{label}</div>
      <div className={`font-mono text-sm font-bold leading-tight ${tone ?? ""}`}>{value}</div>
    </div>
  );
}

export function FinalSignalBanner() {
  const { decision: d, signal, risk, layers } = useMarket();

  const action = d?.action ?? (signal?.signal === "NO TRADE" ? "NO TRADE" : "ANALYZING");
  const style = ACTION_STYLE[action] ?? ACTION_STYLE["NO TRADE"];
  const conf = signal?.dynamic_confidence ?? signal?.confidence;
  const bias = (layers as any)?.global_context?.bias ?? "—";
  const live = !!d;

  return (
    <div className="sticky top-14 z-30 -mx-3 sm:-mx-5 px-3 sm:px-5 py-2
                    bg-terminal-bg/95 backdrop-blur border-b border-terminal-border">
      <div className={`rounded-xl border bg-gradient-to-r ${style}
                       flex items-stretch gap-2 sm:gap-4 px-3 sm:px-4 py-2.5 overflow-x-auto`}>
        {/* the call */}
        <div className="flex flex-col justify-center min-w-[120px] shrink-0">
          <div className="text-[9px] uppercase tracking-widest opacity-70">Final Signal</div>
          <div className="text-xl sm:text-2xl font-black font-mono tracking-tight leading-none">
            {action}
          </div>
          {d?.grade && d.grade !== "NO TRADE" && (
            <div className="text-[10px] font-bold mt-0.5 opacity-90">Grade {d.grade}</div>
          )}
        </div>

        <div className="w-px bg-current opacity-15 shrink-0" />

        {/* levels — only meaningful on a live trade */}
        {d?.is_trade ? (
          <div className="flex items-center gap-1 sm:gap-3 shrink-0">
            <Field label="Entry" value={fmt(d.entry)} />
            <Field label="Stop" value={fmt(d.stop_loss)} tone="text-terminal-bear" />
            <Field label="T1" value={fmt(d.target1)} tone="text-terminal-bull" />
            <Field label="T2" value={fmt(d.target2)} tone="text-terminal-bull" />
            <Field label="T3" value={fmt(d.target3)} tone="text-terminal-bull" />
          </div>
        ) : (
          <div className="flex items-center text-xs text-terminal-muted px-2 shrink-0">
            {live ? (d?.reason || "Capital-protection mode — standing aside") : "Reading the market…"}
          </div>
        )}

        <div className="ml-auto flex items-center gap-2 sm:gap-3 shrink-0">
          <Field label="Confidence" value={conf != null ? `${Math.round(conf)}%` : "—"} />
          <Field label="Bias" value={bias}
            tone={bias === "BULLISH" ? "text-terminal-bull" : bias === "BEARISH" ? "text-terminal-bear" : "text-terminal-muted"} />
          <div className="flex flex-col items-center justify-center gap-1 px-1">
            <div className="text-[9px] uppercase tracking-wider text-terminal-muted">Risk</div>
            <RiskBadge level={risk?.risk_level} size="sm" />
          </div>
        </div>
      </div>
    </div>
  );
}
