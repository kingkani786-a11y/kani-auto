"use client";
// PHASE 21 — EVOLUTION CENTER. Self-analysis dashboard: the system audits its
// own measured outcomes (accuracy, calibration, Brier, engine reliability, DNA)
// and produces a ranked, data-derived upgrade list + a system grade.
// Advisory only — nothing here auto-changes the live trading gate.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const fmt = (n?: number | null) => (n === undefined || n === null ? "—" : `${n}`);

const gradeTone = (g?: string) =>
  g === "A+" || g === "A" ? "text-terminal-bull" : g === "B" ? "text-terminal-warn"
  : g === "BUILDING" ? "text-terminal-muted" : "text-terminal-bear";
const statusTone = (s?: string) =>
  s === "HIGH" ? "text-terminal-bull" : s === "DISABLE" || s === "LOW" ? "text-terminal-bear" : "text-terminal-warn";
const impactTone = (i?: string) =>
  i === "Risk" ? "text-terminal-bear" : i === "Accuracy" || i === "Calibration" ? "text-terminal-accent"
  : i === "Profit" ? "text-terminal-bull" : "text-terminal-muted";

function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${tone ?? ""}`}>{value}</div>
    </div>
  );
}

const PERIODS = ["daily", "weekly", "monthly"];

export default function EvolutionPage() {
  const [period, setPeriod] = useState("weekly");
  const [r, setR] = useState<any>(null);
  const [err, setErr] = useState("");

  const [running, setRunning] = useState(false);

  useEffect(() => {
    const load = () => api.evolution(period).then(setR).catch((e) => setErr(String(e?.message || e)));
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [period]);

  async function runNightly() {
    setRunning(true);
    try { await api.runNightly(); await api.evolution(period).then(setR); } catch {}
    setRunning(false);
  }

  if (err) return <div className="panel text-terminal-bear text-sm max-w-5xl mx-auto">Evolution Center unavailable ({err})</div>;
  if (!r) return <div className="panel text-terminal-muted text-sm max-w-5xl mx-auto">Loading Evolution Center…</div>;

  const ov = r.overview || {};
  const cal = r.calibration_analysis || {};
  const brain = r.brain_analysis || {};
  const dna = r.dna_analysis || {};

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      {/* Header + period + grade */}
      <section className="panel">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="panel-title mb-0">Evolution Center — system self-analysis</div>
          <div className="flex items-center gap-3">
            <div className="flex gap-0.5 bg-terminal-bg rounded-lg p-0.5 border border-terminal-border">
              {PERIODS.map((p) => (
                <button key={p} onClick={() => setPeriod(p)}
                  className={`px-3 py-1 text-[11px] rounded-md capitalize transition-colors ${
                    period === p ? "bg-terminal-accent text-black font-bold" : "text-terminal-muted hover:text-white"}`}>
                  {p}
                </button>
              ))}
            </div>
            <button onClick={runNightly} disabled={running}
              className="text-[11px] px-3 py-1.5 rounded-lg border border-terminal-border text-terminal-muted hover:border-terminal-accent hover:text-white disabled:opacity-50">
              {running ? "Running…" : "Run Nightly Audit"}
            </button>
            <div className="text-right">
              <div className="stat-label">System Grade</div>
              <div className={`text-2xl font-bold ${gradeTone(r.system_grade)}`}>{r.system_grade}</div>
            </div>
          </div>
        </div>
        <div className="text-[10px] text-terminal-muted mt-2">
          Nightly self-tuning audit runs automatically at 23:59 IST. Recommendations only — weight
          changes require human approval (Measure → Validate → Upgrade → Deploy).
        </div>
      </section>

      {/* Roadmap tracker */}
      {r.roadmap && (
        <section className="panel">
          <div className="flex items-center justify-between mb-2">
            <div className="panel-title mb-0">Roadmap — {r.roadmap.completion_pct}% complete</div>
            <div className="text-xs text-terminal-muted">Next: <span className="text-terminal-accent">{r.roadmap.next_recommended}</span></div>
          </div>
          <div className="h-2 rounded-full bg-terminal-bg overflow-hidden mb-3">
            <div className="h-full bg-terminal-bull" style={{ width: `${r.roadmap.completion_pct}%` }} />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {r.roadmap.items.map((it: any) => (
              <span key={it.phase}
                className={`text-[10px] px-2 py-1 rounded-md border ${
                  it.status === "COMPLETED" ? "border-terminal-bull/40 text-terminal-bull"
                  : it.status === "BLOCKED" ? "border-terminal-bear/40 text-terminal-bear"
                  : "border-terminal-warn/40 text-terminal-warn"}`}>
                P{it.phase} {it.name}
              </span>
            ))}
          </div>
          <div className="text-[10px] text-terminal-muted mt-2">{r.roadmap.note}</div>
        </section>
      )}

      {/* Overview */}
      <section className="panel">
        <div className="panel-title">Overview</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4">
          <Stat label="Total Signals" value={fmt(ov.total_signals)} />
          <Stat label="Settled" value={fmt(ov.settled)} />
          <Stat label="Win Rate" value={ov.win_rate != null ? `${ov.win_rate}%` : "—"}
                tone={(ov.win_rate ?? 0) >= 55 ? "text-terminal-bull" : "text-terminal-warn"} />
          <Stat label="Loss Rate" value={ov.loss_rate != null ? `${ov.loss_rate}%` : "—"} tone="text-terminal-bear" />
          <Stat label="Avg RR" value={fmt(ov.avg_rr)} />
          <Stat label="Best Session" value={ov.best_session?.name ? `${ov.best_session.name} (${ov.best_session.win_rate}%)` : "—"} tone="text-terminal-bull" />
          <Stat label="Best Day" value={ov.best_day ? `${ov.best_day.date} (+${ov.best_day.pnl})` : "—"} tone="text-terminal-bull" />
          <Stat label="Worst Day" value={ov.worst_day ? `${ov.worst_day.date} (${ov.worst_day.pnl})` : "—"} tone="text-terminal-bear" />
          <Stat label="Worst Session" value={ov.worst_session?.name ? `${ov.worst_session.name} (${ov.worst_session.win_rate}%)` : "—"} tone="text-terminal-bear" />
        </div>
      </section>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* Calibration */}
        <section className="panel">
          <div className="panel-title">Calibration Analysis</div>
          <div className="grid grid-cols-2 gap-4">
            <Stat label="Calibration Score" value={cal.calibration_score != null ? `${cal.calibration_score}/100` : "—"} />
            <Stat label="Grade" value={cal.grade} tone={gradeTone(cal.grade)} />
            <Stat label="Error" value={cal.error_pct != null ? `${cal.error_pct} pts` : "—"} />
            <Stat label="Actual Win Rate" value={cal.actual_win_rate != null ? `${cal.actual_win_rate}%` : "—"} />
            <Stat label="Brier" value={fmt(cal.brier)} />
            <Stat label="Brier Grade" value={cal.brier_grade ?? "—"} />
          </div>
        </section>

        {/* Brain + DNA */}
        <section className="panel space-y-3">
          <div>
            <div className="panel-title">Brain Analysis</div>
            <div className="text-sm mb-1">{brain.verdict}</div>
            <div className="text-[11px] text-terminal-muted">
              Avg confidence {fmt(brain.avg_confidence)}% vs actual {fmt(brain.actual_win_rate)}%
              {brain.confidence_gap != null ? ` (gap ${brain.confidence_gap})` : ""}.
              {brain.loss_regime ? ` Worst regime: ${String(brain.loss_regime).replace(/_/g, " ")} (${brain.loss_regime_win_rate}%).` : ""}
            </div>
          </div>
          <div className="pt-2 border-t border-terminal-border/40">
            <div className="panel-title">DNA Analysis</div>
            {dna.ready ? (
              <div className="grid grid-cols-2 gap-3">
                <Stat label="Avg Match" value={`${fmt(dna.avg_match_score)}%`} />
                <Stat label="Verdict" value={dna.verdict} />
                <Stat label="Strongest" value={dna.strongest_match != null ? `${dna.strongest_match}%` : "—"} />
                <Stat label="Weakest" value={dna.weakest_match != null ? `${dna.weakest_match}%` : "—"} />
              </div>
            ) : (
              <div className="text-xs text-terminal-muted">{dna.note}</div>
            )}
          </div>
        </section>
      </div>

      {/* Engine analysis */}
      <section className="panel">
        <div className="panel-title">Engine Analysis</div>
        <table className="w-full text-xs font-mono">
          <thead><tr className="stat-label text-left">
            {["Engine", "Reliability", "Trust", "Samples", "Weight", "Status", "Recommendation"].map((h) => (
              <th key={h} className="pb-2 pr-3 font-normal">{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {(r.engine_analysis || []).map((e: any) => (
              <tr key={e.engine} className="border-t border-terminal-border/40">
                <td className="py-1.5 pr-3">{e.engine}</td>
                <td className="pr-3">{e.reliability}%</td>
                <td className="pr-3">{e.trust}</td>
                <td className="pr-3">{e.samples}</td>
                <td className="pr-3">{e.weight}×</td>
                <td className={`pr-3 font-bold ${statusTone(e.status)}`}>{e.status}</td>
                <td className="pr-3 text-terminal-muted">{e.recommendation}</td>
              </tr>
            ))}
            {(!r.engine_analysis || r.engine_analysis.length === 0) && (
              <tr><td colSpan={7} className="py-3 text-terminal-muted">Building — engine reliability fills in as trades settle.</td></tr>
            )}
          </tbody>
        </table>
      </section>

      {/* Weight Recommendation Engine (advisory — human approval required) */}
      {!!r.weight_recommendations?.length && (
        <section className="panel">
          <div className="panel-title">Weight Recommendations — require human approval (not auto-applied)</div>
          <table className="w-full text-xs font-mono">
            <thead><tr className="stat-label text-left">
              {["Engine", "Current", "Suggested", "Δ", "Confidence", "Reason"].map((h) => (
                <th key={h} className="pb-2 pr-3 font-normal">{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {r.weight_recommendations.map((w: any) => (
                <tr key={w.engine} className="border-t border-terminal-border/40">
                  <td className="py-1.5 pr-3">{w.engine}</td>
                  <td className="pr-3">{w.current_weight}×</td>
                  <td className={`pr-3 font-bold ${w.delta > 0 ? "text-terminal-bull" : w.delta < 0 ? "text-terminal-bear" : "text-terminal-muted"}`}>{w.suggested_weight}×</td>
                  <td className={`pr-3 ${w.delta > 0 ? "text-terminal-bull" : w.delta < 0 ? "text-terminal-bear" : "text-terminal-muted"}`}>
                    {w.delta > 0 ? "+" : ""}{w.delta}
                  </td>
                  <td className="pr-3">{w.confidence}</td>
                  <td className="pr-3 text-terminal-muted">{w.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* Report narrative buckets */}
      {r.narrative && (
        <section className="panel">
          <div className="panel-title">Report — What Worked / Failed / To Do</div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
            {([
              ["What Worked", r.narrative.what_worked, "text-terminal-bull"],
              ["What Failed", r.narrative.what_failed, "text-terminal-bear"],
              ["What To Improve", r.narrative.what_to_improve, "text-terminal-warn"],
              ["What To Disable", r.narrative.what_to_disable, "text-terminal-bear"],
              ["What To Upgrade", r.narrative.what_to_upgrade, "text-terminal-accent"],
              ["What To Monitor", r.narrative.what_to_monitor, "text-terminal-muted"],
            ] as [string, string[], string][]).map(([title, items, tone]) => (
              <div key={title}>
                <div className={`stat-label mb-1 ${tone}`}>{title}</div>
                <ul className="space-y-0.5 text-gray-300">
                  {(items || []).map((it, i) => <li key={i} className="flex gap-1.5"><span className={tone}>▸</span>{it}</li>)}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Top 10 upgrades */}
      <section className="panel">
        <div className="panel-title">Top {r.recommendations?.length ?? 0} Upgrade Recommendations</div>
        <div className="space-y-2">
          {(r.recommendations || []).map((rec: any) => (
            <div key={rec.priority} className="flex items-start gap-3 border-t border-terminal-border/40 pt-2 first:border-0 first:pt-0">
              <span className="text-terminal-accent font-bold text-sm w-6">{rec.priority}</span>
              <div className="flex-1">
                <div className="text-sm">{rec.title}</div>
                <div className="text-[11px] text-terminal-muted flex gap-3 mt-0.5">
                  <span>Gain: {rec.expected_gain}</span>
                  <span>Difficulty: {rec.difficulty}</span>
                  <span className={impactTone(rec.impact)}>Impact: {rec.impact}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <p className="text-[10px] text-terminal-muted text-center">{r.disclaimer}</p>
    </div>
  );
}
