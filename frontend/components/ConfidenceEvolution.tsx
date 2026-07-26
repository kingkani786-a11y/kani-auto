"use client";
// MODULE 9 — AI Confidence Evolution. Sparkline of confidence over the session
// + which layer drove the latest move. Derivation-only display.

import { useMarket } from "@/lib/store";

export function ConfidenceEvolution() {
  const { decision } = useMarket();
  const ce = (decision as any)?.confidence_evolution;
  if (!ce?.ready || !ce.timeline?.length) return null;

  const pts: { c: number }[] = ce.timeline;
  const w = 240, h = 40, n = pts.length;
  const lo = Math.min(...pts.map((p) => p.c), 0);
  const hi = Math.max(...pts.map((p) => p.c), 100);
  const span = hi - lo || 1;
  const path = pts.map((p, i) => {
    const x = n === 1 ? w : (i / (n - 1)) * w;
    const y = h - ((p.c - lo) / span) * h;
    return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  const dirTone = ce.direction === "increased" ? "text-terminal-bull"
    : ce.direction === "decreased" ? "text-terminal-bear" : "text-terminal-muted";
  const stroke = ce.direction === "increased" ? "var(--color-terminal-bull, #22c55e)"
    : ce.direction === "decreased" ? "var(--color-terminal-bear, #ef4444)" : "#888";

  return (
    <div className="panel">
      <div className="flex items-center justify-between mb-1">
        <div className="panel-title mb-0">AI Confidence Evolution</div>
        <span className="font-mono text-sm">
          {ce.current}% <span className={`text-xs ${dirTone}`}>
            {ce.delta > 0 ? `▲ +${ce.delta}` : ce.delta < 0 ? `▼ ${ce.delta}` : "▪ flat"}
          </span>
        </span>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-10" preserveAspectRatio="none">
        <path d={path} fill="none" stroke={stroke} strokeWidth="1.5" />
      </svg>
      <div className="flex items-center justify-between text-[11px] text-terminal-muted mt-1">
        <span>{ce.why}</span>
        <span>range {ce.low}–{ce.high}%</span>
      </div>
      {ce.action_hint && ce.action_hint !== "Stable" && (
        <div className={`text-[11px] font-semibold mt-0.5 ${
          ce.action_hint.includes("BUY") ? "text-terminal-bull" : "text-terminal-warn"}`}>
          {ce.action_hint}
        </div>
      )}
      {/* Owner Step 8 (Remove Fake Metrics, 2026-07-26) fix: ce.note (the
          "probabilities, not certainty" disclaimer) was computed by the
          backend but never read here — now shown. */}
      {ce.note && <div className="text-[10px] text-terminal-muted/70 mt-1">{ce.note}</div>}
    </div>
  );
}
