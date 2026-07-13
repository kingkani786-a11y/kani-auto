"use client";
// 👀 AI ATTENTION — where the radar's focus is right now, as a % across strikes
// (like an LLM attention distribution). Honest: this is WHERE it is looking
// (runner-score weighted), not a probability of profit. Deterministic.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function AIAttention() {
  const [a, setA] = useState<any>(null);
  useEffect(() => {
    const load = () => api.premiumRadar(8).then((d: any) => setA(d?.attention || null)).catch(() => {});
    load(); const id = setInterval(load, 3000); return () => clearInterval(id);
  }, []);

  const items: any[] = a?.items || [];
  if (items.length === 0) return null;

  return (
    <section className="panel space-y-1.5">
      <h2 className="text-sm font-semibold text-white">👀 AI Attention <span className="text-[10px] text-terminal-muted">(where the focus is now)</span></h2>
      {items.map((it, i) => (
        <div key={i} className="flex items-center gap-2 text-[11px]">
          <span className="w-20 shrink-0 text-white">{it.strike ? `${it.strike} ${it.type}` : "Rest"}</span>
          <div className="flex-1 h-2 bg-terminal-border rounded overflow-hidden">
            <div className={`h-full ${it.strike ? "bg-terminal-accent" : "bg-terminal-border"}`} style={{ width: `${it.pct}%` }} />
          </div>
          <span className="tabular-nums text-terminal-muted w-10 text-right">{it.pct}%</span>
        </div>
      ))}
      <div className="text-[10px] text-terminal-muted">{a?.note}</div>
    </section>
  );
}
