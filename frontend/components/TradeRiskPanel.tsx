"use client";
// TRADE RISK PANEL — Step 7 (Risk Panel Final, 2026-07-26). The ONE place
// pre-entry risk lives: Stop Loss, Risk, Risk:Reward, Position Size, Max
// Loss, Next Invalidation — nothing else. Never a decision, never BUY/SELL —
// the decision stays with TradeNowCard alone (Rule 11).
//
// NOT the same component as SignalPanels.tsx's `RiskPanel` (that one shows
// qualitative market risk — risk_level/ADX/ATR%/warnings, an unrelated
// scope) — named TradeRiskPanel to avoid the collision.
//
// Every field here reuses a value already computed elsewhere — zero new
// scoring:
//   Stop Loss <- decisionContract().exit_plan/premium_plan (both units,
//     shown side by side so index-points vs option-premium ₹ can never be
//     mistaken for the same number)
//   Risk / Max Loss / R:R / Position Size <- riskApproval()'s position_size
//     (Step 7 fixed this to be the single premium-based source shared with
//     ScalpingTool.tsx — no more disagreeing lot counts across panels)
//   Next Invalidation <- decisionContract().invalidations (the pre-entry/
//     armed-trade conditions — distinct from AI Thinking's radar-momentum
//     "invalidation", which answers a different question)

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { displayReasons } from "@/lib/labels";

export function TradeRiskPanel() {
  const [rc, setRc] = useState<any>(null);
  const [ra, setRa] = useState<any>(null);

  useEffect(() => {
    const load = () => {
      api.decisionContract().then(setRc).catch(() => {});
      api.riskApproval().then(setRa).catch(() => {});
    };
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  const ps = ra?.position_size || {};
  const slIndex = rc?.exit_plan?.stop_loss;
  const slPremium = rc?.premium_plan?.stop_loss;
  // Owner Step 9 (Explainability Final, 2026-07-27) fix: this used to
  // render raw backend strings, which could still say "Kill Switch"
  // instead of the dashboard's display-only "Execution Lock" rename —
  // now passed through the same displayReasons() helper every other
  // blocking-reason surface already uses.
  const invalidations: string[] = displayReasons(rc?.invalidations || []);

  // Owner Step 10 (MTF Confluence, 2026-07-27) — display-only flag from the
  // new mtf_confluence engine (decision_contract.py's `mtf` field). Per
  // owner sign-off this is informational only for now; it does NOT reduce
  // position size — any sizing change is a separate Trading Doctrine
  // proposal once there's real evidence on how predictive this flag is.
  const mtfReady = !!rc?.mtf?.ready;
  const htfConflict = !!rc?.mtf?.higher_tf_conflict;

  if (slIndex == null && slPremium == null && !ps.risk_amount && invalidations.length === 0 && !mtfReady) return null;

  return (
    <section className="panel border border-terminal-border/60">
      <div className="panel-title">Risk <span className="text-[10px] text-terminal-muted font-normal">(pre-entry — not a decision)</span></div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-1 text-center">
        <div>
          <div className="text-sm font-semibold tabular-nums text-terminal-bear">{slIndex ?? "—"}</div>
          <div className="text-[9px] text-terminal-muted">Stop Loss (index pts)</div>
        </div>
        <div>
          <div className="text-sm font-semibold tabular-nums text-terminal-bear">{slPremium != null ? `₹${slPremium}` : "—"}</div>
          <div className="text-[9px] text-terminal-muted">Stop Loss (premium)</div>
        </div>
        <div>
          <div className="text-sm font-semibold tabular-nums text-white">{ps.rr ? `1:${ps.rr}` : "—"}</div>
          <div className="text-[9px] text-terminal-muted">R:R (to Target 2)</div>
        </div>
        <div>
          <div className="text-sm font-semibold tabular-nums text-white">{ps.recommended_lots ?? "—"}{ps.max_lots ? ` / ${ps.max_lots}` : ""}</div>
          <div className="text-[9px] text-terminal-muted">Rec / Max Lots</div>
        </div>
        <div>
          <div className="text-sm font-semibold tabular-nums text-terminal-bear">{ps.risk_amount ? `₹${ps.risk_amount.toLocaleString("en-IN")}` : "—"}</div>
          <div className="text-[9px] text-terminal-muted">Risk (to SL)</div>
        </div>
        <div>
          <div className="text-sm font-semibold tabular-nums text-terminal-bear">{ps.max_loss ? `₹${ps.max_loss.toLocaleString("en-IN")}` : "—"}</div>
          <div className="text-[9px] text-terminal-muted">Max Loss (premium)</div>
        </div>
      </div>

      {invalidations.length > 0 && (
        <div className="text-[10px] border-t border-terminal-border/40 mt-2 pt-1.5">
          <div className="text-terminal-muted font-semibold mb-0.5 uppercase">Next Invalidation</div>
          {invalidations.map((inv, i) => (
            <div key={i} className="text-terminal-muted">• {inv}</div>
          ))}
        </div>
      )}

      {mtfReady && (
        <div className="text-[10px] border-t border-terminal-border/40 mt-2 pt-1.5 flex items-center justify-between">
          <span className="text-terminal-muted font-semibold uppercase">Higher Timeframe Conflict</span>
          <span className={`font-bold ${htfConflict ? "text-terminal-bear" : "text-terminal-bull"}`}>
            {htfConflict ? "YES" : "NO"}
          </span>
        </div>
      )}

      <div className="text-[10px] text-terminal-muted mt-2">
        Risk facts only — never a BUY/SELL call. The decision stays with the Hero card above.
      </div>
    </section>
  );
}
