"use client";
// Enterprise LTS — AI Health Score strip. One line, top of dashboard: system
// health at a glance with 🟢/🟡/🔴 dots. Derivation-only (aggregates existing
// health-center + status + report-card). Honest — never fakes readiness.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";

type Tone = "green" | "amber" | "red" | "muted";
const dot: Record<Tone, string> = {
  green: "bg-terminal-bull", amber: "bg-terminal-warn", red: "bg-terminal-bear", muted: "bg-terminal-muted",
};

function Item({ label, value, tone }: { label: string; value: string; tone: Tone }) {
  return (
    <span className="flex items-center gap-1.5 whitespace-nowrap">
      <span className={`w-1.5 h-1.5 rounded-full ${dot[tone]} ${tone === "green" ? "animate-pulse" : ""}`} />
      <span className="text-terminal-muted">{label}:</span>
      <span className="font-mono">{value}</span>
    </span>
  );
}

export function AIHealthStrip() {
  const { status, decision, killSwitch } = useMarket();
  const [hc, setHc] = useState<any>(null);
  const [rc, setRc] = useState<any>(null);

  useEffect(() => {
    const load = () => {
      api.healthCenter().then(setHc).catch(() => {});
      api.reportCard().then(setRc).catch(() => {});
    };
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  if (!status?.connected || !hc) return null;
  const prod = hc.production || {};
  const comps = hc.components || {};
  // OBS-12 fix (owner, 2026-08-05) — comps.data_quality?.detail traces to
  // health_center.py's `state.data_quality` (source A: did the last tick
  // raise a BrokerError?), NOT the same value Kill Switch/the gate actually
  // run on (source B: data_quality.report().overall). A can read GOOD while
  // B reads POOR — P5A's state_consistency.py caught this live on
  // 2026-08-04 and self-cleared once the two re-synced, exactly as
  // designed. Mirrors the OR-in-B guard P0 already shipped in
  // FeedDiagnostics.tsx — reuses killSwitch.reason_tags (already computed
  // from B, no new fetch) rather than re-deriving B here. Conservative
  // only: can turn a false "GOOD" into "POOR", never the reverse.
  const bPoor = (killSwitch?.reason_tags || []).includes("DATA_QUALITY");
  const dq = bPoor ? "POOR" : (comps.data_quality?.detail ?? "—");
  const latency = prod.latency_ms;
  const conf = (decision as any)?.intelligence_synthesis?.conviction;
  const cal = rc?.scorecard?.calibration_grade;
  const vt = prod.validated_trades ?? 0;
  const cert = prod.certification ?? "NOT READY";

  // Split the single confusing score into INFRA (feed/broker/engine — live now)
  // vs LEARNING (calibration/DNA/validation — builds with data). Feed can be
  // 100% while Learning is 20% — both true; never averaged into one number.
  const avg = (keys: string[]) => {
    const v = keys.map((k) => comps[k]?.score).filter((x: any) => x != null);
    return v.length ? Math.round(v.reduce((a: number, b: number) => a + b, 0) / v.length) : 0;
  };
  const infra = avg(["data_quality", "broker", "ai_engine", "memory"]);
  const learning = avg(["learning", "dna", "audit", "persistence"]);
  const toneOf = (v: number): Tone => (v >= 80 ? "green" : v >= 50 ? "amber" : "red");

  return (
    <div className="panel py-1.5 px-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px]">
      <span className="flex items-center gap-2 font-bold tracking-wider text-terminal-accent">
        SYSTEM
        <span className="flex items-center gap-1"><span className={`w-1.5 h-1.5 rounded-full ${dot[toneOf(infra)]}`} />
          <span className="font-mono">Infra {infra}%</span></span>
        <span className="flex items-center gap-1"><span className={`w-1.5 h-1.5 rounded-full ${dot[toneOf(learning)]}`} />
          <span className="font-mono font-normal text-terminal-muted">Learning {learning}%{learning < 50 ? " (building)" : ""}</span></span>
      </span>
      <Item label="Data" value={dq} tone={dq === "GOOD" ? "green" : dq === "POOR" ? "red" : "amber"} />
      <Item label="Feed" value={latency != null ? `${latency} ms` : "—"}
            tone={latency == null ? "muted" : latency < 250 ? "green" : latency < 600 ? "amber" : "red"} />
      <Item label="Broker" value={status.connected ? "Connected" : "Offline"} tone={status.connected ? "green" : "red"} />
      <Item label="AI Conviction" value={conf != null ? `${conf}%` : "—"}
            tone={conf == null ? "muted" : conf >= 75 ? "green" : conf >= 60 ? "amber" : "red"} />
      <Item label="Calibration" value={cal != null ? `${cal}/100` : "building"}
            tone={cal == null ? "muted" : cal >= 80 ? "green" : cal >= 65 ? "amber" : "red"} />
      <Item label="Validated" value={`${vt} / 100`} tone={vt >= 100 ? "green" : vt > 0 ? "amber" : "red"} />
      <Item label="Production"
            value={cert === "LIVE READY" ? "100% Live Ready" : `${Math.min(100, Math.round(vt))}%`}
            tone={cert === "LIVE READY" ? "green" : cert === "VALIDATION IN PROGRESS" ? "amber" : "red"} />
    </div>
  );
}
