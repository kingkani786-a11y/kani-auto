"use client";
// PHASE 31 — AUTONOMOUS RESEARCH LAB. Live self-diagnosis of the running system
// from real runtime signals. Evidence-based; no fabricated static analysis.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const sevTone = (s: string) =>
  s === "CRITICAL" || s === "HIGH" ? "text-terminal-bear"
  : s === "MEDIUM" ? "text-terminal-warn" : s === "LOW" ? "text-terminal-muted" : "text-terminal-accent";
const sevBorder = (s: string) =>
  s === "CRITICAL" || s === "HIGH" ? "border-terminal-bear/40"
  : s === "MEDIUM" ? "border-terminal-warn/40" : "border-terminal-border";

export default function ResearchPage() {
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const load = () => api.research().then(setD).catch((e) => setErr(String(e?.message || e)));
    load();
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, []);

  if (err) return <div className="panel text-terminal-bear text-sm max-w-4xl mx-auto">Research Lab unavailable ({err})</div>;
  if (!d) return <div className="panel text-terminal-muted text-sm max-w-4xl mx-auto">Running self-diagnosis…</div>;

  const c = d.counts || {};
  const bucket = (title: string, items: string[], tone: string) => (
    <div>
      <div className={`stat-label mb-1 ${tone}`}>{title}</div>
      <ul className="space-y-0.5 text-gray-300 text-xs">
        {(items || []).map((it, i) => <li key={i} className="flex gap-1.5"><span className={tone}>▸</span>{it}</li>)}
      </ul>
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* Severity rollup */}
      <section className="panel">
        <div className="panel-title">Autonomous Research Lab — self-diagnosis</div>
        <div className="grid grid-cols-5 gap-3 text-center">
          {["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"].map((s) => (
            <div key={s}>
              <div className={`text-2xl font-bold ${sevTone(s)}`}>{c[s] ?? 0}</div>
              <div className="stat-label">{s}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Findings */}
      <section className="panel">
        <div className="panel-title">Findings</div>
        <div className="space-y-2">
          {(d.findings || []).map((f: any, i: number) => (
            <div key={i} className={`border-l-2 pl-3 ${sevBorder(f.severity)}`}>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold ${sevTone(f.severity)}`}>{f.severity}</span>
                <span className="text-[11px] text-terminal-muted">{f.area}</span>
              </div>
              <div className="text-sm">{f.finding}</div>
              <div className="text-[11px] text-terminal-muted mt-0.5">→ {f.recommendation}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Buckets */}
      <section className="panel">
        <div className="panel-title">Research Summary</div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {bucket("What Worked", d.what_worked, "text-terminal-bull")}
          {bucket("What Failed", d.what_failed, "text-terminal-bear")}
          {bucket("What Regressed", d.what_regressed, "text-terminal-warn")}
          {bucket("What To Upgrade", d.what_to_upgrade, "text-terminal-accent")}
          {bucket("What To Disable", d.what_to_disable, "text-terminal-bear")}
          {bucket("What To Monitor", d.what_to_monitor, "text-terminal-muted")}
        </div>
      </section>

      <p className="text-[10px] text-terminal-muted text-center">{d.note}</p>
    </div>
  );
}
