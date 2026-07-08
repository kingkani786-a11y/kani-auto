"use client";
// V32 Layer-6 — AI MARKET MEMORY (Research mode). Which historical day does
// today most resemble, and what happened next in those analogue days.
// HISTORICAL context, clearly labelled — never a prediction. Appears only
// after the historical-learning run has populated day features.

import { useMarket } from "@/lib/store";

export function MarketMemory() {
  const { decision } = useMarket();
  const m: any = (decision as any)?.market_memory;
  if (!m) return null;

  return (
    <div className="panel py-2.5">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-1.5">
        <span className="font-bold tracking-wider text-terminal-accent text-[12px]">🧬 AI MARKET MEMORY</span>
        <span className="text-[12px]">
          Today resembles <span className="font-mono font-bold text-gray-100">{m.most_similar_date}</span>
          <span className="text-terminal-muted"> ({m.setup_that_day?.replace(/_/g, " ").toLowerCase()})</span>
          <span className="font-mono"> · {m.similarity_pct}% similar</span>
        </span>
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-1 text-[12px]">
        <span className="text-terminal-muted">In {m.sample} closest analogue days:</span>
        <span>next day up <span className={`font-mono ${m.next_day_up_pct >= 50 ? "text-terminal-bull" : "text-terminal-bear"}`}>{m.next_day_up_pct}%</span></span>
        <span>avg next-day move <span className="font-mono">{m.avg_next_day_ret_pct > 0 ? "+" : ""}{m.avg_next_day_ret_pct}%</span></span>
      </div>
      <div className="text-[11px] text-terminal-muted mt-1">
        {(m.matches || []).map((x: any, i: number) => (
          <span key={i} className="font-mono mr-3">{x.date} ({x.next_ret_pct > 0 ? "+" : ""}{x.next_ret_pct}%)</span>
        ))}
      </div>
      <div className="text-[10px] text-terminal-muted/70 italic mt-1">{m.note}</div>
    </div>
  );
}
