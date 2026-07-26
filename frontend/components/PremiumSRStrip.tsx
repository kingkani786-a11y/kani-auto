"use client";
// PREMIUM S/R STRIP — Step 2 (Hero Dashboard Finalization, 2026-07-26).
// Minimal always-visible premium-level summary for the top-of-page zone.
// Mirrors SRHeroCard's "nearest single level" pattern but for the ATM
// option's own premium — reuses the existing supportResistancePremium()
// data (same math as SupportResistancePanel's full breakdown), just picks
// the single nearest level per side instead of the whole list. Spot and
// Premium are shown in SEPARATE strips (this one vs SRHeroCard) — never
// mixed in one panel, per the roadmap's own Step 4 rule stated early.
// Full multi-level breakdown stays in SupportResistancePanel (Advanced).

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";

function nearest(d: any): { label: string; level: number; touches: number; bounce_pct: number | null; side: "R" | "S" } | null {
  if (!d?.ready || d.cmp == null) return null;
  const all = [
    ...(d.resistance || []).map((l: any) => ({ ...l, side: "R" as const })),
    ...(d.support || []).map((l: any) => ({ ...l, side: "S" as const })),
  ];
  if (all.length === 0) return null;
  return all.reduce((best, l) => (Math.abs(l.level - d.cmp) < Math.abs(best.level - d.cmp) ? l : best), all[0]);
}

export function PremiumSRStrip() {
  const { atm } = useMarket();
  const [ce, setCe] = useState<any>(null);
  const [pe, setPe] = useState<any>(null);

  useEffect(() => {
    if (!atm) return;
    const load = () => {
      api.supportResistancePremium(atm, "CE").then(setCe).catch(() => {});
      api.supportResistancePremium(atm, "PE").then(setPe).catch(() => {});
    };
    load();
    const id = setInterval(load, 20000);
    return () => clearInterval(id);
  }, [atm]);

  if (!atm) return null;
  const nCe = nearest(ce);
  const nPe = nearest(pe);
  if (!nCe && !nPe) return null;

  const Row = ({ typ, cmp, n }: { typ: string; cmp: number | null; n: ReturnType<typeof nearest> }) => {
    if (!n) return null;
    return (
      <div className="flex items-center gap-2 text-[11px]">
        <span className="text-terminal-muted w-16">{atm} {typ}</span>
        <span className="text-terminal-muted">₹{cmp}</span>
        <span className={n.side === "R" ? "text-terminal-bear" : "text-terminal-bull"}>
          {n.label} ({n.side}) ₹{n.level}
        </span>
        <span className="text-terminal-muted">{n.touches}× · {n.bounce_pct ?? "—"}%</span>
      </div>
    );
  };

  return (
    <div className="panel border border-terminal-border/60 py-2">
      <div className="text-[10px] text-terminal-muted uppercase tracking-wide mb-1">Premium S/R (nearest)</div>
      <div className="flex flex-wrap gap-x-6 gap-y-1">
        <Row typ="CE" cmp={ce?.cmp} n={nCe} />
        <Row typ="PE" cmp={pe?.cmp} n={nPe} />
      </div>
    </div>
  );
}
