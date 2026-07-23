"use client";
// S/R HERO CARD (owner, 2026-07-23, item #5 Phase 2 — "Entry Decision
// Platform" priority list, Priority 11). The single nearest actionable
// support/resistance level + distance + strength + evidence + readiness
// stage.
//
// This is NOT a second Trade Light. TradeNowCard above states the ONE
// BUY/WAIT/EXIT verdict (owner 2026-07-21: "ஒரே BUY/WAIT verdict ஒரு
// இடத்தில் மட்டும்") — this card is about proximity to STRUCTURE, a
// different axis. Its "stage" (WAIT/WATCHING/VOLUME_CONFIRM/CANDLE_CONFIRM/
// BUY_READY) is a readiness signal into the Decision Engine, never a trade
// decision of its own — the backend's own workflow note says so explicitly.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const STAGE_STYLE: Record<string, { badge: string; border: string; label: string }> = {
  WAIT: { badge: "text-terminal-muted border-terminal-border", border: "border-terminal-border", label: "WAIT" },
  WATCHING: { badge: "text-terminal-warn border-terminal-warn/40", border: "border-terminal-warn/40", label: "WATCHING" },
  VOLUME_CONFIRM: { badge: "text-sky-400 border-sky-500/40", border: "border-sky-500/40", label: "VOLUME CONFIRM" },
  CANDLE_CONFIRM: { badge: "text-terminal-accent border-terminal-accent/40", border: "border-terminal-accent/40", label: "CANDLE CONFIRM" },
  BUY_READY: { badge: "text-terminal-bull border-terminal-bull/50", border: "border-terminal-bull/50", label: "BUY READY" },
};

const EVIDENCE_LABEL: Record<string, string> = {
  vwap: "VWAP", swing: "Swing", volume_node: "Volume Node", cpr: "CPR", oi_wall: "OI Wall",
};

export function SRHeroCard() {
  const [r, setR] = useState<any>(null);
  useEffect(() => {
    const load = () => api.supportResistance().then(setR).catch(() => {});
    load();
    const id = setInterval(load, 5000);   // faster than the full panel — cheap payload
    return () => clearInterval(id);
  }, []);

  const hero = r?.hero;
  if (!r?.ready || !hero) return null;

  const stage = hero.workflow?.stage || "WAIT";
  const st = STAGE_STYLE[stage] || STAGE_STYLE.WAIT;
  const ev = hero.evidence || {};

  return (
    <section className={`panel border-2 ${st.border} space-y-2`}>
      <div className="flex items-center justify-between">
        <div className="text-[10px] font-semibold text-terminal-muted uppercase tracking-wide">
          NEXT {hero.side}
        </div>
        <span className={`text-[11px] font-bold px-2 py-0.5 rounded border ${st.badge}`}>{st.label}</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
        <div>
          <div className="text-lg font-bold tabular-nums text-white">{hero.level}</div>
          <div className="text-[9px] text-terminal-muted">{hero.label}</div>
        </div>
        <div>
          <div className="text-lg font-bold tabular-nums text-white">{hero.distance}</div>
          <div className="text-[9px] text-terminal-muted">Distance (pts)</div>
        </div>
        <div>
          <div className="text-lg font-bold tabular-nums text-white">{hero.strength_stars}★</div>
          <div className="text-[9px] text-terminal-muted">Strength ({hero.strength_score})</div>
        </div>
        <div>
          <div className="text-lg font-bold tabular-nums text-white">
            {ev.count ?? "—"}/{ev.total ?? "—"}
          </div>
          <div className="text-[9px] text-terminal-muted">Evidence</div>
        </div>
      </div>

      {/* Why here — evidence checklist, not a "confidence %" (owner: probability
          only in Forecast AI; elsewhere observed/evidence). YES/NO per source,
          each read from its own owning engine, never re-derived here. */}
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] border-t border-terminal-border pt-1.5">
        {Object.entries(EVIDENCE_LABEL).map(([k, label]) => (
          <span key={k} className="flex items-center gap-1">
            <span className={ev[k] ? "text-terminal-bull" : "text-terminal-muted"}>{ev[k] ? "✓" : "○"}</span>
            <span className="text-terminal-muted">{label}</span>
          </span>
        ))}
      </div>

      <div className="text-[10px] text-terminal-muted">
        {hero.workflow?.note || "Structure readiness only — the Decision Engine still decides BUY/WAIT/EXIT."}
      </div>
    </section>
  );
}
