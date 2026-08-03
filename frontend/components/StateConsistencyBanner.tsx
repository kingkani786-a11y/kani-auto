"use client";
// STATE CONSISTENCY BANNER — P5A (owner, 2026-08-03, "State Consistency").
//
// Why this exists: this session's audits kept finding the SAME bug shape —
// a duplicated fact with no single source of truth (state.data_quality vs
// data_quality.report().overall; Kill Switch/Safe Mode/Gate echoing one
// cause three ways; Order Flow's low-data default sharing its real
// baseline). Each instance needed a fresh manual trace to find. This panel
// is the runtime version of that trace: it polls the backend's own
// cross-check (state_consistency.py) and says "state inconsistency
// detected" itself, instead of waiting for the next dashboard review to
// notice by hand.
//
// Quiet by default — renders nothing when the backend reports everything
// consistent (which is true almost all the time; this is a rare-alarm
// panel, not a status strip). No gate, no decision, no engine touched:
// state_consistency.py only reads two existing values and compares them.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function StateConsistencyBanner() {
  const [r, setR] = useState<any>(null);
  useEffect(() => {
    const load = () => api.stateConsistency?.().then(setR).catch(() => {});
    load();
    const id = setInterval(load, 20000);
    return () => clearInterval(id);
  }, []);

  if (!r || r.consistent) return null;

  const bad = (r.checks || []).filter((c: any) => !c.consistent);

  return (
    <div className="panel border-2 border-terminal-bear/70 bg-terminal-bear/5 py-2.5 space-y-1.5 text-[11px]">
      <div className="flex items-center gap-2 font-bold tracking-wider text-terminal-bear">
        <span>⚠</span>
        <span>STATE INCONSISTENCY DETECTED</span>
      </div>
      <div className="space-y-1">
        {bad.map((c: any) => (
          <div key={c.name} className="text-gray-200">
            <span className="font-semibold">{c.label}</span>
            <span className="text-terminal-muted">
              {" "}— {c.source_a} says <span className="text-white font-semibold">{c.value_a}</span>,
              {" "}{c.source_b} says <span className="text-white font-semibold">{c.value_b}</span>
            </span>
            <div className="text-terminal-muted mt-0.5">{c.note}</div>
          </div>
        ))}
      </div>
      <div className="text-[10px] text-terminal-muted pt-1 border-t border-terminal-border/40">
        Two independent readings of the same fact disagree — treat any panel
        reading only one of them as unverified until this clears. Detection
        only, changes no gate or decision.
      </div>
    </div>
  );
}
