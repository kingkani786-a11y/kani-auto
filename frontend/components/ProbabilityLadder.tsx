"use client";
// PHASE 28 — PROBABILITY LADDER. Touch-probability of reaching each target and
// of hitting the stop first. Derivation-only; probabilities, not certainty.

import { useMarket } from "@/lib/store";

const bandTone = (b?: string) =>
  b === "VERY HIGH" ? "text-terminal-bull" : b === "HIGH" ? "text-terminal-bull"
  : b === "MEDIUM" ? "text-terminal-warn" : "text-terminal-bear";
const barTone = (b?: string) =>
  b === "VERY HIGH" || b === "HIGH" ? "bg-terminal-bull" : b === "MEDIUM" ? "bg-terminal-warn" : "bg-terminal-bear";

export function ProbabilityLadder() {
  const { decision } = useMarket();
  const lad = (decision as any)?.probability_ladder;
  if (!lad?.ready || !lad.rungs?.length) return null;

  const Row = ({ label, price, prob, band }: { label: string; price: number; prob: number; band: string }) => (
    <div className="flex items-center gap-3">
      <span className="w-8 text-xs font-mono font-bold">{label}</span>
      <span className="w-16 text-xs font-mono text-terminal-muted">{price?.toLocaleString("en-IN")}</span>
      <div className="flex-1 h-2 rounded-full bg-terminal-bg overflow-hidden">
        <div className={`h-full ${barTone(band)}`} style={{ width: `${Math.max(3, prob)}%` }} />
      </div>
      <span className={`w-12 text-right text-xs font-mono font-bold ${bandTone(band)}`}>{prob}%</span>
      <span className={`w-20 text-right text-[10px] ${bandTone(band)}`}>{band}</span>
    </div>
  );

  return (
    <div className="panel">
      <div className="panel-title">Probability Ladder — touch odds (not certainty)</div>
      <div className="space-y-1.5">
        {lad.rungs.map((r: any) => (
          <Row key={r.level} label={r.level} price={r.price} prob={r.probability} band={r.band} />
        ))}
        {lad.stop_loss && (
          <div className="pt-1.5 mt-1 border-t border-terminal-border/40">
            <Row label="SL" price={lad.stop_loss.price} prob={lad.stop_loss.probability} band={lad.stop_loss.band} />
          </div>
        )}
      </div>
      <div className="text-[10px] text-terminal-muted mt-2">
        Expected move ≈ {lad.expected_move} pts · edge {lad.edge}%. {lad.note}
      </div>
    </div>
  );
}
