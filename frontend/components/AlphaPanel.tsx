"use client";
// V29 — Alpha Detection. Alpha score + entry-timing gauge + opportunity queue +
// per-domain confidence distribution. Derivation-only display.

import { useMarket } from "@/lib/store";

const catTone = (c?: string) =>
  c === "Institutional Alpha" || c === "Strong Edge" ? "text-terminal-bull"
  : c === "Moderate Edge" ? "text-terminal-warn" : "text-terminal-muted";
const timingTone = (t?: string) =>
  t === "Ideal" ? "text-terminal-bull" : t === "Late" ? "text-terminal-warn" : t === "Avoid" ? "text-terminal-bear" : "text-terminal-muted";
const GAUGE = ["Too Early", "Ideal", "Late", "Avoid"];

export function AlphaPanel() {
  const { decision } = useMarket();
  const a = (decision as any)?.alpha;
  if (!a?.ready) return null;
  const cd = a.confidence_distribution || {};

  return (
    <div className="panel border-terminal-accent/30">
      <div className="flex items-center justify-between mb-2">
        <div className="panel-title mb-0">Alpha Detection</div>
        <span className={`text-sm font-bold ${catTone(a.category)}`}>{a.alpha_score}/100 · {a.category}</span>
      </div>

      {/* entry timing gauge */}
      <div className="flex gap-1 mb-3">
        {GAUGE.map((g) => (
          <div key={g} className={`flex-1 text-center text-[10px] py-1 rounded ${
            a.entry_timing === g ? `bg-terminal-bg border border-terminal-accent/40 font-bold ${timingTone(g)}` : "text-terminal-muted"}`}>
            {g}
          </div>
        ))}
      </div>

      {/* confidence distribution — heat bars */}
      <div className="space-y-1 mb-3">
        {Object.entries(cd).map(([k, v]: [string, any]) => (
          <div key={k} className="flex items-center gap-2 text-[11px]">
            <span className="w-20 capitalize text-terminal-muted">{k}</span>
            <div className="flex-1 h-2 rounded-full bg-terminal-bg overflow-hidden">
              <div className={`h-full ${v >= 65 ? "bg-terminal-bull" : v >= 50 ? "bg-terminal-warn" : "bg-terminal-bear"}`}
                   style={{ width: `${Math.max(2, Math.min(100, v))}%` }} />
            </div>
            <span className={`w-10 text-right font-mono ${v >= 65 ? "text-terminal-bull" : v >= 50 ? "text-terminal-warn" : "text-terminal-bear"}`}>{v}%</span>
          </div>
        ))}
      </div>

      {/* opportunity queue */}
      <table className="w-full text-xs font-mono">
        <thead><tr className="stat-label text-left">
          {["#", "Type", "Points", "Prob", "Status"].map((h) => <th key={h} className="pb-1 pr-2 font-normal">{h}</th>)}
        </tr></thead>
        <tbody>
          {(a.opportunity_queue || []).map((q: any) => (
            <tr key={q.rank} className="border-t border-terminal-border/30">
              <td className="py-1 pr-2">{q.probability >= 80 ? "🟢" : q.probability >= 65 ? "🟡" : q.probability >= 50 ? "🟠" : "🔴"}</td>
              <td className="pr-2">{q.type}</td>
              <td className="pr-2">{q.points?.[0]}–{q.points?.[1]}</td>
              <td className="pr-2">{q.probability}%</td>
              <td className={`pr-2 ${q.status === "Ready" ? "text-terminal-bull" : q.status === "Preparing" ? "text-terminal-warn" : "text-terminal-muted"}`}>{q.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="text-[10px] text-terminal-muted mt-2">{a.note}</div>
    </div>
  );
}
