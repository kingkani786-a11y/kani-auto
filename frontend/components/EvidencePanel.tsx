"use client";
// EVIDENCE PANEL — Step 6 (Evidence Panel Final, 2026-07-26). The ONE place
// evidence for the CURRENT trade lives: Price Action, Swing, VWAP, CPR,
// Gamma Wall, OI, Volume, Market Structure — nothing else, ever added.
//
// Hard rule (owner-locked): this panel NEVER states a decision, never says
// BUY/SELL, never shows a confidence or probability number. It answers
// exactly one question — "what evidence exists for this trade?" — and
// nothing more. The decision stays with TradeNowCard alone (Rule 11).
// Hierarchy: Hero -> Execution Status -> WHY HERE -> Evidence Panel (here)
// -> Support & Resistance -> Market Structure.
//
// Every row below REUSES a value some other engine already computed — zero
// new scoring, zero new thresholds:
//   Price Action / VWAP / CPR / Gamma Wall <- the Hero S/R level's own
//     evidence chips (support_resistance.py attach_evidence())
//   Swing <- structure.py's real HH/HL/LH/LL sequence (not the trivial
//     always-true "swing" field that used to live on the S/R chips)
//   OI / Volume <- the Decision Matrix's own "OI"/"Volume Profile" rows
//     (confluence.py's layers — already the single shared source those
//     other panels read too, not recomputed here)
//   Market Structure <- structure.py's event/BOS-CHOCH state

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";

type Status = "YES" | "NO" | "N/A";
type Row = { label: string; status: Status; detail?: string };

const STATUS_TONE: Record<Status, string> = {
  YES: "text-terminal-bull border-terminal-bull/30",
  NO: "text-terminal-muted border-terminal-border",
  "N/A": "text-terminal-muted/50 border-terminal-border/40",
};
const MARK: Record<Status, string> = { YES: "✓", NO: "○", "N/A": "–" };

// Owner Step 10 (MTF Confluence, 2026-07-27) — the 5 timeframes shown in the
// owner's own spec example ("5m ✓ / 15m ✓ / 1H ✓ / 4H ✓ / Daily ✓"); the
// engine also computes 1m/3m but those are left off this row (noisier,
// same "lower TF disagreement isn't a red flag" reasoning the engine itself
// already applies to higher_tf_conflict).
const MTF_ROW_TFS = ["5m", "15m", "1H", "4H", "Daily"];

export function EvidencePanel() {
  const { layers } = useMarket();
  const [sr, setSr] = useState<any>(null);
  const [struct, setStruct] = useState<any>(null);
  const [dc, setDc] = useState<any>(null);

  useEffect(() => {
    const load = () => {
      api.supportResistance().then(setSr).catch(() => {});
      api.marketStructure().then(setStruct).catch(() => {});
      // Owner Step 10 (MTF Confluence, 2026-07-27) — same decision-contract
      // source TradeRiskPanel/AI Dealer read, just this panel's own fields.
      api.decisionContract().then(setDc).catch(() => {});
    };
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  const ev = sr?.ready ? sr?.hero?.evidence : null;
  const structReady = !!struct?.ready;
  const dm = (layers as any)?.intelligence?.decision_matrix;
  const dmRow = (name: string) => (dm?.rows || []).find((r: any) => r.layer === name);
  const oiRow = dmRow("OI");
  const volRow = dmRow("Volume Profile");
  const rowStatus = (r: any): Status => (!r ? "N/A" : r.verdict === "PASS" ? "YES" : r.verdict === "FAIL" ? "NO" : "N/A");

  // Owner Step 10 (MTF Confluence, 2026-07-27) — per-TF ✓/✗ against the
  // Hero's OWN already-decided verdict (decision_contract.py's ai_dealer),
  // reusing mtf_confluence.py's per-TF verdicts. Never a second opinion:
  // ✓ means "this timeframe agrees with the Hero", not a new judgement.
  const mtf = dc?.mtf;
  const heroVerdict = dc?.ai_dealer?.verdict;
  const heroBias = heroVerdict === "BUY CALL" ? "BUY" : heroVerdict === "BUY PUT" ? "SELL" : null;
  const mtfTfs = mtf?.timeframes || {};
  const mtfReady = !!mtf?.ready && !!heroBias;

  if (!ev && !dm?.rows && !structReady && !mtfReady) return null;

  const rows: Row[] = [
    { label: "Price Action", status: ev ? (ev.price_action ? "YES" : "NO") : "N/A" },
    { label: "Swing", status: structReady ? (struct.swing && struct.swing !== "—" ? "YES" : "NO") : "N/A", detail: structReady ? struct.swing : undefined },
    { label: "VWAP", status: ev ? (ev.vwap ? "YES" : "NO") : "N/A" },
    { label: "CPR", status: ev ? (ev.cpr ? "YES" : "NO") : "N/A" },
    { label: "Gamma Wall", status: ev ? (ev.gamma_wall ? "YES" : "NO") : "N/A" },
    { label: "OI", status: rowStatus(oiRow), detail: oiRow?.reason },
    { label: "Volume", status: rowStatus(volRow), detail: volRow?.reason },
    { label: "Market Structure", status: structReady ? (struct.event && struct.event !== "NONE" ? "YES" : "NO") : "N/A", detail: structReady ? (struct.bos_choch || struct.event) : undefined },
  ];

  return (
    <section className="panel border border-terminal-border/60">
      <div className="panel-title">Evidence <span className="text-[10px] text-terminal-muted font-normal">(what supports this trade — not a decision)</span></div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-1">
        {rows.map((r) => (
          <div key={r.label} className={`rounded-lg border px-2.5 py-1.5 ${STATUS_TONE[r.status]}`}>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold">{r.label}</span>
              <span className="text-sm font-bold">{MARK[r.status]}</span>
            </div>
            {r.detail && <div className="text-[9px] opacity-70 truncate" title={r.detail}>{r.detail}</div>}
          </div>
        ))}
      </div>

      {mtfReady && (
        <div className="text-[10px] border-t border-terminal-border/40 mt-2 pt-1.5">
          <div className="text-terminal-muted font-semibold mb-1 uppercase">Multi Timeframe</div>
          <div className="flex flex-wrap gap-x-3 gap-y-1">
            {MTF_ROW_TFS.map((label) => {
              const v = mtfTfs[label]?.verdict;
              const agrees = v === heroBias;
              const has = v && v !== "NEUTRAL";
              const cls = !has ? "text-terminal-muted/50" : agrees ? "text-terminal-bull" : "text-terminal-bear";
              return (
                <span key={label} className={cls}>
                  {label} {has ? (agrees ? "✓" : "✗") : "–"}
                </span>
              );
            })}
          </div>
        </div>
      )}

      <div className="text-[10px] text-terminal-muted mt-2">
        Evidence only — never a BUY/SELL call, confidence, or probability. The decision stays with the Hero card above.
      </div>
    </section>
  );
}
