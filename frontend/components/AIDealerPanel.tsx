"use client";
// AI DEALER — Step 9 (Explainability Final, 2026-07-27). A PURE NARRATOR:
// reads ONLY the Hero's own contract + the canonical Evidence/Structure/
// S-R/Risk engines (Steps 3/5/6/7) and translates already-verified
// dashboard state into plain checklists. It NEVER computes a new score,
// NEVER gates/vetoes anything, and NEVER gives a second opinion — the
// verdict shown here is a pure restatement of the Hero's (TradeNowCard's)
// own decision, never a competing one (Rule 11).
//
// WHY BUY / WHY NOT BUY / NEXT LEVEL / INVALIDATION — exactly these 4
// sections, nothing more. Every field is sourced from `c.ai_dealer`
// (decision_contract.py), which itself only reuses values the S/R,
// Structure, Evidence and Risk engines already computed.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const MARK: Record<string, string> = { true: "✓", false: "○" };

export function AIDealerPanel() {
  const [c, setC] = useState<any>(null);
  useEffect(() => {
    const load = () => api.decisionContract().then(setC).catch(() => {});
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  const d = c?.ai_dealer;
  if (!d) return null;

  const nl = d.next_level || {};
  const hasNextLevel = nl.next_resistance != null || nl.next_premium_target != null || nl.gamma_wall != null;

  return (
    <section className="panel border border-terminal-border/60">
      <div className="panel-title flex items-center justify-between">
        <span>🤝 Cloud AI Dealer <span className="text-[10px] text-terminal-muted font-normal">(narrator — never a decision)</span></span>
        <span className={`text-xs font-bold px-2 py-0.5 rounded border ${d.is_buy ? "text-terminal-bull border-terminal-bull/50" : "text-terminal-muted border-terminal-border"}`}>
          {d.verdict}
        </span>
      </div>

      <div className="grid sm:grid-cols-2 gap-3 mt-2">
        <div>
          <div className="text-[10px] text-terminal-muted uppercase tracking-wide mb-1">Why Buy</div>
          <div className="space-y-0.5">
            {(d.why_buy || []).map((w: any) => (
              <div key={w.label} className="flex items-center gap-1.5 text-[11px]">
                <span className={w.ok ? "text-terminal-bull" : "text-terminal-muted"}>{MARK[String(w.ok)]}</span>
                <span className={w.ok ? "text-gray-200" : "text-terminal-muted"}>{w.label}</span>
              </div>
            ))}
          </div>
        </div>

        {d.why_not_buy?.length > 0 && (
          <div>
            <div className="text-[10px] text-terminal-muted uppercase tracking-wide mb-1">Why Not Buy</div>
            <div className="space-y-0.5">
              {d.why_not_buy.map((w: any) => (
                <div key={w.label} className="flex items-center gap-1.5 text-[11px]">
                  <span className="text-terminal-bear">✕</span>
                  <span className="text-gray-200">{w.label}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {hasNextLevel && (
        <div className="text-[11px] border-t border-terminal-border/40 mt-2 pt-1.5">
          <div className="text-terminal-muted uppercase tracking-wide text-[10px] mb-0.5">Next Level</div>
          <div className="flex flex-wrap gap-x-4 gap-y-0.5">
            {nl.next_resistance != null && <span>Next Resistance <span className="font-mono text-white">{nl.next_resistance}</span></span>}
            {nl.next_premium_target != null && <span>Next Premium Target <span className="font-mono text-white">₹{nl.next_premium_target}</span></span>}
            {nl.gamma_wall != null && <span>Gamma Wall <span className="font-mono text-white">{nl.gamma_wall}</span></span>}
          </div>
        </div>
      )}

      {d.invalidation?.length > 0 && (
        <div className="text-[11px] border-t border-terminal-border/40 mt-2 pt-1.5">
          <div className="text-terminal-muted uppercase tracking-wide text-[10px] mb-0.5">Trade Becomes Invalid If</div>
          {d.invalidation.map((inv: string, i: number) => (
            <div key={i} className="text-terminal-muted">• {inv}</div>
          ))}
        </div>
      )}

      <div className="text-[10px] text-terminal-muted mt-2">
        {d.note}
      </div>
    </section>
  );
}
