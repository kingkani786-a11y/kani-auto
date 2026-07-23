"use client";
// S/R HEAT MAP (owner, 2026-07-23, item #5 Phase 2, Priority 8) — side-panel
// visualization of already-computed strength scores. No new data, no new
// calculation: pure rendering of support_resistance.py's own output.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

function bar(score: number, cmp: number, level: number) {
  const width = Math.max(8, Math.min(100, score));
  const above = level > cmp;
  return (
    <div key={level} className="flex items-center gap-1.5 text-[10px]">
      <span className="w-14 text-right tabular-nums text-terminal-muted">{level}</span>
      <div className="flex-1 h-2.5 bg-terminal-border/30 rounded overflow-hidden">
        <div
          className={`h-full rounded ${above ? "bg-terminal-bear/70" : "bg-terminal-bull/70"}`}
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="w-8 tabular-nums text-terminal-muted">{score}</span>
    </div>
  );
}

export function SRHeatMap() {
  const [r, setR] = useState<any>(null);
  useEffect(() => {
    const load = () => api.supportResistance().then(setR).catch(() => {});
    load();
    const id = setInterval(load, 20000);
    return () => clearInterval(id);
  }, []);
  if (!r?.ready) return null;

  const res = [...(r.resistance || [])].sort((a: any, b: any) => a.level - b.level);
  const sup = [...(r.support || [])].sort((a: any, b: any) => b.level - a.level);

  return (
    <div className="panel border border-terminal-border/60">
      <div className="panel-title mb-2">S/R Heat Map <span className="text-[10px] text-terminal-muted font-normal">(strength score, not a prediction)</span></div>
      <div className="space-y-1">
        {res.map((l: any) => bar(l.strength_score, r.cmp, l.level))}
        <div className="text-center text-[10px] text-terminal-accent font-semibold py-0.5 border-y border-terminal-border/40 my-1">
          PRICE {r.cmp}
        </div>
        {sup.map((l: any) => bar(l.strength_score, r.cmp, l.level))}
      </div>
    </div>
  );
}
