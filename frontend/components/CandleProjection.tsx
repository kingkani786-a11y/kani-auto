"use client";
// AI LAYER 6 — Probability Candle Projection. Forward-only expected vs failure
// path (never repaints). Derivation-only display.

import { useMarket } from "@/lib/store";

export function CandleProjection() {
  const { decision } = useMarket();
  const cp = (decision as any)?.candle_projection;
  if (!cp?.ready || !cp.candles?.length) return null;

  const spot = cp.spot;
  const exp = cp.candles.map((c: any) => c.expected.close);
  const fail = cp.candles.map((c: any) => c.failure_close);
  const cone = cp.cone || [];
  const upper = cone.map((c: any) => c.upper);
  const lower = cone.map((c: any) => c.lower);
  const all = [spot, ...exp, ...fail, ...upper, ...lower];
  const lo = Math.min(...all), hi = Math.max(...all), span = hi - lo || 1;
  const W = 260, H = 70, n = cp.candles.length;
  const xs = (i: number) => (i / n) * W;                 // i=0 is spot
  const ys = (v: number) => H - ((v - lo) / span) * H;
  const line = (vals: number[]) =>
    [`M${xs(0)},${ys(spot)}`, ...vals.map((v, i) => `L${xs(i + 1)},${ys(v)}`)].join(" ");
  // ★ Probability Cone — filled 95% band (upper out, lower back)
  const conePath = cone.length
    ? [`M${xs(0)},${ys(spot)}`,
       ...upper.map((v: number, i: number) => `L${xs(i + 1)},${ys(v)}`),
       ...lower.slice().reverse().map((v: number, i: number) => `L${xs(n - i)},${ys(v)}`),
       "Z"].join(" ")
    : "";

  const p = cp.paths || {};

  return (
    <div className="panel">
      <div className="flex items-center justify-between mb-1">
        <div className="panel-title mb-0">Probability Candle Projection</div>
        <span className="text-[10px] text-terminal-muted">forward-only · no repaint</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-[70px]" preserveAspectRatio="none">
        {conePath && <path d={conePath} fill="var(--color-terminal-accent,#3b82f6)" opacity="0.12" stroke="none" />}
        <line x1="0" y1={ys(spot)} x2={W} y2={ys(spot)} stroke="#555" strokeWidth="0.5" strokeDasharray="3 3" />
        <path d={line(exp)} fill="none" stroke="var(--color-terminal-bull,#22c55e)" strokeWidth="1.6" />
        <path d={line(fail)} fill="none" stroke="var(--color-terminal-bear,#ef4444)" strokeWidth="1.2" strokeDasharray="3 2" />
      </svg>
      <div className="grid grid-cols-3 gap-2 text-center text-xs mt-1">
        <div>
          <div className="stat-label text-terminal-bull">Primary</div>
          <div>{p.primary?.probability}% → {p.primary?.target}</div>
        </div>
        <div>
          <div className="stat-label text-terminal-muted">Range</div>
          <div>{p.alternative?.probability}%</div>
        </div>
        <div>
          <div className="stat-label text-terminal-bear">Failure</div>
          <div>{p.failure?.probability}% → {p.failure?.target}</div>
        </div>
      </div>
      <div className="text-[10px] text-terminal-muted mt-1 text-center">
        {cp.direction} · expected move {cp.expected_move} pts · ETA {cp.candles[cp.candles.length - 1].eta_min}m
        {cp.cone_95_range && <> · ~95% range {cp.cone_95_range[0]}–{cp.cone_95_range[1]}</>}
      </div>
      {/* Owner Step 8 (Remove Fake Metrics, 2026-07-26) fix: cp.note (the
          "probabilities, not certainty" disclaimer) was computed by the
          backend but never read here — now shown. */}
      {cp.note && <div className="text-[10px] text-terminal-muted/70 mt-0.5 text-center">{cp.note}</div>}
    </div>
  );
}
