"use client";
// SHADOW CALIBRATION (owner, 2026-08-07) — RESEARCH display only.
//
// WHY THIS CARD EXISTS. The real calibration score can only move when a TAKEN
// signal settles. But the Kill Switch forces "NO TRADE" whenever calibration
// < 55, and memory.track_signal() early-returns on "NO TRADE" — so while the
// gate is shut, the real score is structurally unable to receive new evidence.
// Proven, not assumed: 4,513 of 4,525 black-box snapshots name "Calibration 54"
// as the kill-switch reason. This card shows the SAME calibration maths run
// over the cycles the gate BLOCKED, which audit.py already forward-tracks to a
// real win/loss — the one window the real score cannot see.
//
// It is deliberately styled as RESEARCH (dashed border, explicit label) so it
// can never be mistaken for the production number sitting in CalibrationWatchCard.
// It changes no threshold, unlocks no trade, and the backend module it reads
// imports no gate/decision module at all.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function ShadowCalibrationCard() {
  const [r, setR] = useState<any>(null);
  useEffect(() => {
    const load = () => api.shadowCalibration?.().then(setR).catch(() => {});
    load();
    const id = setInterval(load, 60000);
    return () => clearInterval(id);
  }, []);
  if (!r) return null;

  const score = r.shadow_calibration_score;
  const building = r.status === "BUILDING";
  const buckets: Record<string, any> = r.buckets || {};
  const bucketKeys = ["60-70", "70-80", "80-90", "90-100"];

  return (
    <section className="panel border-dashed border-terminal-muted/50">
      <div className="panel-title flex items-center gap-2">
        <span>🧪 Shadow Calibration</span>
        <span className="text-[10px] px-1.5 py-0.5 rounded border border-terminal-warn/50 text-terminal-warn">
          RESEARCH
        </span>
      </div>

      <div className="text-xs text-terminal-muted mb-3 leading-relaxed">
        The real calibration score can only move when a <b>taken</b> trade settles —
        but while the Kill Switch blocks entries, none ever do. This runs the{" "}
        <b>identical formula</b> over the cycles the gate <b>blocked</b>, which are
        forward-tracked to a real win/loss. It is the evidence the real score
        structurally cannot collect.
      </div>

      {building ? (
        <div className="text-sm">
          <span className="text-terminal-warn font-bold">BUILDING</span>
          <div className="text-xs text-terminal-muted mt-1">{r.progress}</div>
        </div>
      ) : (
        <div className="flex items-baseline gap-3 mb-3">
          <span className="text-3xl font-mono font-bold text-terminal-warn">{score}</span>
          <span className="text-xs text-terminal-muted">
            shadow score · error {r.error} · {r.buckets_measured} bucket
            {r.buckets_measured === 1 ? "" : "s"}
          </span>
        </div>
      )}

      <table className="w-full text-xs font-mono mb-3">
        <thead>
          <tr className="stat-label text-left">
            <th className="pb-1 font-normal">Confidence</th>
            <th className="pb-1 font-normal text-right">Samples</th>
            <th className="pb-1 font-normal text-right">Actual Win %</th>
            <th className="pb-1 font-normal text-right">Error</th>
          </tr>
        </thead>
        <tbody>
          {bucketKeys.map((k) => {
            const b = buckets[k];
            const mid = { "60-70": 65, "70-80": 75, "80-90": 85, "90-100": 95 }[k]!;
            const enough = b && b.n >= 3;
            return (
              <tr key={k} className="border-t border-terminal-border/40">
                <td className="py-1 text-terminal-muted">{k}%</td>
                <td className="py-1 text-right">{b?.n ?? "—"}</td>
                <td className="py-1 text-right">{b ? `${b.win_rate}%` : "—"}</td>
                <td className="py-1 text-right">
                  {enough ? (
                    <span className={Math.abs(mid - b.win_rate) > 20 ? "text-terminal-bear" : ""}>
                      {Math.abs(mid - b.win_rate).toFixed(1)}
                    </span>
                  ) : (
                    <span className="text-terminal-muted">need 3+</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mb-3">
        <div>
          <span className="stat-label">Blocked samples </span>
          <span className="font-mono">{r.sample_blocked ?? 0}</span>
        </div>
        <div>
          <span className="stat-label">Blocked win rate </span>
          <span className="font-mono">
            {r.blocked_win_rate == null ? "—" : `${r.blocked_win_rate}%`}
          </span>
        </div>
        <div>
          <span className="stat-label">Days covered </span>
          <span className="font-mono">{r.days_covered ?? 0}</span>
        </div>
        <div>
          <span className="stat-label">Range </span>
          <span className="font-mono">
            {r.first_day ? `${r.first_day} → ${r.last_day}` : "—"}
          </span>
        </div>
        {/* LEGACY DISCLOSURE (owner, 2026-08-12). The backend excludes
            pre-fix, market-blind records from scoring — but without this the
            card just reads "Blocked samples 0", which looks like a broken
            collector rather than a deliberate reset. The count is already
            computed server-side; this only surfaces it. */}
        {r.sample_legacy > 0 && (
          <div className="col-span-2 text-[11px] text-terminal-warn border-t border-terminal-border/40 pt-1 mt-1">
            <b>{r.sample_legacy} legacy records excluded</b> — {r.legacy_note}
          </div>
        )}
      </div>

      <div className="text-[11px] text-terminal-muted leading-relaxed border-t border-terminal-border/40 pt-2">
        <b>Honest scope:</b> a blocked cycle has no real planned entry, so this uses
        synthetic ATR levels (entry = spot, stop 1.2×ATR, T1 1.5×ATR). It measures
        whether the <i>directional confidence</i> was honest — not whether a planned
        trade would have filled and won. Research only: changes no threshold, no
        Kill Switch, and cannot unlock trading.
      </div>
    </section>
  );
}
