"use client";
// SIGNAL <-> EXECUTION — V7.1 item #1 (owner, 2026-08-04).
//
// THE PROBLEM: when any veto fires, confluence.py sets signal="NO TRADE" and
// direction="NONE". A trader reads that as "the system found nothing" — but
// the truth is usually "the system found a direction and execution refused
// it". The 2026-08-04 session made the cost obvious: the radar flagged
// Runner-90 BUY CANDIDATEs all day while the Hero card read a bare NO TRADE.
// Owner's framing: "an execution block must not erase the underlying
// directional opportunity."
//
// This card shows the three facts as three separate lines:
//     SIGNAL     — what the engine computed (direction + confidence)
//     EXECUTION  — BLOCKED
//     REASON     — the vetoes that actually govern
//
// HARD BOUNDARIES, deliberately:
//   * It reads `decision.signal.signal_candidate`, which is additive metadata.
//     No threshold, gate, veto or score was changed to produce it.
//   * It is NOT a recommendation and NOT tradable. The vetoes are what govern;
//     this only stops a blocked signal from vanishing without trace.
//   * Rule 11 intact: TradeNowCard remains the ONLY decision surface. This
//     card never says BUY/SELL as an instruction — it reports what was
//     computed and that it was refused.

import { useMarket } from "@/lib/store";

export function SignalExecutionCard() {
  const { decision } = useMarket();
  const cand = (decision as any)?.signal?.signal_candidate;

  // Quiet unless the engine actually had a direction that execution refused.
  if (!cand || !["BULL", "BEAR"].includes(cand.direction)) return null;

  const bull = cand.direction === "BULL";
  const tone = bull ? "text-terminal-bull" : "text-terminal-bear";
  const reasons: string[] = cand.blocked_by || [];

  return (
    <div className="panel border border-terminal-warn/50 py-2.5 space-y-2 text-[11px]">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="font-bold tracking-wider text-terminal-muted">
          SIGNAL vs EXECUTION
        </span>
        <span className="text-[10px] text-terminal-muted">
          engine had a direction · execution refused it
        </span>
      </div>

      <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 items-baseline">
        <span className="text-terminal-muted">SIGNAL</span>
        <span>
          <span className={`font-bold ${tone}`}>{cand.would_be_signal}</span>
          {cand.confidence != null && (
            <span className="text-terminal-muted">
              {" "}· confidence {cand.confidence}
              {cand.dynamic_confidence != null && ` · dynamic ${cand.dynamic_confidence}`}
            </span>
          )}
          {cand.confirmations_count != null && (
            <span className="text-terminal-muted"> · {cand.confirmations_count} layers confirming</span>
          )}
        </span>

        <span className="text-terminal-muted">EXECUTION</span>
        <span className="font-bold text-terminal-bear">BLOCKED</span>

        <span className="text-terminal-muted">REASON</span>
        <span className="space-y-0.5">
          {reasons.length === 0 ? (
            <span className="text-terminal-muted">—</span>
          ) : (
            reasons.map((r, i) => (
              <div key={i} className="text-gray-200">• {r}</div>
            ))
          )}
          {cand.blocked_count > reasons.length && (
            <div className="text-terminal-muted">
              …and {cand.blocked_count - reasons.length} more
            </div>
          )}
        </span>
      </div>

      <div className="text-[10px] text-terminal-muted pt-1 border-t border-terminal-border/40">
        The directional read the engine computed BEFORE execution was refused —
        not a recommendation, not tradable. The vetoes above are what govern,
        and capital protection is unchanged. Shown so a blocked signal reads as
        blocked instead of disappearing into a bare NO TRADE. The decision
        itself stays with the Hero card.
      </div>
    </div>
  );
}
