"use client";
// PHASE 29 — TODAY + TOMORROW SIMULATOR. Scenario projections (Bull/Bear/Range
// today; Gap-Up/Gap-Down/Flat tomorrow) with probability, expected move, target
// zone, risk. Derivation-only; probabilities, never certainty.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const scTone = (s?: string) =>
  s?.includes("BULL") || s === "GAP UP" ? "text-terminal-bull"
  : s?.includes("BEAR") || s === "GAP DOWN" ? "text-terminal-bear" : "text-terminal-warn";
const riskTone = (r?: string) =>
  r === "LOW" ? "text-terminal-bull" : r === "HIGH" ? "text-terminal-bear" : "text-terminal-warn";

function ScenarioCard({ s }: { s: any }) {
  return (
    <div className="panel">
      <div className="flex items-center justify-between">
        <span className={`font-bold ${scTone(s.scenario)}`}>{s.scenario}</span>
        <span className="font-mono text-sm">{s.probability}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-terminal-bg overflow-hidden my-2">
        <div className="h-full bg-terminal-accent" style={{ width: `${s.probability}%` }} />
      </div>
      <div className="text-[11px] text-terminal-muted flex justify-between">
        <span>Move ≈ {s.expected_move}</span>
        <span className={riskTone(s.risk)}>{s.risk} risk</span>
      </div>
      <div className="text-[11px] text-terminal-muted mt-0.5">
        Zone {s.target_zone?.[0]?.toLocaleString("en-IN")} – {s.target_zone?.[1]?.toLocaleString("en-IN")}
      </div>
    </div>
  );
}

export default function SimulatorPage() {
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const load = () => api.simulator().then(setD).catch((e) => setErr(String(e?.message || e)));
    load();
    const t = setInterval(load, 12000);
    return () => clearInterval(t);
  }, []);

  if (err) return <div className="panel text-terminal-bear text-sm max-w-4xl mx-auto">Simulator unavailable ({err})</div>;
  if (!d) return <div className="panel text-terminal-muted text-sm max-w-4xl mx-auto">Loading simulator…</div>;
  if (!d.ready)
    return <div className="panel text-terminal-muted text-sm max-w-4xl mx-auto">{d.note || "No live analysis yet — connect and let the AI cycle run."}</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* Ranking */}
      <section className="panel">
        <div className="panel-title">Scenario Ranking</div>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="stat-label">Most Likely</div>
            <div className={`stat-value ${scTone(d.most_likely?.scenario)}`}>{d.most_likely?.scenario} ({d.most_likely?.probability}%)</div>
          </div>
          <div>
            <div className="stat-label">Second Likely</div>
            <div className={`stat-value ${scTone(d.second_likely?.scenario)}`}>{d.second_likely?.scenario} ({d.second_likely?.probability}%)</div>
          </div>
          <div>
            <div className="stat-label">Worst Case</div>
            <div className={`stat-value ${scTone(d.worst_case?.scenario)}`}>{d.worst_case?.scenario} ({d.worst_case?.probability}%)</div>
          </div>
        </div>
      </section>

      <div>
        <div className="stat-label mb-2">TODAY</div>
        <div className="grid sm:grid-cols-3 gap-3">
          {d.today.map((s: any) => <ScenarioCard key={s.scenario} s={s} />)}
        </div>
      </div>

      <div>
        <div className="stat-label mb-2">TOMORROW · bias {d.tomorrow_bias}</div>
        <div className="grid sm:grid-cols-3 gap-3">
          {d.tomorrow.map((s: any) => <ScenarioCard key={s.scenario} s={s} />)}
        </div>
      </div>

      <p className="text-[10px] text-terminal-muted text-center">{d.note}</p>
    </div>
  );
}
