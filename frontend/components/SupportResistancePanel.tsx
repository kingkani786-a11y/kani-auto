"use client";
// DYNAMIC SUPPORT/RESISTANCE — Phase 2 KICKOFF (owner, 2026-07-23, item #5).
// Partial by design: spot levels only (swing-fractal clustering + real
// touch/bounce/break stats from candle history, support_resistance.py).
// Premium S/R is deferred — no persisted full-session premium series exists
// yet to compute honest touch stats on (see the engine's own docstring).

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const stars = (n: number) => "★".repeat(n) + "☆".repeat(5 - n);

function Level({ l }: { l: any }) {
  return (
    <div className="flex items-center justify-between text-[11px] border-b border-terminal-border/20 py-1">
      <span className="text-terminal-muted w-8">{l.label}</span>
      <span className="tabular-nums text-white font-semibold">{l.level}</span>
      <span className="text-terminal-muted">{l.touches}× touched</span>
      <span className="text-terminal-bull">{l.bounce_pct != null ? `${l.bounce_pct}% bounce` : "—"}</span>
      <span className="text-terminal-warn">{stars(l.strength_stars)}</span>
    </div>
  );
}

export function SupportResistancePanel() {
  const [r, setR] = useState<any>(null);
  useEffect(() => {
    const load = () => api.supportResistance?.().then(setR).catch(() => {});
    load();
    const id = setInterval(load, 20000);
    return () => clearInterval(id);
  }, []);
  if (!r) return null;

  return (
    <div className="panel border border-terminal-border/60">
      <div className="flex items-baseline justify-between mb-2">
        <div className="panel-title mb-0">Dynamic Support / Resistance <span className="text-[10px] text-terminal-muted font-normal">(Phase 2 kickoff — spot only)</span></div>
        {r.cmp != null && <span className="text-xs text-terminal-muted">CMP {r.cmp}</span>}
      </div>
      {!r.ready ? (
        <div className="text-[11px] text-terminal-muted">{r.reason || "building — needs more candle history"}</div>
      ) : (
        <div className="space-y-2">
          <div>
            <div className="text-[10px] text-terminal-bear font-semibold mb-0.5">RESISTANCE</div>
            {r.resistance.length ? r.resistance.map((l: any) => <Level key={l.label} l={l} />)
              : <div className="text-[11px] text-terminal-muted">none detected above CMP</div>}
          </div>
          <div>
            <div className="text-[10px] text-terminal-bull font-semibold mb-0.5">SUPPORT</div>
            {r.support.length ? r.support.map((l: any) => <Level key={l.label} l={l} />)
              : <div className="text-[11px] text-terminal-muted">none detected below CMP</div>}
          </div>
        </div>
      )}
      {!r.premium_available && (
        <div className="text-[10px] text-terminal-muted mt-2 pt-1.5 border-t border-terminal-border/40">
          Premium S/R: deferred — needs a persisted full-session premium series (Phase 2 dependency), not yet built.
        </div>
      )}
    </div>
  );
}
