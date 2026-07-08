"use client";
// V: Signal Performance Analytics — analytics layer only (reads existing
// recorded outcomes). No trading logic touched.

import { useEffect, useState } from "react";

const fmt = (n?: number | null, s = "") =>
  n === undefined || n === null ? "—" : `${n}${s}`;

function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className={`stat-value text-lg ${tone ?? ""}`}>{value}</div>
    </div>
  );
}

const accTone = (a?: number | null) =>
  a == null ? "" : a >= 65 ? "text-terminal-bull" : a >= 50 ? "text-terminal-warn" : "text-terminal-bear";

export default function AnalyticsPage() {
  const [p, setP] = useState<any>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const load = () =>
      fetch("/api/analytics/performance", { headers: { "X-Auth-Token": localStorage.getItem("cat_token") || "" } })
        .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
        .then(setP).catch((e) => setErr(String(e)));
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  if (err) return <div className="panel text-terminal-bear text-sm">Failed to load analytics ({err})</div>;
  if (!p) return <div className="panel text-terminal-muted text-sm">Loading performance analytics…</div>;

  const empty = (p.validation?.signals_tested ?? 0) === 0;

  return (
    <div className="space-y-4 max-w-5xl mx-auto">
      {empty && (
        <div className="panel border-terminal-warn/40 text-terminal-warn text-xs py-2.5">
          No closed signals yet — these metrics populate automatically as the engine generates and
          resolves signals during market hours. (History persists across restarts only with Supabase configured.)
        </div>
      )}

      {/* TODAY / 7D / 30D */}
      <div className="grid lg:grid-cols-3 gap-4">
        <section className="panel">
          <div className="panel-title">Today</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            <Stat label="Signals Generated" value={fmt(p.today.generated)} />
            <Stat label="Closed" value={fmt(p.today.closed)} />
            <Stat label="Winning" value={fmt(p.today.wins)} tone="text-terminal-bull" />
            <Stat label="Losing" value={fmt(p.today.losses)} tone="text-terminal-bear" />
            <Stat label="Accuracy" value={fmt(p.today.accuracy, "%")} tone={accTone(p.today.accuracy)} />
            <Stat label="Avg R:R" value={p.today.avg_reward_risk != null ? `${p.today.avg_reward_risk} : 1` : "—"} />
          </div>
        </section>

        <section className="panel">
          <div className="panel-title">Last 7 Days</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            <Stat label="Total Signals" value={fmt(p.week.generated)} />
            <Stat label="Win Rate" value={fmt(p.week.accuracy, "%")} tone={accTone(p.week.accuracy)} />
            <Stat label="Avg Confidence" value={fmt(p.week.avg_confidence, "%")} />
            <Stat label="Net Points" value={fmt(p.week.net_points)} tone={(p.week.net_points ?? 0) >= 0 ? "text-terminal-bull" : "text-terminal-bear"} />
            <div className="col-span-2 text-xs text-terminal-muted">
              <div>Best: {p.week.best ? `${p.week.best.signal} · ${p.week.best.regime} · ${p.week.best.r_multiple}R` : "—"}</div>
              <div>Worst: {p.week.worst ? `${p.week.worst.signal} · ${p.week.worst.regime} · ${p.week.worst.r_multiple}R` : "—"}</div>
            </div>
          </div>
        </section>

        <section className="panel">
          <div className="panel-title">Last 30 Days</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            <Stat label="Total Trades" value={fmt(p.month.closed)} />
            <Stat label="Accuracy" value={fmt(p.month.accuracy, "%")} tone={accTone(p.month.accuracy)} />
            <Stat label="ROI Estimate" value={fmt(p.month.roi_estimate_pct, "%")} tone={(p.month.roi_estimate_pct ?? 0) >= 0 ? "text-terminal-bull" : "text-terminal-bear"} />
            <Stat label="Profit Factor" value={fmt(p.month.profit_factor)} />
            <Stat label="Risk Efficiency" value={p.month.risk_efficiency != null ? `${p.month.risk_efficiency}R/trade` : "—"} />
            <Stat label="Total R" value={fmt(p.month.total_r, "R")} />
          </div>
        </section>
      </div>

      {/* AI LEARNING INSIGHTS */}
      <section className="panel">
        <div className="panel-title">AI Learning Insights</div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="stat-label">Best Performing Setup</div>
            <div className="stat-value text-terminal-bull">{p.learning.by_setup.best ? `${p.learning.by_setup.best.name}` : "—"}</div>
            <div className="text-[11px] text-terminal-muted">{p.learning.by_setup.best ? `${p.learning.by_setup.best.win_rate}% · n=${p.learning.by_setup.best.n}` : "building"}</div>
          </div>
          <div>
            <div className="stat-label">Worst Performing Setup</div>
            <div className="stat-value text-terminal-bear">{p.learning.by_setup.worst ? `${p.learning.by_setup.worst.name}` : "—"}</div>
            <div className="text-[11px] text-terminal-muted">{p.learning.by_setup.worst ? `${p.learning.by_setup.worst.win_rate}% · n=${p.learning.by_setup.worst.n}` : "building"}</div>
          </div>
          <div>
            <div className="stat-label">Most Reliable Confidence</div>
            <div className="stat-value text-terminal-accent">{p.learning.by_confidence.most_reliable ?? "—"}</div>
            <div className="text-[11px] text-terminal-muted">
              {p.learning.by_confidence.most_reliable ? `${p.learning.by_confidence.buckets[p.learning.by_confidence.most_reliable].win_rate}% win` : "building"}
            </div>
          </div>
          <div>
            <div className="stat-label">Most Reliable Condition</div>
            <div className="stat-value text-terminal-accent">{p.learning.by_market_condition.best ? String(p.learning.by_market_condition.best.name).replace(/_/g, " ") : "—"}</div>
            <div className="text-[11px] text-terminal-muted">{p.learning.by_market_condition.best ? `${p.learning.by_market_condition.best.win_rate}% · n=${p.learning.by_market_condition.best.n}` : "building"}</div>
          </div>
        </div>
      </section>

      {/* HISTORICAL ACCURACY — last 30 / 100 + holding time */}
      {p.historical && (
        <section className="panel">
          <div className="panel-title">Historical Accuracy</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Stat label="Last 30 Accuracy" value={fmt(p.historical.last_30?.accuracy, "%")} tone={accTone(p.historical.last_30?.accuracy)} />
            <Stat label="Last 100 Accuracy" value={fmt(p.historical.last_100?.accuracy, "%")} tone={accTone(p.historical.last_100?.accuracy)} />
            <Stat label="Avg Hold (30)" value={p.historical.last_30?.avg_hold_min != null ? `${p.historical.last_30.avg_hold_min} min` : "—"} />
            <Stat label="Best / Worst Setup" value={`${p.historical.best_setup?.name ?? "—"} / ${p.historical.worst_setup?.name ?? "—"}`} />
          </div>
        </section>
      )}

      {/* SESSION INTELLIGENCE — win rate by session */}
      {p.learning?.by_session?.all && Object.keys(p.learning.by_session.all).length > 0 && (
        <section className="panel">
          <div className="panel-title">Session Intelligence</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            {Object.entries(p.learning.by_session.all).map(([s, v]: [string, any]) => (
              <Stat key={s} label={s.replace(/_/g, " ")} value={`${v.win_rate}% (${v.n})`} tone={accTone(v.win_rate)} />
            ))}
          </div>
        </section>
      )}

      {/* VALIDATION PANEL */}
      <section className="panel">
        <div className="panel-title">Signal Validation — Grade {p.validation.validation_grade ?? "—"}</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Stat label="Generated / Tested" value={`${fmt(p.validation.signals_generated)} / ${fmt(p.validation.signals_tested)}`} />
          <Stat label="Wins / Losses" value={`${fmt(p.validation.wins)} / ${fmt(p.validation.losses)}`} />
          <Stat label="Validation Accuracy" value={fmt(p.validation.validation_accuracy, "%")} tone={accTone(p.validation.validation_accuracy)} />
          <Stat label="Model Reliability" value={p.validation.model_reliability} />
        </div>
        <div className="text-[11px] text-terminal-muted mt-3">
          Open positions tracking: {p.validation.open_positions}. Outcomes are scored when price hits target or stop.
        </div>
      </section>
    </div>
  );
}
