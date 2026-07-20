"use client";
// 🧠 AI THINKING NOW — makes the engine's reasoning visible. A live reasoning
// cycle (OBSERVE→DETECT→REASON→EXPECT→VERIFY→LEARN) over the single best premium
// opportunity: what it's watching, which confirmations are in/out, what it
// expects (a conditional, not a prediction), the risk, and a confidence
// sparkline. Deterministic — evidence-based reasoning, NOT a trade call.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BuyChecklist } from "@/components/BuyChecklist";

function Spark({ data }: { data: number[] }) {
  if (!data || data.length < 2) return null;
  const w = 120, h = 28, max = 100, min = 0;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / (max - min)) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const up = data[data.length - 1] >= data[0];
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline points={pts} fill="none" strokeWidth="1.5"
        className={up ? "stroke-terminal-bull" : "stroke-terminal-bear"} />
    </svg>
  );
}

export function AIThinkingPanel() {
  const [t, setT] = useState<any>(null);
  const [c, setC] = useState<any>(null);   // the shared BUY checklist object
  useEffect(() => {
    const load = () => {
      api.premiumRadar(8).then((d: any) => setT(d?.thinking || null)).catch(() => {});
      api.decisionContract().then(setC).catch(() => {});
    };
    load(); const id = setInterval(load, 4000); return () => clearInterval(id);
  }, []);

  if (!t) return null; // nothing running to reason about (quiet market)

  return (
    <section className="panel space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">🧠 AI Thinking Now <span className="text-[10px] text-terminal-muted">(evidence-based · not a prediction)</span></h2>
        <span className="text-[10px] text-terminal-muted">next review {t.next_review}</span>
      </div>

      <div className="text-[10px] text-terminal-muted tracking-wide">{t.cycle}</div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
        <div className="space-y-1">
          <div><span className="text-terminal-muted">Watching </span><b className="text-white">{t.watching}</b> <span className={`${t.phase?.code === "RUNNER_CONFIRMED" ? "text-terminal-bear" : t.phase?.code === "RUNNER_BUILDING" ? "text-terminal-warn" : "text-terminal-bull"}`}>{t.phase?.dot} {t.phase?.label}{t.phase?.action ? ` (${t.phase.action})` : ""}</span></div>
          {/* THE shared BUY checklist — same backend object as the hero
              (owner 2026-07-21). This panel used to render the radar's own 4
              checks (Premium velocity / Velocity rising / Volume expansion /
              OI build-up), which is a DIFFERENT list from the hero's — two
              "checklists" that could disagree on screen. Radar confirmations
              still shown below, clearly labelled as radar-only. */}
          <BuyChecklist c={c} compact />
          <div className="text-[10px] text-terminal-muted pt-1">RADAR CONFIRMATIONS (this strike only)</div>
          <ul className="space-y-0.5">
            {t.confirmed.map((label: string, i: number) => (
              <li key={`c${i}`} className="text-terminal-bull">✔ {label}</li>
            ))}
            {(t.missing || []).map((label: string, i: number) => (
              <li key={`m${i}`} className="text-terminal-muted">✗ {label}</li>
            ))}
          </ul>
          <div className="text-terminal-muted">{t.confirmations_line}</div>
        </div>
        <div className="space-y-1">
          {t.cause && <div><span className="text-terminal-muted">Why: </span><span className="text-white">{t.cause}</span></div>}
          <div><span className="text-terminal-muted">Expectation: </span><span className="text-white">{t.expectation}</span></div>
          <div><span className="text-terminal-muted">Risk: </span><span className="text-terminal-warn">{t.risk}</span></div>
          <div className="flex items-center gap-2">
            <span className="text-terminal-muted">Confidence</span>
            <b className="text-white tabular-nums">{t.confidence}</b>
            <Spark data={t.score_hist} />
          </div>
        </div>
      </div>

      {/* Evidence Meter — where the confidence comes from */}
      {t.evidence && (
        <div className="border-t border-terminal-border pt-2">
          <div className="text-[10px] text-terminal-muted mb-1">EVIDENCE (declared signal strength)</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-0.5">
            {Object.entries(t.evidence).map(([k, v]: any) => (
              <div key={k} className="flex items-center gap-2 text-[11px]">
                <span className="text-terminal-muted w-20 shrink-0">{k}</span>
                <div className="flex-1 h-1.5 bg-terminal-border rounded overflow-hidden">
                  <div className={`h-full ${v >= 75 ? "bg-terminal-bull" : v >= 50 ? "bg-terminal-warn" : "bg-terminal-bear"}`} style={{ width: `${v}%` }} />
                </div>
                <span className="tabular-nums text-terminal-muted w-8 text-right">{v}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Invalidation — the pre-stated condition that cancels the thesis */}
      {t.invalidation && (
        <div className="border border-terminal-bear/30 rounded p-2 text-[11px]">
          <span className="text-terminal-bear font-semibold">Invalidation (I change my mind IF): </span>
          <span className="text-white">{t.invalidation.conditions.join(" · ")}</span>
          <span className="text-terminal-muted"> → {t.invalidation.then}</span>
        </div>
      )}

      <div className="text-[10px] text-terminal-muted">{t.note}</div>
    </section>
  );
}
