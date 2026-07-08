"use client";
// V27 §1 — AI Accuracy Report Card. Consolidated measured performance.
// Honest: BUILDING until ≥20 settled live trades. No fabricated numbers.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const pct = (n?: number | null) => (n === undefined || n === null ? "—" : `${n}%`);
const gradeTone = (g?: string) =>
  g === "A+" || g === "A" ? "text-terminal-bull" : g === "B" ? "text-terminal-warn"
  : g === "BUILDING" ? "text-terminal-muted" : "text-terminal-bear";

function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${tone ?? ""}`}>{value}</div>
    </div>
  );
}

export default function ReportCardPage() {
  const [r, setR] = useState<any>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const load = () => api.reportCard().then(setR).catch((e) => setErr(String(e?.message || e)));
    load();
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, []);

  if (err) return <div className="panel text-terminal-bear text-sm max-w-4xl mx-auto">Report card unavailable ({err})</div>;
  if (!r) return <div className="panel text-terminal-muted text-sm max-w-4xl mx-auto">Loading report card…</div>;

  const sc = r.scorecard || {};

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <section className="panel">
        <div className="flex items-center justify-between">
          <div className="panel-title mb-0">AI Accuracy Report Card ({r.samples} settled)</div>
          <div className={`text-3xl font-bold ${gradeTone(r.overall_rating)}`}>{r.overall_rating}</div>
        </div>
      </section>

      {r.notes?.length > 0 && (
        <div className="panel border-terminal-warn/40 text-terminal-warn text-xs py-2.5">{r.notes[0]}</div>
      )}

      <section className="panel">
        <div className="panel-title">Scorecard</div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <Stat label="Win Rate" value={pct(sc.win_rate)} tone={(sc.win_rate ?? 0) >= 55 ? "text-terminal-bull" : "text-terminal-warn"} />
          <Stat label="Entry Accuracy" value={pct(sc.entry_accuracy)} />
          <Stat label="Exit Quality" value={sc.exit_quality ?? "—"} tone={sc.exit_quality === "GOOD" ? "text-terminal-bull" : sc.exit_quality === "POOR" ? "text-terminal-bear" : "text-terminal-warn"} />
          <Stat label="Premium Capture" value={pct(sc.premium_capture_pct)} />
          <Stat label="Point Capture (MFE)" value={sc.point_capture_avg_pts != null ? `${sc.point_capture_avg_pts} pts` : "—"} tone="text-terminal-bull" />
          <Stat label="Avg Adverse (MAE)" value={sc.avg_adverse_pts != null ? `${sc.avg_adverse_pts} pts` : "—"} tone="text-terminal-bear" />
          <Stat label="False Signal Rate" value={pct(sc.false_signal_rate)} tone="text-terminal-warn" />
          <Stat label="Calibration" value={sc.calibration_grade != null ? `${sc.calibration_grade}/100` : "—"} />
          <Stat label="Brier" value={sc.brier ?? "—"} />
          <Stat label="Avg Entry Delay" value={sc.avg_entry_delay_sec != null ? `${sc.avg_entry_delay_sec}s` : "building"} tone="text-terminal-muted" />
        </div>
      </section>

      <div className="grid sm:grid-cols-2 gap-4">
        <section className="panel">
          <div className="panel-title">Best / Worst (this week)</div>
          <div className="text-sm space-y-1">
            <div className="text-terminal-bull">Best: {r.best_trade ? `${r.best_trade.signal ?? "—"} · ${r.best_trade.result} · R ${r.best_trade.r_multiple ?? "—"}` : "—"}</div>
            <div className="text-terminal-bear">Worst: {r.worst_trade ? `${r.worst_trade.signal ?? "—"} · ${r.worst_trade.result} · R ${r.worst_trade.r_multiple ?? "—"}` : "—"}</div>
          </div>
        </section>
        <section className="panel">
          <div className="panel-title">Opportunity</div>
          <div className="text-sm">Taken: {r.opportunity?.taken ?? 0} · Seen: {r.opportunity?.seen ?? "—"}</div>
          <div className="text-[11px] text-terminal-muted mt-1">{r.opportunity?.note}</div>
        </section>
      </div>

      <p className="text-[10px] text-terminal-muted text-center">{r.disclaimer}</p>
    </div>
  );
}
