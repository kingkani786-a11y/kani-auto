"use client";
// AI Timeline (AI Journal, FAIOS) — the day's market story, timestamped.
// Glance after 30 min away → understand the whole session. Engine transitions
// only (recorded server-side each AI cycle); the AI narrates, never decides.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const ICON: Record<string, string> = {
  session: "🎙", trend: "📈", structure: "🏗", liquidity: "💧",
  entry: "🎯", wait: "⏸", decision: "🧭", target: "✅", exit: "🚪",
};

export function AITimelineCard() {
  const [t, setT] = useState<any>(null);

  useEffect(() => {
    const load = () => api.aiTimeline(40).then(setT).catch(() => {});
    load();
    const id = setInterval(load, 20000);
    return () => clearInterval(id);
  }, []);

  const events: any[] = t?.events || [];

  return (
    <section className="panel space-y-2">
      <h2 className="text-sm font-semibold text-white">📜 AI Timeline <span className="text-[10px] text-terminal-muted">(the day's story)</span></h2>
      {events.length === 0 ? (
        <div className="text-xs text-terminal-muted">
          No events yet. The timeline fills as the market moves — trend flips,
          liquidity shifts, entry-ready, targets, exit. Quiet on a closed market.
        </div>
      ) : (
        <ol className="space-y-1 max-h-72 overflow-auto">
          {events.map((e, i) => (
            <li key={i} className="flex items-start gap-2 text-sm">
              <span className="text-terminal-muted tabular-nums text-xs mt-0.5 w-10 shrink-0">{e.time}</span>
              <span className="shrink-0">{ICON[e.kind] || "•"}</span>
              <span className="leading-snug">{e.text}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
