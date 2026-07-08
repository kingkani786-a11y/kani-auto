"use client";
// PHASE 27 + 26 + Confidence Explainer. Entry-timing zone, premium forecast,
// and per-engine confidence breakdown — all derivation-only from the decision.

import { useMarket } from "@/lib/store";

const zoneTone = (z?: string) =>
  z === "BEST ENTRY" ? "text-terminal-bull" : z === "GOOD ENTRY" ? "text-terminal-bull"
  : z === "LATE ENTRY" ? "text-terminal-warn" : "text-terminal-bear";
const classTone = (c?: string) =>
  c === "EXPLOSIVE" || c === "STRONG" ? "text-terminal-bull" : c === "MODERATE" ? "text-terminal-warn" : "text-terminal-bear";

export function EntryZonePremium() {
  const { decision } = useMarket();
  const d: any = decision || {};
  const ez = d.entry_zone, pf = d.premium_forecast, cb = d.confidence_breakdown;
  if (!ez?.ready && !pf?.ready && !cb?.ready) return null;

  return (
    <div className="grid lg:grid-cols-3 gap-4">
      {/* Entry Zone */}
      {ez?.ready && (
        <div className="panel">
          <div className="panel-title">Entry Zone</div>
          <div className={`text-xl font-bold ${zoneTone(ez.zone)}`}>{ez.zone}</div>
          <div className="text-xs text-terminal-muted mt-0.5">Score {ez.score}/100</div>
          <div className="text-xs text-gray-300 mt-1.5">{ez.reason}</div>
        </div>
      )}

      {/* Premium Forecast */}
      {pf?.ready && (
        <div className="panel">
          <div className="panel-title">Premium Forecast</div>
          <div className="flex items-baseline gap-2">
            <span className={`text-lg font-bold ${classTone(pf.classification)}`}>{pf.classification}</span>
            <span className="text-xs text-terminal-muted">now ₹{pf.current_premium} · {pf.probability}% prob</span>
          </div>
          <div className="grid grid-cols-4 gap-1.5 mt-2 text-center">
            {Object.entries(pf.forecasts).map(([h, v]: [string, any]) => (
              <div key={h}>
                <div className="stat-label">{h}</div>
                <div className="text-xs font-mono">₹{v.premium}</div>
                <div className={`text-[10px] ${v.change_pct >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
                  {v.change_pct >= 0 ? "+" : ""}{v.change_pct}%
                </div>
              </div>
            ))}
          </div>
          <div className="text-[10px] text-terminal-muted mt-1.5">
            Exp +{pf.expected_expansion_pct}% vs decay −{pf.expected_decay_pct}% (θ {pf.theta_risk} · IV-crush {pf.iv_crush_risk})
          </div>
        </div>
      )}

      {/* Confidence Explainer */}
      {cb?.ready && (
        <div className="panel">
          <div className="panel-title">Why Confidence {cb.confidence}%</div>
          <div className="space-y-1">
            {cb.components.map((c: any) => (
              <div key={c.engine} className="flex items-center gap-2 text-xs">
                <span className="w-24 capitalize text-terminal-muted">{c.engine.replace("_", " ")}</span>
                <div className="flex-1 h-1.5 bg-terminal-bg rounded-full overflow-hidden flex justify-center">
                  <div className={`h-full ${c.contribution >= 0 ? "bg-terminal-bull" : "bg-terminal-bear"}`}
                       style={{ width: `${Math.min(100, Math.abs(c.contribution) * 12)}%` }} />
                </div>
                <span className={`w-10 text-right font-mono ${c.contribution >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
                  {c.contribution >= 0 ? "+" : ""}{c.contribution}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
