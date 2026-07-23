"use client";
// PHASE 39 — AI COMMAND CENTER. One unified cockpit: live status tiles +
// launchers to every module. Read-only aggregation of existing state — no
// engine logic, fully additive.

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";

const gradeTone = (g?: string) =>
  g === "A+" || g === "A" ? "text-terminal-bull" : g === "B" ? "text-terminal-warn"
  : g === "BUILDING" ? "text-terminal-muted" : "text-terminal-bear";

function Tile({ label, value, tone, href }: { label: string; value: React.ReactNode; tone?: string; href?: string }) {
  const inner = (
    <div className="panel h-full hover:border-terminal-accent/50 transition-colors">
      <div className="stat-label">{label}</div>
      <div className={`stat-value text-lg ${tone ?? ""}`}>{value}</div>
    </div>
  );
  return href ? <Link href={href}>{inner}</Link> : inner;
}

const LAUNCHERS: [string, string][] = [
  ["Dashboard", "/"], ["Analysis", "/advanced"], ["AI Brain", "/brain"],
  ["Chief Strategist", "/strategist"], ["Market DNA", "/dna"], ["Simulator", "/simulator"],
  ["Evolution", "/evolution"], ["Research Lab", "/research"], ["Weights", "/weights"],
  ["Scanner", "/scanner"], ["Replay", "/replay"], ["Analytics", "/analytics"],
  ["Audit", "/audit"], ["Journal", "/journal"], ["Health", "/health"], ["Settings", "/settings"],
];

export default function CockpitPage() {
  const { status, decision, killSwitch, safeMode, spot } = useMarket();
  const [hc, setHc] = useState<any>(null);
  const [pp, setPp] = useState<any>(null);
  const [rm, setRm] = useState<any>(null);
  const [vd, setVd] = useState<any>(null);

  useEffect(() => {
    const load = () => {
      api.healthCenter().then(setHc).catch(() => {});
      api.healthPersistence().then(setPp).catch(() => {});
      api.roadmap().then(setRm).catch(() => {});
      api.validate().then(setVd).catch(() => {});
    };
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  const action = (decision as any)?.primary_action || (decision as any)?.action || "—";
  const safe = safeMode?.active;
  const ks = killSwitch?.active;

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <div className="panel-title">AI Command Center</div>

      {/* Critical safety row */}
      {(safe || ks) && (
        <div className="panel border-terminal-bear/60 bg-terminal-bear/10 py-2.5 text-sm font-bold text-terminal-bear">
          {safe ? "🛡 SAFE MODE ACTIVE — signals frozen. " : ""}
          {ks ? "⛔ KILL SWITCH ACTIVE — FORCE WAIT." : ""}
        </div>
      )}

      {/* Live status tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Tile label="System Grade" value={hc?.overall_grade ?? "—"} tone={gradeTone(hc?.overall_grade)} href="/health" />
        <Tile label="Health Score" value={hc ? `${hc.overall_score}/100` : "—"} href="/health" />
        <Tile label="Final Action" value={action}
              tone={action === "ENTER" || action === "HOLD" ? "text-terminal-bull" : action.includes("EXIT") ? "text-terminal-bear" : "text-terminal-warn"} href="/strategist" />
        <Tile label="Spot" value={spot?.ltp ? spot.ltp.toLocaleString("en-IN") : "—"} />
        <Tile label="Broker" value={status?.connected ? "CONNECTED" : "OFFLINE"}
              tone={status?.connected ? "text-terminal-bull" : "text-terminal-bear"} href="/settings" />
        <Tile label="Persistence" value={pp?.database ?? "—"}
              tone={pp?.persistence_status === "ACTIVE" ? "text-terminal-bull" : "text-terminal-warn"} href="/health" />
        <Tile label="Roadmap" value={rm ? `${rm.completion_pct}%` : "—"} href="/evolution" />
        <Tile label="Validation" value={vd ? `${vd.pass}✓ ${vd.warning}⚠ ${vd.fail}✗` : "—"} href="/research" />
      </div>

      {/* Execution Lock / safe mode status (when nominal) — display label only
          (owner, 2026-07-23, item #3); internal `killSwitch` state/identifier
          is unchanged, this is a UI rename. */}
      <div className="grid grid-cols-2 gap-3">
        <Tile label="Execution Lock" value={killSwitch?.level ?? (ks ? "ACTIVE" : "SAFE")}
              tone={ks ? "text-terminal-bear" : "text-terminal-bull"} />
        <Tile label="Safe Mode" value={safe ? "ACTIVE" : "NOMINAL"}
              tone={safe ? "text-terminal-bear" : "text-terminal-bull"} />
      </div>

      {/* Launchers */}
      <section className="panel">
        <div className="panel-title">All Modules</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
          {LAUNCHERS.map(([label, href]) => (
            <Link key={href} href={href}
              className="text-center text-xs px-3 py-3 rounded-lg border border-terminal-border text-terminal-muted hover:border-terminal-accent hover:text-white transition-colors">
              {label}
            </Link>
          ))}
        </div>
      </section>

      <p className="text-[10px] text-terminal-muted text-center">
        Unified cockpit — live status aggregated from existing engines. Probabilities, never certainty.
      </p>
    </div>
  );
}
