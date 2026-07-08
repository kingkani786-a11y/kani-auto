"use client";
// V26 §1 — Entry Score Timeline. Fire/entry score over time with a sparkline so
// the trader sees it climbing toward entry (or fading). Derivation-only display.

import { useMarket } from "@/lib/store";

export function EntryScoreTimeline() {
  const { decision } = useMarket();
  const t = (decision as any)?.entry_score_timeline;
  if (!t?.ready || !t.timeline?.length) return null;

  const pts: { s: number }[] = t.timeline;
  const w = 240, h = 36, n = pts.length;
  const path = pts.map((p, i) => {
    const x = n === 1 ? w : (i / (n - 1)) * w;
    const y = h - (Math.max(0, Math.min(100, p.s)) / 100) * h;
    return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  const stageTone = t.stage === "ENTRY NOW" ? "text-terminal-bull"
    : t.stage === "APPROACHING" ? "text-terminal-warn"
    : t.stage === "WEAKENING" ? "text-terminal-bear" : "text-terminal-muted";
  const stroke = t.trend === "STRENGTHENING" ? "var(--color-terminal-bull,#22c55e)"
    : t.trend === "FADING" ? "var(--color-terminal-bear,#ef4444)" : "#888";

  return (
    <div className="panel">
      <div className="flex items-center justify-between mb-1">
        <div className="panel-title mb-0">Entry Score Timeline</div>
        <span className="font-mono text-sm">
          {t.current} <span className={`text-xs font-bold ${stageTone}`}>{t.stage}</span>
        </span>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-9" preserveAspectRatio="none">
        {/* entry threshold line */}
        <line x1="0" y1={h - (t.threshold / 100) * h} x2={w} y2={h - (t.threshold / 100) * h}
              stroke="#555" strokeWidth="0.5" strokeDasharray="3 3" />
        <path d={path} fill="none" stroke={stroke} strokeWidth="1.6" />
      </svg>
      <div className="flex items-center justify-between text-[11px] text-terminal-muted mt-1">
        <span>{t.trend} {t.delta > 0 ? `▲ +${t.delta}` : t.delta < 0 ? `▼ ${t.delta}` : ""}</span>
        <span>fire ≥ {t.threshold} = entry · range {t.low}–{t.high}</span>
      </div>
    </div>
  );
}
