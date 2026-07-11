"use client";
// AI Changelog (owner request) — what the AI OS shipped, derived from git
// history so it's verifiable against `git log` (not a hand-written claim).

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function AIChangelog() {
  const [d, setD] = useState<any>(null);
  useEffect(() => { api.aiChangelog(15).then(setD).catch(() => {}); }, []);
  if (!d) return null;
  const b = d.budget_today || {};

  return (
    <section className="panel space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">📋 AI Changelog</h2>
        <span className="text-[11px] text-terminal-muted">
          Today: {b.calls ?? 0} calls · ₹{b.cost_inr ?? 0} / ₹{b.cap_inr ?? 0}
        </span>
      </div>
      <ol className="space-y-1 max-h-64 overflow-auto text-xs">
        {(d.entries || []).map((e: any) => (
          <li key={e.commit} className="flex gap-2">
            <span className="text-terminal-muted tabular-nums shrink-0">{e.date}</span>
            <span className="text-terminal-accent tabular-nums shrink-0">{e.commit}</span>
            <span className="leading-snug">{e.summary}</span>
          </li>
        ))}
      </ol>
      <div className="text-[10px] text-terminal-muted">Derived from git history — verify with `git log`.</div>
    </section>
  );
}
