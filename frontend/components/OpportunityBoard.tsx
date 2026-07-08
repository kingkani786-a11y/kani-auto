"use client";
// V26 — 🔥 AI Market Opportunity Board. Staged scan results: momentum L1 →
// chains for top candidates only (L2). Click a card → switches the platform
// to that instrument, opening the full Universal Strike Engine (L3).
// Premium fields absent ⇒ chain unavailable — shown as "Unavailable", never estimated.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function OpportunityBoard() {
  const [d, setD] = useState<any>(null);
  const [switching, setSwitching] = useState("");

  useEffect(() => {
    const load = () =>
      fetch("/api/opportunities", { headers: { "X-Auth-Token": localStorage.getItem("cat_token") || "" } })
        .then((r) => (r.ok ? r.json() : null)).then(setD).catch(() => {});
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  if (!d?.ready || (!(d.ce || []).length && !(d.pe || []).length)) return null;

  const pick = async (sym: string) => {
    setSwitching(sym);
    try { await api.setSymbol(sym); } catch {}
    setSwitching("");
  };

  const Row = ({ c }: { c: any }) => (
    <button onClick={() => pick(c.symbol)} disabled={switching === c.symbol}
      className={`w-full text-left rounded-md border px-2 py-1.5 text-[11px] hover:border-terminal-accent/60 transition-colors ${
        c.status === "READY" ? "border-terminal-bull/50" : "border-terminal-border/60"}`}>
      <div className="flex items-center justify-between">
        <span className="font-mono font-bold">
          {c.symbol}{c.strike ? <span className={c.type === "CE" ? " text-terminal-bull" : " text-terminal-bear"}> {Math.round(c.strike)} {c.type}</span> : null}
        </span>
        <span className="font-mono">AI {Math.round(c.ai_score)}</span>
      </div>
      <div className="flex items-center justify-between text-terminal-muted">
        <span>
          {c.premium != null
            ? <>₹{c.premium} → SL ₹{c.premium_sl} · T1 ₹{c.premium_t1}</>
            : <span className="italic">Premium: Unavailable ({c.detail || "no chain"})</span>}
        </span>
        <span>{c.prob_itm != null ? `ITM ${Math.round(c.prob_itm)}%` : `${c.change_pct > 0 ? "+" : ""}${c.change_pct}%`}</span>
      </div>
      <div className="flex items-center justify-between text-[10px]">
        <span className={c.status === "READY" ? "text-terminal-bull font-bold" : "text-terminal-warn"}>{c.status}</span>
        <span className="text-terminal-muted">tap → full strike engine</span>
      </div>
    </button>
  );

  return (
    <div className="panel py-2.5">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
        <span className="font-bold tracking-wider text-terminal-accent text-[12px]">🔥 AI MARKET OPPORTUNITIES</span>
        {d.meter && (
          <span className="text-[10px] text-terminal-muted">
            scanned {d.meter.scanned} · deep {d.meter.deep_scanned} · options {d.meter.options_analysed}
          </span>
        )}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <div className="stat-label mb-1 text-terminal-bull">Best CE (bullish)</div>
          <div className="space-y-1.5">{(d.ce || []).map((c: any) => <Row key={c.symbol} c={c} />)}</div>
          {!(d.ce || []).length && <div className="text-[11px] text-terminal-muted">No bullish candidates this cycle.</div>}
        </div>
        <div>
          <div className="stat-label mb-1 text-terminal-bear">Best PE (bearish)</div>
          <div className="space-y-1.5">{(d.pe || []).map((c: any) => <Row key={c.symbol} c={c} />)}</div>
          {!(d.pe || []).length && <div className="text-[11px] text-terminal-muted">No bearish candidates this cycle.</div>}
        </div>
      </div>
      <div className="text-[10px] text-terminal-muted mt-1.5">{d.note}</div>
    </div>
  );
}
