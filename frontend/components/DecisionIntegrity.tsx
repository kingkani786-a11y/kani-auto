"use client";
// DECISION INTEGRITY STRIP (owner, 2026-08-11) — the one thing the dashboard
// could not answer at a glance: "is the SOFTWARE working?" versus "is a TRADE
// allowed?". Those are different questions with different answers, and a
// WAIT/BLOCKED verdict answers only the second one. Read the owner's framing
// literally: a trader opening this tomorrow must not conclude "WAIT appeared,
// therefore the software is broken".
//
// The load-bearing idea: a stage that RAN and returned BLOCKED is 🟢 for
// software integrity and 🔴 for execution. Both facts are true at once, and
// this panel is the only place that says so side by side.
//
// REARRANGE, NOT NEW INFORMATION (UI rule, 2026-08-03: "New Number needs
// evidence, New Visualization doesn't"). Every value below is already
// published and already rendered elsewhere — System Verify, WHY NO TRADE,
// Execution Control Center, Calibration Watch, Shadow Calibration. Nothing
// here computes a score, a probability, or a threshold, and nothing here can
// gate, veto, or influence a trade. Deleting this file changes no decision.
//
// Rule 11 ("One Hero -> One Decision") holds: this states no verdict of its
// own. The execution line restates the Hero's existing decision verbatim.

import { useEffect, useState } from "react";
import { useMarket } from "@/lib/store";
import { api } from "@/lib/api";

type Health = "ok" | "blocked" | "idle" | "fault";

const DOT: Record<Health, string> = {
  ok: "🟢",
  blocked: "🔴",
  idle: "⚪",
  fault: "🔴",
};

function Row({ label, health, detail }: { label: string; health: Health; detail: string }) {
  return (
    <div className="flex items-baseline gap-2 text-xs">
      <span className="shrink-0">{DOT[health]}</span>
      <span className="text-white shrink-0">{label}</span>
      <span className="text-terminal-muted truncate">— {detail}</span>
    </div>
  );
}

export function DecisionIntegrity() {
  const { status, signal, decision, killSwitch, safeMode, wsOk } = useMarket();
  const [cal, setCal] = useState<any>(null);
  const [shadow, setShadow] = useState<any>(null);

  useEffect(() => {
    const load = () => {
      api.calibrationWatch().then(setCal).catch(() => {});
      api.shadowCalibration().then(setShadow).catch(() => {});
    };
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  const marketOpen = !!status?.market_open;
  const connected = !!status?.connected;

  // ── DATA ────────────────────────────────────────────────────────────────
  // A closed market with no ticks is idle, not a fault — the same doctrine
  // System Verify already states ("paused/off on a closed market is expected").
  const dq = status?.data_quality || "UNKNOWN";
  const dataHealth: Health = !connected
    ? "fault"
    : !marketOpen
    ? "idle"
    : dq === "GOOD"
    ? "ok"
    : "blocked";
  const dataDetail = !connected
    ? "broker disconnected — reconnect in Settings"
    : !marketOpen
    ? "market closed — feeds resume at open"
    : `feed quality ${dq}`;

  // ── ANALYSIS ────────────────────────────────────────────────────────────
  const techOk = !!(signal as any)?.tech;
  const engineOk = !!decision?.action;

  // ── GATE ────────────────────────────────────────────────────────────────
  // "Evaluated" is the question here, NOT "passed". A gate that ran and said
  // BLOCKED is working exactly as designed — that is the whole point of this
  // panel, so it must never render as a fault.
  const ksEvaluated = killSwitch != null;
  const ksActive = !!killSwitch?.active;
  const smEvaluated = safeMode != null;
  const smActive = !!safeMode?.active;
  const eg = (decision as any)?.execution_gate;
  const gateEvaluated = !!eg;
  const calScore = cal?.calibration_score ?? cal?.calibration ?? null;
  const calOk = calScore != null;

  // ── EXECUTION ───────────────────────────────────────────────────────────
  // Restated from the Hero's already-published verdict; never recomputed.
  const finalDecision = eg?.final_decision || decision?.action || "—";
  const executionAllowed =
    typeof finalDecision === "string" && finalDecision.startsWith("BUY");

  // Software integrity = did every stage that SHOULD run actually run.
  // Deliberately excludes whether the answer was BUY or WAIT.
  const softwareChecks = [connected || !marketOpen, engineOk || !marketOpen,
                           ksEvaluated, gateEvaluated || !marketOpen];
  const softwareOk = softwareChecks.every(Boolean);
  // Degraded feed is NOT a code fault — the pipeline detected it and acted,
  // which is the software working. But claiming a flat "HEALTHY" next to a
  // red DATA stage is its own contradiction, and this panel exists to kill
  // contradictions, not add one. Found while verifying against live state
  // (feed POOR + every stage green), so it is a real case, not hypothetical.
  const dataDegraded = dataHealth === "blocked" || dataHealth === "fault";
  const softwareVerdict = !softwareOk
    ? { dot: "🔴", text: "SYSTEM FAULT", tone: "text-terminal-bear",
        note: "a stage did not produce output — see rows below" }
    : dataDegraded
    ? { dot: "🟡", text: "HEALTHY · DATA DEGRADED", tone: "text-terminal-warn",
        note: "every stage ran; input feed is degraded, not the code" }
    : { dot: "🟢", text: "SYSTEM HEALTHY", tone: "text-terminal-bull",
        note: "every stage ran and produced output" };

  const blockers: string[] = [];
  if (ksActive) blockers.push(...(killSwitch?.reasons || ["Execution Lock"]));
  if (smActive) blockers.push(...(safeMode?.triggers || ["Safe Mode"]));

  // Key is `sample_blocked`, NOT `blocked_samples` — verified against
  // shadow_calibration.py's actual return. A wrong key here renders a silent
  // "no samples yet" that reads as a broken collector rather than a typo.
  const shadowN = shadow?.sample_blocked ?? null;

  return (
    <section className="panel space-y-2">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-white">🧭 Decision Integrity</h2>
        <span className="text-[10px] px-1.5 py-0.5 rounded border border-terminal-border text-terminal-muted">
          VERIFICATION ONLY
        </span>
      </div>

      {/* The two questions, answered separately — the entire reason this panel
          exists. Software health and trade permission are independent facts. */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <div className="rounded border border-terminal-border/60 p-2">
          <div className="text-[10px] stat-label">IS THE SOFTWARE WORKING?</div>
          <div className={`text-base font-bold ${softwareVerdict.tone}`}>
            {softwareVerdict.dot} {softwareVerdict.text}
          </div>
          <div className="text-[11px] text-terminal-muted">{softwareVerdict.note}</div>
        </div>
        <div className="rounded border border-terminal-border/60 p-2">
          <div className="text-[10px] stat-label">IS A TRADE ALLOWED?</div>
          <div className={`text-base font-bold ${executionAllowed ? "text-terminal-bull" : "text-terminal-warn"}`}>
            {executionAllowed ? "🟢 PERMITTED" : "🔴 NO EXECUTION"}
          </div>
          <div className="text-[11px] text-terminal-muted truncate">
            {executionAllowed ? String(finalDecision) : blockers[0] || String(finalDecision)}
          </div>
        </div>
      </div>

      {/* Pipeline — where in the chain the answer was decided. */}
      <div className="flex flex-wrap items-center gap-1 text-[11px] font-mono">
        {[
          ["DATA", dataHealth],
          ["ANALYSIS", (techOk && engineOk ? "ok" : marketOpen ? "fault" : "idle") as Health],
          ["GATE", (ksEvaluated && gateEvaluated ? "ok" : marketOpen ? "fault" : "idle") as Health],
          ["DECISION", (decision?.action ? "ok" : marketOpen ? "fault" : "idle") as Health],
          ["EXECUTION", (executionAllowed ? "ok" : "blocked") as Health],
        ].map(([name, h], i, arr) => (
          <span key={name as string} className="flex items-center gap-1">
            <span>{DOT[h as Health]}</span>
            <span className="text-white">{name}</span>
            {i < arr.length - 1 && <span className="text-terminal-muted mx-0.5">→</span>}
          </span>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 pt-1 border-t border-terminal-border/40">
        <Row label="Live data flowing" health={dataHealth} detail={dataDetail} />
        <Row
          label="Technicals updated"
          health={techOk ? "ok" : marketOpen ? "fault" : "idle"}
          detail={techOk ? "indicators published" : marketOpen ? "no tech packet" : "idle — market closed"}
        />
        <Row
          label="Decision engine running"
          health={engineOk ? "ok" : marketOpen ? "fault" : "idle"}
          detail={engineOk ? `published "${decision?.action}"` : marketOpen ? "no decision published" : "idle — market closed"}
        />
        <Row
          label="Calibration calculated"
          health={calOk ? "ok" : "idle"}
          detail={calOk ? `score ${calScore} (measured, not assumed)` : "building — insufficient settled samples"}
        />
        <Row
          label="Kill Switch evaluated"
          health={ksEvaluated ? "ok" : marketOpen ? "fault" : "idle"}
          detail={
            !ksEvaluated
              ? "not evaluated"
              : ksActive
              ? `ran → ACTIVE (${killSwitch?.reasons?.[0] || "blocking"})`
              : "ran → clear"
          }
        />
        <Row
          label="Safe Mode evaluated"
          health={smEvaluated ? "ok" : marketOpen ? "fault" : "idle"}
          detail={
            !smEvaluated
              ? "not evaluated"
              : smActive
              ? `ran → ACTIVE (${safeMode?.triggers?.[0] || "infra"})`
              : "ran → clear"
          }
        />
        <Row
          label="Final gate evaluated"
          health={gateEvaluated ? "ok" : marketOpen ? "fault" : "idle"}
          detail={gateEvaluated ? `ran → ${finalDecision}` : marketOpen ? "gate not published" : "idle — market closed"}
        />
        <Row
          label="Execution allowed"
          health={executionAllowed ? "ok" : "blocked"}
          detail={executionAllowed ? "gate open" : blockers.length ? blockers.join(" · ") : "gate closed"}
        />
        <Row
          label="Shadow research collecting"
          health={shadowN ? "ok" : "idle"}
          detail={shadowN ? `${shadowN} blocked samples logged` : "no samples yet"}
        />
        <Row
          label="Live connection (WS)"
          health={wsOk ? "ok" : "fault"}
          detail={wsOk ? "streaming" : "websocket down — values may be stale"}
        />
      </div>

      <div className="text-[10px] text-terminal-muted leading-relaxed border-t border-terminal-border/40 pt-2">
        <b>A blocked gate is not a broken system.</b> Rows above answer “did this
        stage run?”, not “did it say yes”. Kill Switch or Safe Mode showing ACTIVE
        means they evaluated correctly and chose to protect capital — that is 🟢
        integrity and 🔴 execution at the same time. Restates existing panels only:
        no new score, no threshold, no influence on any decision.
      </div>
    </section>
  );
}
