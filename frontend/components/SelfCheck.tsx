"use client";
// V23 — AI Self-Check. One consolidated readiness list (broker, feed, quotes,
// candles, futures, chain, greeks, AI brain, database). Reads /api/self-check
// (real reachability/heartbeat facts, no fabrication). Collapses to a single
// green line when everything is READY; expands when a subsystem needs attention.

import { useEffect, useState } from "react";

export function SelfCheck() {
  const [d, setD] = useState<any>(null);
  useEffect(() => {
    const load = () =>
      fetch("/api/self-check", { headers: { "X-Auth-Token": localStorage.getItem("cat_token") || "" } })
        .then((r) => (r.ok ? r.json() : null)).then(setD).catch(() => {});
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  if (!d?.checks) return null;
  const bad = d.checks.filter((c: any) => c.status !== "OK");
  const tone = (s: string) => s === "OK" ? "text-terminal-bull" : s === "FAIL" ? "text-terminal-bear" : "text-terminal-warn";
  const mark = (s: string) => s === "OK" ? "✅" : s === "FAIL" ? "❌" : "⏳";

  // all-green ⇒ compact one-liner
  if (d.ready && bad.length === 0) {
    return (
      <div className="panel py-1.5 text-[11px] flex items-center gap-2">
        <span className="font-bold tracking-wider text-terminal-bull">🩺 AI SELF-CHECK</span>
        <span className="text-terminal-bull">✅ All {d.checks.length} subsystems READY</span>
      </div>
    );
  }
  return (
    <div className="panel py-2 border-terminal-warn/40">
      <div className="flex items-center justify-between text-[11px] mb-1">
        <span className="font-bold tracking-wider text-terminal-accent">🩺 AI SELF-CHECK</span>
        <span className={d.ready ? "text-terminal-bull" : "text-terminal-warn"}>{d.summary}</span>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px]">
        {d.checks.map((c: any) => (
          <span key={c.name} title={c.detail}>
            {mark(c.status)} <span className={tone(c.status)}>{c.name}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
