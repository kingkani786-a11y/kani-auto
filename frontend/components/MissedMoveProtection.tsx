"use client";
// MOVE INTELLIGENCE PANEL — MODE Phase B.1 (owner-approved design).
// Two brains, one card, never mixed:
//   Layer 1 (Market Observer): live move FACTS from the opportunity engine —
//     premium path, velocity, strength stars, episode lifetime, next tier.
//   Layer 2 (Decision Engine): the gate's verdict — WAIT + missing, or
//     READY + the plan. Pure consumer of both sources; computes nothing.
// Incident #001 rule: a building move must be visible even while the
// Decision Layer says WAIT.
import { useEffect, useState } from "react";
import { useMarket } from "@/lib/store";
import { api } from "@/lib/api";
import { displayReasons } from "@/lib/labels";

const STARS = (n: number) => "★".repeat(n) + "☆".repeat(5 - n);
const STRENGTH_WORD = ["—", "Early", "Building", "Strong", "Very Strong", "Explosive"];

export function MissedMoveProtection() {
  const { alerts, decision } = useMarket();
  const [episodes, setEpisodes] = useState<any[]>([]);

  useEffect(() => {
    const load = () =>
      api.moveAlerts?.().then((d: any) => setEpisodes(d?.active_episodes || [])).catch(() => {});
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  const moveAlertCount = (alerts || []).filter((a: any) => a.kind === "MOVE").length;
  const eg = (decision as any)?.execution_gate || {};
  const ready = !!eg.gate_passed;
  const strike = (decision as any)?.strike || {};
  // display-mapped (owner, 2026-07-23, item #3): "Kill Switch: ..." renders as
  // "Execution Lock: ..."; the backend field/value itself is untouched.
  const missing: string[] = ready ? [] :
    displayReasons((eg.blocking_reasons?.length ? eg.blocking_reasons : eg.waiting_on || []).slice(0, 4));
  const research = (eg.blocker_research || [])[0];

  if (episodes.length === 0 && moveAlertCount === 0) return null; // calm until MODE speaks

  return (
    <div className={`panel ${ready ? "border-terminal-bull/60" : "border-terminal-warn/40"}`}>
      <div className="flex items-baseline justify-between">
        <div className="panel-title">
          {ready ? "🟢 MOVE INTELLIGENCE — ENTRY READY" : "🔥 MOVE INTELLIGENCE — MOVE DETECTED"}
        </div>
        <div className="text-[11px] text-terminal-muted">observer ∥ decision · never mixed</div>
      </div>

      {/* ---- Layer 1: Market Observer (facts) ---- */}
      {episodes.slice(0, 3).map((e, i) => (
        <div key={i} className="mt-2 text-xs border-b border-terminal-border/20 pb-2">
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
      {episodes.length === 0 && (
        <div className="mt-2 text-[11px] text-terminal-muted">
          No open episode — {moveAlertCount} move alert(s) earlier this session (see alert feed).
        </div>
      )}

      {/* ---- Layer 2: Decision Engine (verdict) ---- */}
      <div className="mt-2 pt-2 text-xs">
        {ready ? (
          <div className="flex flex-wrap gap-x-4">
            <span className="text-terminal-bull font-bold">🟢 ENTRY STATUS: READY</span>
            {strike.premium_entry != null && (
              <span className="font-mono">
                Entry ₹{strike.premium_entry} · SL ₹{strike.premium_stop_loss} · T1 ₹{strike.premium_target1}
              </span>
            )}
          </div>
        ) : (
          <div className="space-y-0.5">
            <div><span className="text-terminal-warn font-bold">🟡 ENTRY STATUS: WAIT</span>
              {missing.length > 0 && (
                <span className="text-terminal-muted"> · missing: {missing.join(" · ")}</span>
              )}
            </div>
            {research && research.status !== "NO DATA YET" && (
              <div className="text-[11px] text-terminal-muted">
                Entering against "{research.module}" historically: saved {research.saved_pct}% /
                missed {research.missed_pct}%
                {research.solo_missed_pct != null && ` (solo-missed ${research.solo_missed_pct}%)`}
                {" "}— research only, not an approval.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
