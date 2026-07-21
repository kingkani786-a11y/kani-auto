"use client";
// V24.5 — One-Click Execution Card + Dual-Mode Opportunity Radar.
// The single actionable instruction at the very top. Derivation-only display.

import { useMarket } from "@/lib/store";

function speak(text: string) {
  try {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.05;
    window.speechSynthesis.speak(u);
  } catch {}
}

export function ExecutionCard() {
  const { decision } = useMarket();
  const x = (decision as any)?.execution_card;
  const clock = (decision as any)?.market_clock;
  if (!x?.ready) return null;

  const radar = x.opportunity_radar || [];

  if (!x.is_trade) {
    return (
      <div className="panel border-terminal-warn/40">
        <div className="text-sm font-bold text-terminal-warn mb-1">⏳ {x.actionable}</div>
        <RadarRow radar={radar} />
      </div>
    );
  }

  const c = x.card || {};
  return (
    <div className="panel border-2 border-terminal-bull/50 bg-terminal-bull/5">
      {/* AI Market Clock (§6) + Voice (§8) */}
      <div className="flex items-center justify-between mb-1">
        {clock?.current && (
          <span className="text-[10px] text-terminal-muted">
            🕐 {clock.ist_time} · {clock.current.phase}{clock.no_fresh_entries ? " · NO FRESH ENTRIES" : ""}
          </span>
        )}
        <button onClick={() => speak(x.actionable)}
          className="text-[10px] px-2 py-0.5 rounded border border-terminal-border text-terminal-muted hover:text-white hover:border-terminal-accent">
          🔊 Speak
        </button>
      </div>
      {/* the one actionable line */}
      <div className="text-sm sm:text-base font-bold text-terminal-bull mb-2 leading-snug">
        {x.actionable}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
        <Cell label="Strike" value={`${c.strike} ${c.type}`} />
        <Cell label="Entry ₹" value={c.entry_premium} />
        <Cell label="Exp ₹" value={`${c.expected_premium?.[0]}–${c.expected_premium?.[1]}`} tone="text-terminal-bull" />
        <Cell label="SL ₹" value={c.stop_premium} tone="text-terminal-bear" />
        <Cell label="NIFTY pts" value={`+${c.expected_points?.[0]}–${c.expected_points?.[1]}`} />
        <Cell label="Probability" value={`${c.probability}%`} />
        <Cell label="Hold" value={`${c.hold_minutes?.[0]}–${c.hold_minutes?.[1]}m`} />
        <Cell label="Tier" value={c.tier} tone="text-terminal-accent" />
      </div>

      {c.alternate_strikes?.length > 0 && (
        <div className="text-[11px] text-terminal-muted mt-2">
          Alternate strikes: {c.alternate_strikes.join(" · ")}
        </div>
      )}
      <div className="text-[11px] text-terminal-muted mt-1">Exit rule: {c.exit_rule}</div>

      <PointCapture pc={x.point_capture} />
      <RadarRow radar={radar} />
    </div>
  );
}

function Cell({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className={`font-mono ${tone ?? ""}`}>{value ?? "—"}</div>
    </div>
  );
}

function PointCapture({ pc }: { pc: any }) {
  // Renamed from "Point Capture Probability" 2026-07-21. It rendered a declared
  // decay curve as probability; measured against the black box it overstated
  // reality 3x-50x. Now shows OBSERVED historical frequency with sample size,
  // explicitly labelled not-a-prediction (owner: history and prediction must
  // never wear the same word).
  const rows: any[] = pc?.rows || [];
  if (!rows.length) return null;
  const observed = !!pc?.observed;
  return (
    <div className="mt-3 pt-2 border-t border-terminal-border/40">
      <div className="stat-label mb-1">
        {observed ? "Observed outcomes — historical frequency" : "Modelled (low sample)"}
      </div>
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-center text-[11px]">
        {rows.map((p: any) => (
          <div key={p.points}>
            <div className="font-mono">{p.points}pt</div>
            <div className="text-gray-200 tabular-nums">{p.reached_pct == null ? "—" : `${p.reached_pct}%`}</div>
          </div>
        ))}
      </div>
      <div className="text-[10px] text-terminal-muted mt-1">
        {observed
          ? `Of ${(pc?.sample_n ?? 0).toLocaleString("en-IN")} past ignitions — NOT a forecast`
          : `Sample too small (${pc?.sample_n ?? 0}) — declared model`}
      </div>
    </div>
  );
}

function RadarRow({ radar }: { radar: any[] }) {
  if (!radar?.length) return null;
  return (
    <div className="mt-3 pt-2 border-t border-terminal-border/40">
      <div className="stat-label mb-1">Opportunity Ladder</div>
      <div className="space-y-0.5">
        {radar.map((o) => (
          <div key={o.mode} className="flex items-center justify-between text-[11px]">
            <span className="w-24">{o.label}</span>
            <span className="text-terminal-muted flex-1 text-center">{o.expected_points?.[0]}–{o.expected_points?.[1]} pts</span>
            <span className={`w-14 text-right font-mono ${o.probability >= 75 ? "text-terminal-bull" : o.probability >= 55 ? "text-terminal-warn" : "text-terminal-muted"}`}>{o.probability}%</span>
            <span className="w-20 text-right text-terminal-muted">{o.time ?? (o.eta_min ? `${o.eta_min}m` : "")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
