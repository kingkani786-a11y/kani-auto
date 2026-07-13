"use client";
// ⚡ Premium Radar — the option BUYER's live view. Always-on tracking of the
// ATM±N strikes so a premium's BIRTH → EXPANSION → RUNNER is visible from the
// first minute (not hidden until a big-move alert). Read-only; the engine gate
// still decides trades. Runner score is a declared signal blend, NOT a
// win-calibrated probability.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const STAGE_TONE: Record<string, string> = {
  BIRTH: "text-terminal-muted", EXPANSION: "text-terminal-accent",
  ACCELERATION: "text-terminal-warn", RUNNER: "text-terminal-bull",
  EXHAUSTION: "text-terminal-bear",
};
const stars = (n: number) => "★".repeat(n) + "☆".repeat(5 - n);

export function PremiumRadar() {
  const [d, setD] = useState<any>(null);
  useEffect(() => {
    const load = () => api.premiumRadar(8).then(setD).catch(() => {});
    load(); const t = setInterval(load, 4000); return () => clearInterval(t);
    // 4s poll — the backend samples every option tick (~5s)
  }, []);

  const movers: any[] = d?.movers || [];
  const active = movers.filter((m) => m.runner_score > 0);

  return (
    <section className="panel space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">⚡ Premium Radar <span className="text-[10px] text-terminal-muted">(option buyer · live)</span></h2>
        {d && <span className="text-[10px] text-terminal-muted">{d.tracked} strikes tracked</span>}
      </div>

      {!d ? <div className="text-xs text-terminal-muted">Loading…</div>
        : active.length === 0 ? (
          <div className="text-xs text-terminal-muted">
            No premium movement yet. Fills live during market hours — you'll see
            each strike's premium, velocity and runner score as a move is born.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-terminal-muted text-[10px]">
                <tr className="text-left">
                  <th className="py-1">Strike</th><th>Premium</th><th>▲%</th>
                  <th>Vel</th><th>Accel</th><th>OI%</th><th>Stage</th><th>Runner</th>
                </tr>
              </thead>
              <tbody>
                {active.map((m, i) => (
                  <tr key={i} className="border-t border-terminal-border">
                    <td className="py-1 text-white whitespace-nowrap">{m.strike} {m.type}</td>
                    <td className="tabular-nums">₹{m.premium}</td>
                    <td className={`tabular-nums ${m.rise_pct > 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>{m.rise_pct > 0 ? "+" : ""}{m.rise_pct}%</td>
                    <td className="tabular-nums">{m.velocity}</td>
                    <td className={`tabular-nums ${m.accel > 0 ? "text-terminal-bull" : m.accel < 0 ? "text-terminal-bear" : ""}`}>{m.accel > 0 ? "+" : ""}{m.accel}</td>
                    <td className="tabular-nums">{m.oi_pct > 0 ? "+" : ""}{m.oi_pct}%</td>
                    <td className={STAGE_TONE[m.stage] || ""}>{m.stage}</td>
                    <td className="whitespace-nowrap"><span className="text-terminal-warn">{stars(m.stars)}</span> <span className="text-terminal-muted tabular-nums">{m.runner_score}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      <div className="text-[10px] text-terminal-muted">
        Runner score = declared signal blend (rise/velocity/acceleration/volume/OI), not a calibrated win-probability. Radar observes; the engine decides trades.
      </div>
    </section>
  );
}
