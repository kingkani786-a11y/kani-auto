"use client";
// Daily Review — keeps the dashboard alive when the market is closed: a learning
// summary of the session (signals, win rate, best/worst, last strike, AI status).
// Derivation-only; only renders when the market is closed.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";

function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${tone ?? ""}`}>{value}</div>
    </div>
  );
}

export function DailyReview() {
  const { status } = useMarket();
  const [d, setD] = useState<any>(null);
  const closed = status?.connected && (status as any)?.market_status && !(status as any).market_status.is_open;

  useEffect(() => {
    if (!closed) return;
    const load = () => api.dailyReview().then(setD).catch(() => {});
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [closed]);

  if (!closed || !d?.ready) return null;
  const pct = (n?: number | null) => (n == null ? "—" : `${n}%`);

  return (
    <div className="space-y-3">
      <section className="panel">
        <div className="panel-title">Daily Review — session summary</div>
        {/* RC1.13 — every stat carries its own scope word, not just the card title */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4">
          <Stat label="Signals (Today)" value={d.signals ?? 0} />
          <Stat label="Settled (Today)" value={d.settled ?? 0} />
          <Stat label="Win Rate (Today)" value={pct(d.win_rate)} tone={(d.win_rate ?? 0) >= 55 ? "text-terminal-bull" : "text-terminal-warn"} />
          <Stat label="Net Points (Today)" value={d.net_points ?? 0} tone={(d.net_points ?? 0) >= 0 ? "text-terminal-bull" : "text-terminal-bear"} />
          <Stat label="Avg MFE (Today)" value={d.avg_mfe_pts != null ? `${d.avg_mfe_pts} pts` : "—"} tone="text-terminal-bull" />
          <Stat label="Last Strike" value={d.last_strike ? `${d.last_strike} ${d.last_strike_type ?? ""}` : "—"} />
        </div>
        {(d.best || d.worst) && (
          <div className="text-xs mt-3 space-y-1">
            {/* RC1.11 fix: these are the WEEK's best/worst (backend pulls
                week aggregate so the card isn't blank on a zero-trade day) —
                label it, so it never reads as contradicting "no trades yet"
                for TODAY right above. */}
            <div className="text-terminal-muted text-[10px]">This week:</div>
            {d.best && <div className="text-terminal-bull">Best: {d.best.signal ?? "—"} · R {d.best.r_multiple ?? "—"} · {d.best.result}</div>}
            {d.worst && <div className="text-terminal-bear">Worst: {d.worst.signal ?? "—"} · R {d.worst.r_multiple ?? "—"} · {d.worst.result}</div>}
          </div>
        )}
        <div className="text-[11px] text-terminal-muted mt-2">🤖 {d.ai_status}</div>
        <div className="text-[10px] text-terminal-muted mt-1">{d.note}</div>
      </section>
    </div>
  );
}
