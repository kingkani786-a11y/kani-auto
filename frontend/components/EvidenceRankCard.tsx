"use client";
// WHY THIS DIRECTION — V7.1 Trade Explorer Phase 2 (owner, 2026-08-04).
//
// The owner's framing this implements:
//   "எல்லா indicators-ஐ சமமாக கலந்து ஒரு opaque score கொடுக்கக்கூடாது...
//    எந்த காரணத்தால் entry உருவாகிறதோ, அந்த காரணமே முதலில் காட்டப்பட வேண்டும்."
//
// Seven weighted layers currently collapse into one composite. A 72 built
// from Trend+Structure and a 72 built from OI+MTF look identical. This card
// names the driver instead: PRIMARY / CONFIRMING / CONTRADICTORY /
// INSUFFICIENT, over the SAME scores the composite already used.
//
// BOUNDARIES, deliberate:
//   * Reads `layers.evidence_rank`, which computes no new score and changes
//     no existing one. Remove the backend block and the decision is
//     byte-identical.
//   * PRIMARY = strongest supporting evidence right now. NOT a claim the
//     trade will work; no probability is attached anywhere.
//   * The Candle Pattern layer appears as evidence but can never be PRIMARY —
//     a detection has no comparable 0-100 score, and inventing one to let it
//     rank would be exactly the fabricated ranking this card exists to avoid.
//   * Rule 11: never an instruction. TradeNowCard alone owns the decision.
//   * CONTRADICTORY is the general form of OBS-15's fix — a layer leaning
//     against the chosen direction gets named, not averaged away.

import { useMarket } from "@/lib/store";

export function EvidenceRankCard() {
  const { layers } = useMarket();
  const er = (layers as any)?.evidence_rank;
  if (!er?.ready || !er.primary) return null;

  const bull = er.direction === "BULL";
  const dirTone = bull ? "text-terminal-bull" : "text-terminal-bear";
  const confirming: any[] = er.confirming || [];
  const contra: any[] = er.contradicting || [];
  const insuff: any[] = er.insufficient || [];

  const Row = ({ r, tone }: { r: any; tone: string }) => (
    <div className="flex items-baseline gap-2 flex-wrap">
      <span className={`font-semibold ${tone}`}>{r.label}</span>
      {r.score != null && (
        <span className="text-terminal-muted tabular-nums">{r.score}</span>
      )}
      {r.rankable === false && (
        <span className="text-[10px] text-terminal-muted">(not rankable)</span>
      )}
      {r.detail && <span className="text-terminal-muted">— {r.detail}</span>}
    </div>
  );

  return (
    <div className="panel py-2.5 space-y-2 text-[11px]">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="font-bold tracking-wider text-terminal-accent">
          WHY THIS DIRECTION
        </span>
        <span className={`font-bold ${dirTone}`}>{er.direction}</span>
      </div>

      <div className="space-y-1.5">
        <div>
          <div className="text-[10px] text-terminal-muted uppercase tracking-wide">
            Primary basis{er.primary_is_sole_driver ? "" : " (shared lead)"}
          </div>
          <Row r={er.primary} tone={dirTone} />
        </div>

        {confirming.length > 0 && (
          <div>
            <div className="text-[10px] text-terminal-muted uppercase tracking-wide">
              Confirming ({confirming.length})
            </div>
            <div className="space-y-0.5">
              {confirming.map((r, i) => <Row key={i} r={r} tone="text-gray-200" />)}
            </div>
          </div>
        )}

        {contra.length > 0 && (
          <div>
            <div className="text-[10px] text-terminal-warn uppercase tracking-wide font-bold">
              ⚠ Contradicting ({contra.length})
            </div>
            <div className="space-y-0.5">
              {contra.map((r, i) => (
                <div key={i} className="flex items-baseline gap-2 flex-wrap">
                  <span className="font-semibold text-terminal-warn">{r.label}</span>
                  {r.opposite != null && (
                    <span className="text-terminal-muted tabular-nums">{r.opposite}</span>
                  )}
                  <span className="text-terminal-muted">leans {r.leans}</span>
                  {r.detail && <span className="text-terminal-muted">— {r.detail}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {insuff.length > 0 && (
          <div className="text-terminal-muted">
            <span className="text-[10px] uppercase tracking-wide">Insufficient: </span>
            {insuff.map((r) => r.label).join(", ")}
          </div>
        )}
      </div>

      <div className={`pt-1.5 border-t border-terminal-border/40 ${er.contested ? "text-terminal-warn" : "text-gray-200"}`}>
        {er.conclusion}
      </div>

      <div className="text-[10px] text-terminal-muted">
        A classification of scores the engine already computed — no new score,
        no threshold, no effect on the decision. &quot;Primary&quot; means strongest
        supporting evidence right now, not that the trade will work. The
        decision stays with the Hero card.
      </div>
    </div>
  );
}
