"use client";
// Move Observer — extracted from MissedMoveProtection (2026-07-26 Dashboard
// Cleanup Audit). MissedMoveProtection's verdict half (READY/WAIT + missing
// reasons) duplicated execution_gate.blocking_reasons/blocker_research already
// shown in full by ExecutionControlCenter — that half was removed. This strip
// keeps the one thing that panel wasn't duplicating anywhere else: live
// move-episode facts from moveAlerts(). Kept Simple-mode visible (not gated
// behind Advanced mode) per Incident #001: "a building move must be visible
// even while the Decision Layer says WAIT."
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const STARS = (n: number) => "★".repeat(n) + "☆".repeat(5 - n);
const STRENGTH_WORD = ["—", "Early", "Building", "Strong", "Very Strong", "Explosive"];

export function MoveObserverStrip() {
  const [episodes, setEpisodes] = useState<any[]>([]);

  useEffect(() => {
    const load = () =>
      api.moveAlerts?.().then((d: any) => setEpisodes(d?.active_episodes || [])).catch(() => {});
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  if (episodes.length === 0) return null; // calm until a move is actually observed

  return (
    <div className="panel border-terminal-warn/40">
      <div className="panel-title">🔥 Move Observer — MOVE DETECTED</div>
      {episodes.slice(0, 3).map((e: any, i: number) => (
        <div key={i} className="mt-2 text-xs border-b border-terminal-border/20 pb-2 last:border-0">
          <div className="flex flex-wrap items-baseline gap-x-3">
            <span className="font-bold">{e.symbol} {e.strike}{e.type}</span>
            <span className="font-mono">₹{e.from_low} → ₹{e.premium} (+{e.rise_pct}%)</span>
            <span className={e.move_strength >= 4 ? "text-terminal-bull font-bold" : "text-terminal-warn"}>
              {STARS(e.move_strength)} {e.move_strength}/5 · {STRENGTH_WORD[e.move_strength]}
            </span>
          </div>
          <div className="flex flex-wrap gap-x-4 text-[11px] text-terminal-muted mt-0.5">
            <span>Velocity {e.velocity_pts_min} pts/min{e.accelerating ? " · ACCELERATING" : ""}</span>
            {e.volume_x != null && <span>Vol {e.volume_x}×</span>}
            {e.oi_change_pct != null && <span>OI {e.oi_change_pct > 0 ? "+" : ""}{e.oi_change_pct}%</span>}
            {e.next_tier && <span>Next: {e.next_tier.name} at ₹{e.next_tier.at_premium}</span>}
            <span>Episode {e.episode_started ?? "—"} · {e.elapsed_min}m elapsed
              {e.avg_episode_min != null ? ` · avg ${e.avg_episode_min}m` : " · avg — (learning)"}</span>
          </div>
        </div>
      ))}
      <div className="text-[10px] text-terminal-muted mt-2">
        Full WAIT/READY verdict and reasons: see Execution Control Center (Advanced) or the Block Reason banner above.
      </div>
    </div>
  );
}
