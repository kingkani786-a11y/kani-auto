"use client";
// PHASE 27 + Confidence Explainer. Entry-timing zone and per-engine
// confidence breakdown — derivation-only from the decision.
//
// Owner Step 4 (Premium Panel Final, 2026-07-26): the Premium Forecast box
// that used to sit here was a duplicate of PremiumTimeline.tsx's "Premium
// Roadmap" panel — both rendered the identical decision.premium_forecast
// object. Removed here; PremiumTimeline.tsx is the one canonical Premium
// panel (it also carries strike identity + a "Now" anchor point).

import { useMarket } from "@/lib/store";

const zoneTone = (z?: string) =>
  z === "BEST ENTRY" ? "text-terminal-bull" : z === "GOOD ENTRY" ? "text-terminal-bull"
  : z === "LATE ENTRY" ? "text-terminal-warn" : "text-terminal-bear";

export function EntryZonePremium() {
  const { decision } = useMarket();
  const d: any = decision || {};
  const ez = d.entry_zone, cb = d.confidence_breakdown;
  if (!ez?.ready && !cb?.ready) return null;

  return (
    <div className="grid lg:grid-cols-2 gap-4">
      {/* Entry Zone */}
      {ez?.ready && (
        <div className="panel">
          <div className="panel-title">Entry Zone</div>
          <div className={`text-xl font-bold ${zoneTone(ez.zone)}`}>{ez.zone}</div>
          <div className="text-xs text-terminal-muted mt-0.5">Score {ez.score}/100</div>
          <div className="text-xs text-gray-300 mt-1.5">{ez.reason}</div>
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
