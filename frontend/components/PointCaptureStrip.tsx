"use client";
// V9 §2/§5 — compact Point Capture strip for Trading mode. One row: how many
// points are realistically available right now. Reuses execution_card data
// (which lives in Research) — display only, no new calculations.

import { useMarket } from "@/lib/store";

export function PointCaptureStrip() {
  const { decision } = useMarket();
  const pc = (decision as any)?.execution_card?.point_capture;
  if (!pc?.length) return null;

  // V12 §4 — highlight ONE best tier: the largest capture still in the
  // strip's own green zone (≥60%). No green tier ⇒ no BEST (honest).
  const best = [...pc].reverse().find((p: any) => p.probability >= 60)?.points;

  return (
    <div className="panel py-2">
      <div className="flex items-center gap-2">
        <span className="stat-label shrink-0">Point Capture</span>
        <div className="flex-1 grid grid-cols-6 gap-1.5 text-center text-[11px]">
          {pc.map((p: any) => (
            <div key={p.points} className={p.points === best ? "rounded-md ring-1 ring-terminal-bull/70 bg-terminal-bull/10" : ""}>
              <div className="font-mono">{p.points}pt{p.points === best ? " ★" : ""}</div>
              <div className={p.probability >= 60 ? "text-terminal-bull" : p.probability >= 35 ? "text-terminal-warn" : "text-terminal-muted"}>
                {p.probability}%
              </div>
              {p.time ? <div className="text-terminal-muted text-[9px]">{p.time}</div> : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
