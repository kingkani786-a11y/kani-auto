"use client";
// Phase 3 — Validation & Audit dashboard. Measures how well the EXISTING
// decisions performed (read-only; no engine/threshold changes).

import { useEffect, useState } from "react";

const pct = (n?: number | null) => (n === undefined || n === null ? "—" : `${n}%`);

function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className={`stat-value text-lg ${tone ?? ""}`}>{value}</div>
    </div>
  );
}
const accTone = (a?: number | null) =>
  a == null ? "" : a >= 60 ? "text-terminal-bull" : a >= 45 ? "text-terminal-warn" : "text-terminal-bear";

export default function AuditPage() {
  const [a, setA] = useState<any>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const load = () =>
      fetch("/api/audit", { headers: { "X-Auth-Token": localStorage.getItem("cat_token") || "" } })
        .then((r) => (r.ok ? r.json() : Promise.reject(r.status))).then(setA).catch((e) => setErr(String(e)));
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  if (err) return <div className="panel text-terminal-bear text-sm">Audit unavailable ({err})</div>;
  if (!a) return <div className="panel text-terminal-muted text-sm">Loading audit…</div>;

  const empty = (a.samples_settled ?? 0) === 0;
  const sc = a.scorecard || {};

  return (
    <div className="space-y-4 max-w-5xl mx-auto">
      {empty && (
        <div className="panel border-terminal-warn/40 text-terminal-warn text-xs py-2.5">
          Audit metrics populate as decisions are forward-tracked to outcome during market hours.
          Measurement only — no engine or threshold is changed by this layer.
        </div>
      )}

      {/* Scorecard */}
      <section className="panel">
        <div className="panel-title">Performance Scorecard ({a.samples_settled} settled · {a.samples_open} open)</div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <Stat label="Overall" value={pct(sc.overall_accuracy)} tone={accTone(sc.overall_accuracy)} />
          <Stat label="Entry" value={pct(sc.entry_accuracy)} tone={accTone(sc.entry_accuracy)} />
          <Stat label="Runner" value={pct(sc.runner_accuracy)} tone={accTone(sc.runner_accuracy)} />
          <Stat label="No-Trade" value={pct(sc.no_trade_accuracy)} tone={accTone(sc.no_trade_accuracy)} />
          <Stat label="Animal" value={pct(sc.animal_accuracy)} tone={accTone(sc.animal_accuracy)} />
          <Stat label="Decision" value={pct(sc.decision_accuracy)} tone={accTone(sc.decision_accuracy)} />
        </div>
      </section>

      {/* Decision distribution */}
      <section className="panel">
        <div className="panel-title">Decision Distribution ({a.total_decisions})</div>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          {["WAIT", "ENTER", "HOLD", "TRAIL", "EXIT"].map((k) => (
            <Stat key={k} label={k} value={a.distribution?.[k] ?? 0} />
          ))}
        </div>
      </section>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* Entry accuracy */}
        <section className="panel">
          <div className="panel-title">Entry Accuracy ({a.entry?.n ?? 0})</div>
          <div className="grid grid-cols-2 gap-4">
            <Stat label="Entry Accuracy" value={pct(a.entry?.entry_accuracy)} tone={accTone(a.entry?.entry_accuracy)} />
            <Stat label="Stop Loss Rate" value={pct(a.entry?.stop_loss_rate)} tone={accTone(100 - (a.entry?.stop_loss_rate ?? 0))} />
            <Stat label="Reached T1 / T2 / T3" value={`${pct(a.entry?.t1)} / ${pct(a.entry?.t2)} / ${pct(a.entry?.t3)}`} />
          </div>
        </section>

        {/* WAIT / No-Trade */}
        <section className="panel">
          <div className="panel-title">WAIT / No-Trade Audit ({a.wait?.n ?? 0})</div>
          <div className="grid grid-cols-2 gap-4">
            <Stat label="WAIT Accuracy" value={pct(a.wait?.wait_accuracy)} tone={accTone(a.wait?.wait_accuracy)} />
            <Stat label="Saved Loss" value={pct(a.wait?.saved_loss)} tone="text-terminal-bull" />
            <Stat label="False WAIT" value={pct(a.wait?.false_wait)} tone="text-terminal-warn" />
            <Stat label="Capital Saved" value={pct(a.no_trade?.capital_saved)} tone="text-terminal-bull" />
          </div>
        </section>

        {/* Runner */}
        <section className="panel">
          <div className="panel-title">Runner Detection ({a.runner?.n ?? 0} predicted)</div>
          <div className="grid grid-cols-2 gap-4">
            <Stat label="Runner Accuracy" value={pct(a.runner?.runner_accuracy)} tone={accTone(a.runner?.runner_accuracy)} />
            <Stat label="False Runner" value={pct(a.runner?.false_runner)} tone="text-terminal-warn" />
            <Stat label="Missed Runner" value={a.runner?.missed_runner ?? 0} />
          </div>
        </section>

        {/* Clarity + Data confidence */}
        <section className="panel">
          <div className="panel-title">Clarity & Data Confidence</div>
          <div className="grid grid-cols-2 gap-4 mb-2">
            <Stat label="Decision Clarity Acc." value={pct(a.clarity?.decision_clarity_accuracy)} tone={accTone(a.clarity?.decision_clarity_accuracy)} />
            <Stat label="Data Reliability" value={pct(a.data_confidence?.reliability)} tone={accTone(a.data_confidence?.reliability)} />
          </div>
          <div className="text-[11px] text-terminal-muted">
            {Object.entries(a.clarity?.by_label || {}).map(([k, v]: [string, any]) => `${k}: ${v.win_rate}% (${v.n})`).join("  ·  ") || "—"}
          </div>
        </section>
      </div>

      {/* Animal accuracy */}
      {a.animal?.by_animal && Object.keys(a.animal.by_animal).length > 0 && (
        <section className="panel">
          <div className="panel-title">Animal Classification Accuracy — {pct(a.animal.classification_accuracy)}</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            {Object.entries(a.animal.by_animal).map(([k, v]: [string, any]) => (
              <Stat key={k} label={k} value={`${pct(v.accuracy)} (${v.n})`} tone={accTone(v.accuracy)} />
            ))}
          </div>
        </section>
      )}

      {/* Module 4 — Accuracy Calibration + Phase 16 Brier forecast quality */}
      {a.calibration && (
        <section className="panel">
          <div className="panel-title">Accuracy Calibration (predicted vs realised)</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <Stat label="Calibration Score" value={a.calibration.calibration_score != null ? `${a.calibration.calibration_score}/100` : "—"} tone={accTone(a.calibration.calibration_score)} />
            <Stat label="Avg Error" value={a.calibration.error != null ? `${a.calibration.error} pts` : "—"} />
            <Stat label="Buckets Measured" value={a.calibration.buckets_measured ?? "—"} />
          </div>
          {a.calibration.note && <div className="text-[11px] text-terminal-muted mt-2">{a.calibration.note}</div>}

          {a.calibration.brier && (
            <div className="mt-3 pt-3 border-t border-terminal-border/40">
              <div className="stat-label mb-1">Forecast Quality — Brier Score (lower is better; 0.25 = no-skill)</div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <Stat label="Brier Score" value={a.calibration.brier.brier ?? "—"}
                      tone={a.calibration.brier.brier == null ? "" : a.calibration.brier.brier <= 0.18 ? "text-terminal-bull" : a.calibration.brier.brier <= 0.25 ? "text-terminal-warn" : "text-terminal-bear"} />
                <Stat label="Grade" value={a.calibration.brier.grade ?? "—"}
                      tone={a.calibration.brier.grade === "EXCELLENT" || a.calibration.brier.grade === "GOOD" ? "text-terminal-bull" : a.calibration.brier.grade === "POOR" ? "text-terminal-bear" : "text-terminal-warn"} />
                <Stat label="Skill vs Coin-Flip" value={a.calibration.brier.skill_pct != null ? `${a.calibration.brier.skill_pct}%` : "—"} tone={accTone(a.calibration.brier.skill_pct)} />
              </div>
              {a.calibration.brier.note && <div className="text-[11px] text-terminal-muted mt-2">{a.calibration.brier.note}</div>}
            </div>
          )}
        </section>
      )}

      {/* V25 §5/§10 — Execution Quality (MFE/MAE capture) */}
      {a.execution_quality && a.execution_quality.avg_mfe_pts !== undefined && (
        <section className="panel">
          <div className="panel-title">Execution Quality ({a.execution_quality.n} settled)</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <Stat label="Avg MFE" value={`${a.execution_quality.avg_mfe_pts} pts`} tone="text-terminal-bull" />
            <Stat label="Avg MAE" value={`${a.execution_quality.avg_mae_pts} pts`} tone="text-terminal-bear" />
            <Stat label="Avg Missed" value={`${a.execution_quality.avg_missed_pts} pts`} tone="text-terminal-warn" />
            <Stat label="Capture Eff." value={a.execution_quality.capture_efficiency_pct != null ? `${a.execution_quality.capture_efficiency_pct}%` : "—"} />
            <Stat label="Entry Quality" value={a.execution_quality.entry_quality} tone={a.execution_quality.entry_quality === "GOOD" ? "text-terminal-bull" : a.execution_quality.entry_quality === "POOR" ? "text-terminal-bear" : "text-terminal-warn"} />
            <Stat label="Exit Quality" value={a.execution_quality.exit_quality} tone={a.execution_quality.exit_quality === "GOOD" ? "text-terminal-bull" : a.execution_quality.exit_quality === "POOR" ? "text-terminal-bear" : "text-terminal-warn"} />
          </div>
        </section>
      )}

      {/* Module 5 — Engine Reliability (which engines to trust) */}
      {a.engine_reliability && Object.keys(a.engine_reliability).length > 0 && (
        <section className="panel">
          <div className="panel-title">Engine Reliability (self-learning weights)</div>
          <table className="w-full text-xs font-mono">
            <thead><tr className="stat-label text-left">
              {["Engine", "Samples", "Reliability", "Trust", "Weight"].map((h) => <th key={h} className="pb-2 pr-3 font-normal">{h}</th>)}
            </tr></thead>
            <tbody>
              {Object.entries(a.engine_reliability).map(([e, v]: [string, any]) => (
                <tr key={e} className="border-t border-terminal-border/40">
                  <td className="py-1.5 pr-3">{e}</td>
                  <td className="pr-3">{v.n}</td>
                  <td className={`pr-3 ${accTone(v.reliability)}`}>{v.reliability}%</td>
                  <td className={`pr-3 ${v.trust === "HIGH" ? "text-terminal-bull" : v.trust === "LOW" ? "text-terminal-bear" : "text-terminal-muted"}`}>{v.trust}</td>
                  <td className="pr-3">{v.weight}×</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="text-[11px] text-terminal-muted mt-2">Advisory — reliability weighting is measured here first; not auto-applied to the live gate yet.</div>
        </section>
      )}

      {/* Monthly report */}
      <section className="panel">
        <div className="panel-title">Report — Strengths, Weaknesses & Tuning</div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm mb-3">
          <Stat label="Best Setup" value={a.monthly_report?.best_signal_type ?? "—"} tone="text-terminal-bull" />
          <Stat label="Worst Setup" value={a.monthly_report?.worst_signal_type ?? "—"} tone="text-terminal-bear" />
          <Stat label="Most Reliable Regime" value={String(a.monthly_report?.most_reliable_regime ?? "—").replace(/_/g, " ")} tone="text-terminal-bull" />
          <Stat label="Least Reliable Regime" value={String(a.monthly_report?.least_reliable_regime ?? "—").replace(/_/g, " ")} tone="text-terminal-bear" />
        </div>
        <div className="stat-label mb-1">Recommended Threshold Adjustments (advisory — not auto-applied)</div>
        <ul className="text-xs text-gray-300 space-y-1">
          {(a.monthly_report?.recommended_threshold_adjustments || []).map((r: string, i: number) => (
            <li key={i} className="flex gap-2"><span className="text-terminal-accent">▸</span>{r}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
