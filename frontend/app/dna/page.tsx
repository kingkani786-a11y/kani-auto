"use client";
// PHASE 20 — MARKET DNA. Historical-similarity layer: the current setup matched
// against stored historical outcomes. Probabilities, never certainty. Shows
// "Insufficient DNA" until ≥10 comparable sessions exist (no guessing).

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const fmt = (n?: number | null) =>
  n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: 1 });

const verdictTone = (v?: string) =>
  v === "VERY STRONG MATCH" || v === "STRONG MATCH" ? "text-terminal-bull"
  : v === "MODERATE MATCH" ? "text-terminal-warn" : "text-terminal-muted";
const riskTone = (r?: string) =>
  r === "LOW" ? "text-terminal-bull" : r === "HIGH" ? "text-terminal-bear" : "text-terminal-warn";

function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${tone ?? ""}`}>{value}</div>
    </div>
  );
}

export default function DnaPage() {
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const load = () => api.marketDna().then(setD).catch((e) => setErr(String(e?.message || e)));
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  if (err) return <div className="panel text-terminal-bear text-sm max-w-3xl mx-auto">Market DNA unavailable ({err})</div>;
  if (!d) return <div className="panel text-terminal-muted text-sm max-w-3xl mx-auto">Loading Market DNA…</div>;

  if (!d.ready) {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <div className="panel border-terminal-warn/40">
          <div className="panel-title text-terminal-warn">Insufficient DNA</div>
          <div className="text-sm text-gray-200">
            {d.note || "Not enough comparable historical sessions yet."}
          </div>
          <div className="text-xs text-terminal-muted mt-2">
            DNA needs ≥10 similar stored sessions before it draws conclusions — no guessing.
            It accumulates as the system runs (and persists permanently with Supabase).
          </div>
        </div>
      </div>
    );
  }

  const p = d.prediction || {};

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      {/* Headline */}
      <section className="panel">
        <div className="panel-title">Market DNA — historical similarity</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Stat label="Match Score" value={`${fmt(d.match_score)}%`} tone={verdictTone(d.verdict)} />
          <Stat label="Verdict" value={d.verdict} tone={verdictTone(d.verdict)} />
          <Stat label="Historical Win Rate" value={`${fmt(d.historical_win_rate)}%`}
                tone={(d.historical_win_rate ?? 0) >= 55 ? "text-terminal-bull" : "text-terminal-warn"} />
          <Stat label="Risk Rating" value={d.risk_rating} tone={riskTone(d.risk_rating)} />
        </div>
      </section>

      {/* DNA stats */}
      <section className="panel">
        <div className="panel-title">What usually happens ({d.samples} similar sessions)</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Stat label="Avg Premium Expansion" value={d.avg_premium_expansion_pct != null ? `${fmt(d.avg_premium_expansion_pct)}%` : "—"} />
          <Stat label="Avg Duration" value={d.avg_duration_min != null ? `${fmt(d.avg_duration_min)} min` : "—"} />
          <Stat label="Best Strike" value={d.best_strike ?? "—"} tone="text-terminal-bull" />
          <Stat label="Worst Strike" value={d.worst_strike ?? "—"} tone="text-terminal-bear" />
          <Stat label="Most Common Outcome" value={d.most_common_outcome}
                tone={d.most_common_outcome === "WIN" ? "text-terminal-bull" : "text-terminal-bear"} />
          <Stat label="Avg R-Multiple" value={fmt(d.avg_r_multiple)}
                tone={(d.avg_r_multiple ?? 0) > 0 ? "text-terminal-bull" : "text-terminal-bear"} />
        </div>
      </section>

      {/* DNA prediction */}
      <section className="panel">
        <div className="panel-title">DNA Prediction (probabilistic)</div>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          <Stat label="Direction" value={p.expected_direction ?? "—"}
                tone={p.expected_direction === "BULL" ? "text-terminal-bull" : p.expected_direction === "BEAR" ? "text-terminal-bear" : ""} />
          <Stat label="Expected Range" value={p.expected_range_pts != null ? `${fmt(p.expected_range_pts)} pts` : "—"} />
          <Stat label="Premium Exp." value={p.expected_premium_expansion_pct != null ? `${fmt(p.expected_premium_expansion_pct)}%` : "—"} />
          <Stat label="Duration" value={p.expected_duration_min != null ? `${fmt(p.expected_duration_min)} min` : "—"} />
          <Stat label="Probability" value={p.expected_probability != null ? `${fmt(p.expected_probability)}%` : "—"} />
        </div>
      </section>

      {/* Similar days */}
      <section className="panel">
        <div className="panel-title">Similar Sessions (top {d.similar_days?.length ?? 0})</div>
        <table className="w-full text-xs font-mono">
          <thead><tr className="stat-label text-left">
            {["Date", "Match", "Result", "Prem. Exp", "R", "Regime", "Outcome"].map((h) => (
              <th key={h} className="pb-2 pr-3 font-normal">{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {(d.similar_days || []).map((s: any, i: number) => (
              <tr key={i} className="border-t border-terminal-border/40">
                <td className="py-1.5 pr-3">{s.date}</td>
                <td className="pr-3">{fmt(s.match)}%</td>
                <td className={`pr-3 ${s.result === "WIN" ? "text-terminal-bull" : "text-terminal-bear"}`}>{s.result}</td>
                <td className="pr-3">{s.premium_expansion != null ? `${fmt(s.premium_expansion)}%` : "—"}</td>
                <td className="pr-3">{fmt(s.r_multiple)}</td>
                <td className="pr-3">{String(s.regime ?? "—").replace(/_/g, " ")}</td>
                <td className="pr-3">{s.outcome}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <p className="text-[10px] text-terminal-muted text-center">{d.note}</p>
    </div>
  );
}
