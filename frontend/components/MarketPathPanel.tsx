"use client";
// AI Market Path Predictor — "where is price most likely to go next?" Fuses
// existing engines: bias, next touch + ETA, 3 targets, failure level, per-horizon
// direction probability, and a natural-language summary. Derivation-only display.

import { useMarket } from "@/lib/store";

const biasTone = (b?: string) =>
  b === "BULLISH" ? "text-terminal-bull" : b === "BEARISH" ? "text-terminal-bear" : "text-terminal-warn";

export function MarketPathPanel() {
  const { decision } = useMarket();
  const mp = (decision as any)?.market_path;
  if (!mp?.ready) return null;
  const nt = mp.next_touch;

  return (
    <div className="panel border-terminal-accent/30">
      <div className="flex items-center justify-between mb-1">
        <div className="panel-title mb-0">AI Market Path — where next?</div>
        <span className={`text-sm font-bold ${biasTone(mp.bias)}`}>{mp.bias}</span>
      </div>

      {/* natural-language summary */}
      <div className="text-sm text-gray-200 mb-3">{mp.summary}</div>

      {/* overall direction — bar graph */}
      {mp.overall_direction && (
        <div className="space-y-1 mb-2">
          {[["UP", mp.overall_direction.up, "bg-terminal-bull"], ["DOWN", mp.overall_direction.down, "bg-terminal-bear"], ["RANGE", mp.overall_direction.range, "bg-terminal-warn"]].map(([lbl, v, c]: any) => (
            <div key={lbl} className="flex items-center gap-2 text-[11px]">
              <span className="w-12 text-terminal-muted">{lbl}</span>
              <div className="flex-1 h-2 rounded-full bg-terminal-bg overflow-hidden">
                <div className={`h-full ${c}`} style={{ width: `${Math.max(2, v)}%` }} />
              </div>
              <span className="w-10 text-right font-mono">{v}%</span>
            </div>
          ))}
        </div>
      )}
      <div className="flex gap-4 mb-3 text-[11px] text-terminal-muted">
        <span>Breakout <span className="font-mono text-gray-200">{mp.breakout_probability}%</span></span>
        <span>Reversal <span className="font-mono text-gray-200">{mp.reversal_probability}%</span></span>
      </div>

      {/* confidence reasoning — why this bias? */}
      {mp.reasoning?.length > 0 && (
        <div className="mb-3 border-t border-terminal-border/40 pt-2">
          <div className="stat-label mb-1">Why {mp.bias} — Layer Support {mp.layer_support ?? mp.confidence_source}/100</div>
          <div className="space-y-0.5 text-[11px]">
            {mp.reasoning.map((r: any, i: number) => (
              <div key={i} className="flex justify-between">
                <span className="text-gray-300">{r.contribution >= 0 ? "✅" : "⚠"} {r.layer}{r.reason ? ` · ${r.reason}` : ""}</span>
                <span className={`font-mono ${r.contribution >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
                  {r.contribution >= 0 ? "+" : ""}{r.contribution}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* next touch + targets */}
      <div className="grid sm:grid-cols-2 gap-3 mb-3">
        <div>
          <div className="stat-label mb-1">Next Touch</div>
          {nt ? (
            <div className="text-sm">
              <span className="font-mono">{nt.name} {nt.level}</span>
              <span className="text-terminal-muted"> · {nt.touch_prob}% · ETA {nt.eta_min}m</span>
            </div>
          ) : <div className="text-terminal-muted text-sm">—</div>}
        </div>
        <div>
          <div className="stat-label mb-1">Targets</div>
          <div className="space-y-0.5">
            {(mp.targets || []).map((t: any, i: number) => (
              <div key={i} className="text-xs flex justify-between">
                <span className="font-mono">{t.name} {t.level}</span>
                <span className="text-terminal-muted">{t.prob}%</span>
              </div>
            ))}
            {(!mp.targets || mp.targets.length === 0) && (
              <span className="text-terminal-warn text-xs">{mp.discovery || "Price discovery mode — no tracked level in range"}</span>
            )}
          </div>
        </div>
      </div>

      {/* per-horizon direction probability */}
      <div className="grid grid-cols-4 gap-2 text-center text-[11px] border-t border-terminal-border/40 pt-2">
        {(mp.horizons || []).map((h: any) => (
          <div key={h.horizon}>
            <div className="stat-label">{h.horizon}</div>
            <div className={h.lean === "UP" ? "text-terminal-bull" : h.lean === "DOWN" ? "text-terminal-bear" : "text-terminal-warn"}>
              {h.lean === "DOWN" ? `${h.down}%↓` : `${h.up}%↑`}
            </div>
          </div>
        ))}
      </div>

      {mp.failure_level && (
        <div className="text-[11px] text-terminal-bear mt-2">
          ✕ Path cancels if {mp.failure_level.level} ({mp.failure_level.name}) breaks
        </div>
      )}
      <div className="text-[10px] text-terminal-muted mt-1">🔄 {mp.live_note || mp.note}</div>
    </div>
  );
}
