"use client";
// V8 §8 — Gamma Shield strip. Shows ONLY when gamma risk is elevated (WATCH/
// HIGH/SPIKE): state + recommendation + reasons. Advisory display; SAFE = hidden.

import { useMarket } from "@/lib/store";

export function GammaShield() {
  const { decision } = useMarket();
  const g = (decision as any)?.gamma_shield;
  if (!g?.ready || g.state === "SAFE") return null;

  const tone = g.state === "SPIKE" ? "border-terminal-bear/70 bg-terminal-bear/15 text-terminal-bear"
    : g.state === "HIGH" ? "border-terminal-bear/50 bg-terminal-bear/10 text-terminal-bear"
    : "border-terminal-warn/50 bg-terminal-warn/5 text-terminal-warn";

  return (
    <div className={`panel border py-2.5 ${tone}`}>
      <div className="flex items-center justify-between flex-wrap gap-2 text-sm">
        <span className="font-bold tracking-wider">🛡 GAMMA SHIELD — {g.state}</span>
        <span className="font-semibold">{g.recommendation}</span>
      </div>
      {g.reasons?.length > 0 && (
        <div className="text-[11px] text-gray-300 mt-1">
          {g.reasons.slice(0, 2).join(" · ")}
          {g.gamma_wall ? ` · wall ${g.gamma_wall}${g.wall_distance_pts != null ? ` (${g.wall_distance_pts} pts away)` : ""}` : ""}
        </div>
      )}
    </div>
  );
}
