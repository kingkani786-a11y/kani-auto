"use client";
// V13 unified AI Confidence meter — display only. Reads the confidence the
// engines already produced; classifies LOW / MODERATE / HIGH / VERY HIGH.

import { useMarket } from "@/lib/store";

// V13 classification: 0-25 LOW · 26-50 MODERATE · 51-75 HIGH · 76-100 VERY HIGH
function band(v: number) {
  if (v >= 76) return { label: "VERY HIGH", tone: "text-terminal-bull", bar: "bg-terminal-bull", chip: "bg-terminal-bull/15 text-terminal-bull border-terminal-bull/40" };
  if (v >= 51) return { label: "HIGH", tone: "text-terminal-accent", bar: "bg-terminal-accent", chip: "bg-terminal-accent/15 text-terminal-accent border-terminal-accent/40" };
  if (v >= 26) return { label: "MODERATE", tone: "text-terminal-warn", bar: "bg-terminal-warn", chip: "bg-terminal-warn/15 text-terminal-warn border-terminal-warn/40" };
  return { label: "LOW", tone: "text-terminal-bear", bar: "bg-terminal-bear", chip: "bg-terminal-bear/15 text-terminal-bear border-terminal-bear/40" };
}

export function ConfidenceMeter() {
  const { signal } = useMarket();
  const v = Math.round(signal?.dynamic_confidence ?? signal?.confidence ?? 0);
  const b = band(v);
  const components = signal?.confidence_components;

  return (
    <section className="panel py-3">
      <div className="panel-title">AI Confidence</div>
      <div className="flex items-end gap-3">
        <span className={`text-4xl font-black font-mono leading-none ${b.tone}`}>{v}<span className="text-lg">%</span></span>
        <span className={`ml-auto px-2.5 py-1 rounded-full border text-[11px] font-bold tracking-wide ${b.chip}`}>
          {b.label} CONFIDENCE
        </span>
      </div>
      <div className="h-2 rounded-full bg-terminal-bg overflow-hidden mt-2">
        <div className={`h-full ${b.bar} transition-all duration-500`} style={{ width: `${v}%` }} />
      </div>
      {components && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-3">
          {Object.entries(components).map(([k, val]) => (
            <div key={k} className="flex items-center justify-between text-[10px]">
              <span className="text-terminal-muted capitalize">{k.replace(/_/g, " ")}</span>
              <span className="font-mono">{val ?? "—"}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
