"use client";
// CANDLE PATTERNS — V7.1 Trade Explorer Phase 1 (owner, 2026-08-04).
//
// The only fully-absent Phase 1 evidence layer at the 2026-08-04 audit.
// Renders what backend `engines/candles.py` detected on the latest bar, with
// its context, so "what did the candles actually do" is visible evidence
// rather than something implicit inside a blended score.
//
// DELIBERATE OMISSIONS — these are the point, not oversights:
//   * No win rate, no probability, no "this pattern works N% of the time."
//     A pattern name is not evidence of an outcome. RVE-001/002 (owner's own
//     research) found named features that looked strongly predictive
//     collapsed to 0.0-1.1pp once confounds were controlled. Outcome stats
//     must be measured per pattern per regime from the black box first.
//   * `geometry_strength` describes how CLEAN the shape is — not how likely
//     the trade is to work. Labelled explicitly so it can't be misread.
//   * Rule 11 intact: never a BUY/SELL instruction. TradeNowCard alone owns
//     the decision; this layer changes no score, threshold or gate.

import { useMarket } from "@/lib/store";

const dirTone = (d: string) =>
  d === "BULL" ? "text-terminal-bull"
  : d === "BEAR" ? "text-terminal-bear"
  : "text-terminal-muted";

export function CandlePatternCard() {
  const { layers } = useMarket();
  const cd = (layers as any)?.candles;
  if (!cd?.ready) return null;

  const patterns: any[] = cd.patterns || [];

  return (
    <div className="panel py-2.5 space-y-2 text-[11px]">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="font-bold tracking-wider text-terminal-accent">
          CANDLE PATTERNS
        </span>
        <span className="text-terminal-muted">
          {cd.count === 0 ? "none on the latest bar" : (
            <>
              lean <span className={`font-semibold ${dirTone(cd.bias)}`}>{cd.bias}</span>
              {" "}({cd.bull_count}↑ / {cd.bear_count}↓)
            </>
          )}
        </span>
      </div>

      {patterns.length === 0 ? (
        <div className="text-terminal-muted">
          No defined candle pattern on the latest bar.
        </div>
      ) : (
        <div className="space-y-1.5">
          {patterns.map((p, i) => (
            <div key={i}>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`font-semibold ${dirTone(p.direction)}`}>
                  {p.pattern}
                </span>
                <span className="text-[10px] text-terminal-muted">
                  {p.direction} · shape {p.geometry_strength}
                </span>
                {(p.tags || []).map((t: string) => (
                  <span key={t} className="text-[10px] text-terminal-bull border border-terminal-bull/40 px-1 rounded">
                    {t}
                  </span>
                ))}
              </div>
              <div className="text-terminal-muted">{p.note}</div>
            </div>
          ))}
        </div>
      )}

      {(cd.context || []).length > 0 && (
        <div className="pt-1 border-t border-terminal-border/40">
          <span className="text-terminal-muted">Context: </span>
          <span className="text-terminal-warn font-semibold">
            {cd.context.join(" · ")}
          </span>
          <span className="text-terminal-muted"> — the pattern is happening at a level, not in open space.</span>
        </div>
      )}

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-terminal-muted pt-1 border-t border-terminal-border/40">
        <span>range {cd.range_multiple}× avg</span>
        <span>body {cd.body_pct}% of range</span>
        <span>closed at {cd.close_location_pct}% of the bar</span>
        {cd.volume_confirmed && <span className="text-terminal-bull">volume-confirmed</span>}
      </div>

      <div className="text-[10px] text-terminal-muted">
        Detection and geometry only — no win rate or probability is attached to
        any pattern. Outcome statistics have to be measured per pattern per
        regime from the black box first. Changes no score, threshold or gate;
        the decision stays with the Hero card.
      </div>
    </div>
  );
}
