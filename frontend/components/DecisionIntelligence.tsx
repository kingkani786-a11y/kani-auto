"use client";
// PHASE 1/5/13 — Decision Intelligence panel. One synthesised institutional
// decision + Trade Quality (0–1000) + governance/devil's-advocate. Reads the
// existing decision slice; derivation-only display.

import { useMarket } from "@/lib/store";

const gradeTone = (g?: string) =>
  g === "ELITE" || g === "HIGH PROBABILITY" ? "text-terminal-bull"
  : g === "MEDIUM" ? "text-terminal-warn" : "text-terminal-bear";
const decTone = (d?: string) =>
  d?.startsWith("BUY") ? "text-terminal-bull" : d === "NO TRADE" ? "text-terminal-bear" : "text-terminal-warn";

export function DecisionIntelligence() {
  const { decision } = useMarket();
  const di = (decision as any)?.intelligence_synthesis;
  if (!di?.ready) return null;

  const tq = di.trade_quality || {};
  const g = di.governance || {};

  return (
    <div className="panel border-terminal-accent/30">
      <div className="panel-title">Decision Intelligence — institutional synthesis</div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-3">
        <div>
          <div className="stat-label">Final Decision</div>
          <div className={`stat-value text-lg ${decTone(di.final_decision)}`}>{di.final_decision}</div>
        </div>
        <div>
          <div className="stat-label">AI Conviction</div>
          <div className="stat-value text-lg">{di.conviction}%</div>
        </div>
        <div>
          <div className="stat-label">Trade Quality</div>
          <div className={`stat-value text-lg ${gradeTone(tq.grade)}`}>{tq.score}<span className="text-xs text-terminal-muted">/1000</span></div>
        </div>
        <div>
          <div className="stat-label">Grade</div>
          <div className={`stat-value text-lg ${gradeTone(tq.grade)}`}>{tq.grade}</div>
        </div>
      </div>

      {/* component score bars */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 mb-3">
        {Object.entries(di.components || {}).map(([k, v]: [string, any]) => (
          <div key={k} className="flex items-center justify-between text-[11px]">
            <span className="text-terminal-muted capitalize">{k.replace("_score", "").replace("_", " ")}</span>
            <span className={`font-mono ${v >= 65 ? "text-terminal-bull" : v >= 50 ? "text-terminal-warn" : "text-terminal-bear"}`}>{v}</span>
          </div>
        ))}
      </div>

      {/* governance / devil's advocate */}
      <div className="border-t border-terminal-border/40 pt-2 space-y-1 text-xs">
        <div><span className="text-terminal-bull">▲ For:</span> <span className="text-gray-300">{g.strongest_bull}</span></div>
        <div><span className="text-terminal-bear">▼ Against:</span> <span className="text-gray-300">{g.strongest_bear}</span></div>
        <div><span className="text-terminal-warn">⚠ Largest risk:</span> <span className="text-gray-300">{g.largest_risk}</span></div>
        <div><span className="text-terminal-muted">🗣 Devil's advocate:</span> <span className="text-gray-300">{g.devils_advocate}</span></div>
        <div className="pt-1 font-semibold">{g.final_verdict}</div>
      </div>
      <div className="text-[10px] text-terminal-muted mt-2">
        Engine agreement {tq.engine_agreement_pct}% · {di.disclaimer}
      </div>
    </div>
  );
}
