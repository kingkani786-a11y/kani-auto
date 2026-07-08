"use client";
// V13 — AI Index Selector (momentum radar). Ranks the 5 supported indices
// from ONE existing batch-quote call per minute. Honestly labelled: momentum
// ranking only — full institutional ranking needs per-index chains.

import { useMarket } from "@/lib/store";

export function IndexRadar() {
  const { decision } = useMarket();
  const r: any = (decision as any)?.index_radar;
  if (!r?.ready || !r.ranking?.length) return null;

  return (
    <div className="panel py-2.5">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-1.5">
        <span className="font-bold tracking-wider text-terminal-accent text-[12px]">📡 AI INDEX SELECTOR</span>
        <span className="text-[12px]">
          Best: <span className="font-mono font-bold text-terminal-bull">{r.best}</span>
          <span className="text-terminal-muted"> — {r.best_reason}</span>
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-[11px]">
        {r.ranking.map((x: any, i: number) => (
          <div key={x.symbol}
               className={`rounded-md border px-2 py-1 ${x.symbol === r.current ? "border-terminal-accent/60" : "border-terminal-border/60"}`}>
            <div className="flex items-center justify-between">
              <span className={`font-semibold ${i === 0 ? "text-terminal-bull" : ""}`}>{i + 1}. {x.symbol}</span>
              <span className="font-mono">{x.score}</span>
            </div>
            <div className="flex items-center justify-between text-[10px]">
              <span className={x.change_pct > 0 ? "text-terminal-bull" : x.change_pct < 0 ? "text-terminal-bear" : "text-terminal-muted"}>
                {x.change_pct > 0 ? "+" : ""}{x.change_pct}%
              </span>
              <span className={x.bias === "BULL" ? "text-terminal-bull" : x.bias === "BEAR" ? "text-terminal-bear" : "text-terminal-muted"}>
                {x.bias === "BULL" ? "CE lean" : x.bias === "BEAR" ? "PE lean" : "flat"}
              </span>
              <span className="text-terminal-muted">rng {x.range_pos}%</span>
            </div>
            {x.symbol === r.current && <div className="text-[9px] text-terminal-accent">trading now</div>}
          </div>
        ))}
      </div>
      <div className="text-[10px] text-terminal-muted mt-1.5">{r.note}</div>
    </div>
  );
}
