"use client";
// DYNAMIC SUPPORT/RESISTANCE — Phase 2 (owner, 2026-07-23, item #5).
// Spot levels (swing-fractal clustering + real touch/bounce/break stats from
// candle history), CPR (daily/weekly/monthly pivots — fixed formula, not
// tuned), per-level evidence (VWAP/Volume Node/CPR/OI Wall confluence — each
// read from its own owning engine, never re-derived), and Premium S/R for
// the current ATM strike (persisted tick log, same math reused unchanged).

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";

const stars = (n: number) => "★".repeat(n) + "☆".repeat(5 - n);
const EVIDENCE_LABEL: Record<string, string> = {
  vwap: "VWAP", swing: "Swing", volume_node: "Vol Node", cpr: "CPR", oi_wall: "OI Wall",
};

function EvidenceChips({ ev }: { ev: any }) {
  if (!ev) return null;
  return (
    <div className="flex flex-wrap gap-x-2 text-[9px] pl-8 pb-0.5">
      {Object.entries(EVIDENCE_LABEL).map(([k, label]) => (
        <span key={k} className={ev[k] ? "text-terminal-bull" : "text-terminal-muted/60"}>
          {ev[k] ? "✓" : "○"} {label}
        </span>
      ))}
    </div>
  );
}

function Level({ l }: { l: any }) {
  return (
    <div className="border-b border-terminal-border/20 py-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-terminal-muted w-8">{l.label}</span>
        <span className="tabular-nums text-white font-semibold">{l.level}</span>
        <span className="text-terminal-muted">{l.touches}× touched</span>
        <span className="text-terminal-bull">{l.bounce_pct != null ? `${l.bounce_pct}% bounce` : "—"}</span>
        <span className="text-terminal-warn">{stars(l.strength_stars)}</span>
      </div>
      <EvidenceChips ev={l.evidence} />
    </div>
  );
}

function PivotRow({ label, p }: { label: string; p: any }) {
  if (!p || p.pivot == null) return null;
  return (
    <div className="flex items-center gap-2 text-[10px] text-terminal-muted overflow-x-auto">
      <span className="w-14 shrink-0">{label}</span>
      <span>S3 {p.s3}</span><span>S2 {p.s2}</span><span>S1 {p.s1}</span>
      <span className="text-white font-semibold">P {p.pivot}</span>
      <span>R1 {p.r1}</span><span>R2 {p.r2}</span><span>R3 {p.r3}</span>
    </div>
  );
}

function PremiumSR({ atm }: { atm: number | null }) {
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

  const Row = ({ typ, d }: { typ: string; d: any }) => {
    if (!d) return null;
    if (!d.ready) {
      return <div className="text-[10px] text-terminal-muted">{atm} {typ}: {d.reason || "insufficient premium history today"}</div>;
    }
    return (
      <div className="text-[10px] space-y-0.5">
        <div className="text-terminal-muted font-semibold">{atm} {typ} · premium {d.cmp}</div>
        {d.resistance.map((l: any) => (
          <div key={l.label} className="flex justify-between text-terminal-bear">
            <span>{l.label} (R)</span><span>₹{l.level} · {l.touches}× · {l.bounce_pct ?? "—"}%</span>
          </div>
        ))}
        {d.support.map((l: any) => (
          <div key={l.label} className="flex justify-between text-terminal-bull">
            <span>{l.label} (S)</span><span>₹{l.level} · {l.touches}× · {l.bounce_pct ?? "—"}%</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2 pt-2 border-t border-terminal-border/40">
      <Row typ="CE" d={ce} />
      <Row typ="PE" d={pe} />
    </div>
  );
}

export function SupportResistancePanel() {
  const [r, setR] = useState<any>(null);
  const { atm } = useMarket();
  useEffect(() => {
    const load = () => api.supportResistance?.().then(setR).catch(() => {});
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);
  if (!r) return null;

  return (
    <div className="panel border border-terminal-border/60">
      <div className="flex items-baseline justify-between mb-2">
        <div className="panel-title mb-0">Dynamic Support / Resistance <span className="text-[10px] text-terminal-muted font-normal">(spot + premium)</span></div>
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
      {r.cpr && (
        <div className="space-y-0.5 mt-2 pt-2 border-t border-terminal-border/40">
          <div className="text-[10px] text-terminal-muted font-semibold uppercase">CPR / Pivots</div>
          <PivotRow label="Daily" p={r.cpr.daily} />
          <PivotRow label="Weekly" p={r.cpr.weekly} />
          <PivotRow label="Monthly" p={r.cpr.monthly} />
        </div>
      )}
      <PremiumSR atm={atm ?? null} />
    </div>
  );
}
