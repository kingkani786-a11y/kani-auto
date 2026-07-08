"use client";
// Phase A — Premium Roadmap timeline. How the recommended option's premium is
// projected to evolve (15/30/60/90 min). Reads premium_forecast; derivation-only.

import { useMarket } from "@/lib/store";

export function PremiumTimeline() {
  const { decision } = useMarket();
  const pf = (decision as any)?.premium_forecast;
  if (!pf?.ready || !pf.forecasts) return null;

  const now = pf.current_premium;
  const steps = [
    { t: "Now", v: now, c: 0 },
    ...Object.entries(pf.forecasts).map(([h, f]: [string, any]) => ({ t: h, v: f.premium, c: f.change_pct })),
  ];

  return (
    <div className="panel">
      <div className="flex items-center justify-between mb-2">
        <div className="panel-title mb-0">Premium Roadmap — {pf.strike} {pf.type}</div>
        <span className={`text-xs font-bold ${pf.classification === "EXPLOSIVE" || pf.classification === "STRONG" ? "text-terminal-bull" : pf.classification === "MODERATE" ? "text-terminal-warn" : "text-terminal-bear"}`}>
          {pf.classification} · {pf.probability}%
        </span>
      </div>
      <div className="flex items-center justify-between">
        {steps.map((s, i) => (
          <div key={s.t} className="flex items-center">
            <div className="text-center">
              <div className="text-[10px] text-terminal-muted">{s.t}</div>
              <div className="font-mono text-sm">₹{s.v}</div>
              {s.c !== 0 && (
                <div className={`text-[10px] ${s.c >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
                  {s.c >= 0 ? "+" : ""}{s.c}%
                </div>
              )}
            </div>
            {i < steps.length - 1 && <span className="text-terminal-border mx-1">→</span>}
          </div>
        ))}
      </div>
      <div className="text-[10px] text-terminal-muted mt-1.5">
        Exp +{pf.expected_expansion_pct}% vs decay −{pf.expected_decay_pct}% (θ {pf.theta_risk} · IV-crush {pf.iv_crush_risk})
      </div>
    </div>
  );
}
