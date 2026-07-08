"use client";
// PHASE 22 — WEIGHT APPROVAL ENGINE (human-in-the-loop).
// The nightly audit recommends engine-weight changes; nothing reaches the live
// gate until a human walks each one through QUEUE → APPROVE → SIMULATE → APPLY.
// Weights are NEVER auto-applied. Default = all 1.0 = current behaviour.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const STEPS = ["PENDING", "APPROVED", "SIMULATED", "APPLIED"];
const stepTone = (s: string, cur: string) => {
  const a = STEPS.indexOf(cur), b = STEPS.indexOf(s);
  if (cur === "REJECTED") return "text-terminal-bear";
  return b <= a && a >= 0 ? "text-terminal-bull" : "text-terminal-muted";
};

export default function WeightsPage() {
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState("");

  const load = () => api.weights().then(setD).catch((e) => setErr(String(e?.message || e)));
  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  async function act(action: any, wk?: string) {
    setBusy(`${action}:${wk ?? ""}`);
    try {
      if (action === "queue") await api.weightsQueue();
      else await api.weightAction(action, wk!);
      await load();
    } catch (e: any) {
      setErr(String(e?.message || e));
    } finally {
      setBusy("");
    }
  }

  if (err) return <div className="panel text-terminal-bear text-sm max-w-4xl mx-auto">Weight engine unavailable ({err})</div>;
  if (!d) return <div className="panel text-terminal-muted text-sm max-w-4xl mx-auto">Loading approval engine…</div>;

  const queue = d.queue || [];
  const applied = d.applied || [];

  const Btn = ({ label, action, wk, tone }: { label: string; action: any; wk: string; tone?: string }) => (
    <button onClick={() => act(action, wk)} disabled={!!busy}
      className={`text-[11px] px-2.5 py-1 rounded-md border disabled:opacity-40 ${tone ?? "border-terminal-border text-terminal-muted hover:text-white hover:border-terminal-accent"}`}>
      {busy === `${action}:${wk}` ? "…" : label}
    </button>
  );

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div className="panel border-terminal-warn/30 bg-terminal-warn/5 py-2.5 text-xs text-terminal-warn">
        Weights NEVER auto-apply. Each change needs human Approval → paper Simulation → production Apply.
        Default multiplier 1.0 = the current equal-weighted gate (no change).
      </div>

      <section className="panel">
        <div className="flex items-center justify-between mb-3">
          <div className="panel-title mb-0">Weight Approval Queue</div>
          <Btn label="Rebuild Queue from Reliability" action="queue" wk=""
               tone="border-terminal-accent/40 text-terminal-accent hover:bg-terminal-accent/10" />
        </div>
        {queue.length === 0 ? (
          <div className="text-sm text-terminal-muted">
            No pending changes. Recommendations queue only for engines with ≥{d.min_samples_for_queue} samples
            whose suggested weight differs from what's applied.
          </div>
        ) : (
          <div className="space-y-3">
            {queue.map((e: any) => (
              <div key={e.weight_key} className="border-t border-terminal-border/40 pt-2.5 first:border-0 first:pt-0">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <span className="font-bold text-sm">{e.engine}</span>
                    <span className="text-xs text-terminal-muted ml-2">
                      {e.current}× → <span className={e.suggested > 1 ? "text-terminal-bull" : e.suggested < 1 ? "text-terminal-bear" : ""}>{e.suggested}×</span>
                      {"  ·  "}reliability {e.reliability}% ({e.samples}) · conf {e.confidence}
                    </span>
                  </div>
                  <div className="flex gap-1.5">
                    {e.status === "PENDING" && <Btn label="Approve" action="approve" wk={e.weight_key} tone="border-terminal-bull/40 text-terminal-bull hover:bg-terminal-bull/10" />}
                    {e.status === "APPROVED" && <Btn label="Simulate" action="simulate" wk={e.weight_key} tone="border-terminal-accent/40 text-terminal-accent hover:bg-terminal-accent/10" />}
                    {e.status === "SIMULATED" && <Btn label="Apply" action="apply" wk={e.weight_key} tone="border-terminal-bull/60 text-terminal-bull hover:bg-terminal-bull/15 font-bold" />}
                    {e.status !== "REJECTED" && <Btn label="Reject" action="reject" wk={e.weight_key} tone="border-terminal-bear/40 text-terminal-bear hover:bg-terminal-bear/10" />}
                  </div>
                </div>
                {/* workflow tracker */}
                <div className="flex items-center gap-1.5 mt-1.5 text-[10px] font-mono">
                  {STEPS.map((s, i) => (
                    <span key={s} className="flex items-center gap-1.5">
                      <span className={stepTone(s, e.status)}>{s}</span>
                      {i < STEPS.length - 1 && <span className="text-terminal-border">→</span>}
                    </span>
                  ))}
                </div>
                <div className="text-[11px] text-terminal-muted mt-1">{e.reason}</div>
                {e.simulation && (
                  <div className="text-[11px] text-gray-300 mt-1 bg-terminal-bg/60 rounded px-2 py-1">
                    Paper sim — baseline {e.simulation.baseline_win_rate}% · engine-pass {e.simulation.engine_pass_win_rate}%
                    ({e.simulation.pass_samples}) · est. impact {e.simulation.estimated_impact} pts.
                    <span className="text-terminal-muted"> {e.simulation.note}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-title">Applied Weights (live in the confluence gate)</div>
        {applied.length === 0 ? (
          <div className="text-sm text-terminal-muted">None applied — the gate is equal-weighted (every engine 1.0×).</div>
        ) : (
          <table className="w-full text-xs font-mono">
            <thead><tr className="stat-label text-left">
              {["Engine", "Multiplier", "Status", "Action"].map((h) => <th key={h} className="pb-2 pr-3 font-normal">{h}</th>)}
            </tr></thead>
            <tbody>
              {applied.map((e: any) => (
                <tr key={e.weight_key} className="border-t border-terminal-border/40">
                  <td className="py-1.5 pr-3">{e.engine}</td>
                  <td className={`pr-3 font-bold ${e.multiplier > 1 ? "text-terminal-bull" : e.multiplier < 1 ? "text-terminal-bear" : ""}`}>{e.multiplier}×</td>
                  <td className="pr-3">{e.status}</td>
                  <td className="pr-3"><Btn label="Revert to 1.0×" action="revert" wk={e.weight_key} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="text-[10px] text-terminal-muted mt-2">{d.note}</div>
      </section>
    </div>
  );
}
