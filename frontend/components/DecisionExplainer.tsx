"use client";
// V13.1 Decision Explainer — transparency table of per-engine contributions
// to the final confidence (display only; mirrors the engines' own scores).

import { useMarket } from "@/lib/store";

export function DecisionExplainer() {
  const { layers } = useMarket();
  const ex = (layers as any)?.decision_explainer;
  if (!ex?.rows) return (
    <section className="panel">
      <div className="panel-title">Decision Explainer</div>
      <p className="text-sm text-terminal-muted">Contribution breakdown appears with the first signal.</p>
    </section>
  );

  return (
    <section className="panel">
      <div className="panel-title">Decision Explainer</div>
      <div className="space-y-1.5">
        {ex.rows.map((r: any) => (
          <div key={r.engine} className="flex items-center gap-2 text-xs">
            <span className="w-36 text-terminal-muted">{r.engine}</span>
            <span className={`w-16 ${r.bias === "Bullish" ? "text-terminal-bull" : r.bias === "Bearish" ? "text-terminal-bear" : "text-terminal-muted"}`}>
              {r.bias}
            </span>
            <div className="flex-1 h-1.5 rounded bg-terminal-bg overflow-hidden flex justify-center">
              <div className={`h-full ${r.contribution >= 0 ? "bg-terminal-bull" : "bg-terminal-bear"}`}
                style={{ width: `${Math.min(Math.abs(r.contribution), 50)}%` }} />
            </div>
            <span className={`w-10 text-right font-mono ${r.contribution >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
              {r.display}
            </span>
          </div>
        ))}
        <div className="flex items-center gap-2 text-sm font-bold pt-2 mt-1 border-t border-terminal-border">
          <span className="w-36">FINAL CONFIDENCE</span>
          <span className="ml-auto font-mono text-terminal-accent">{ex.final_confidence}%</span>
        </div>
      </div>
    </section>
  );
}
