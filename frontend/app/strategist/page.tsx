"use client";
// PHASE 25 — AI CHIEF STRATEGIST.
// One structured decision card + the permanent questions answered proactively,
// all derived from the platform's existing engine state. Probabilities, never
// certainty. Decision-support only — never places orders.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const fmt = (n?: number | null) =>
  n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: 2 });

const viewTone = (v?: string) =>
  v === "BULLISH" ? "text-terminal-bull" : v === "BEARISH" ? "text-terminal-bear" : "text-terminal-muted";
const riskTone = (r?: string) =>
  r === "SAFE" ? "text-terminal-bull" : r === "DANGER" ? "text-terminal-bear" : "text-terminal-warn";
const actionTone = (a?: string) =>
  a === "ENTER" || a === "HOLD" || a === "TRAIL" ? "text-terminal-bull"
  : a === "EXIT" || a === "FULL EXIT" ? "text-terminal-bear" : "text-terminal-warn";

function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${tone ?? ""}`}>{value}</div>
    </div>
  );
}

export default function StrategistPage() {
  const [s, setS] = useState<any>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const load = () => api.strategist().then(setS).catch((e) => setErr(String(e?.message || e)));
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  if (err) return <div className="panel text-terminal-bear text-sm max-w-3xl mx-auto">Strategist unavailable ({err})</div>;
  if (!s) return <div className="panel text-terminal-muted text-sm max-w-3xl mx-auto">Loading Chief Strategist…</div>;
  if (!s.ready) {
    // RC1.16.4 — honest AI STATUS block instead of a dead-end one-liner:
    // why there is no analysis, what the first cycle will do, and when.
    const st = s.ai_status || {};
    return (
      <div className="panel max-w-3xl mx-auto space-y-3">
        <div className="panel-title">AI STATUS</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
          <div><div className="stat-label">Broker</div>
            <div className={st.broker === "CONNECTED" ? "text-terminal-bull" : "text-terminal-warn"}>{st.broker ?? "—"}</div></div>
          <div><div className="stat-label">Market</div>
            <div className={st.market === "OPEN" ? "text-terminal-bull" : "text-terminal-warn"}>{st.market ?? "—"}{st.ist_time ? ` · ${st.ist_time} IST` : ""}</div></div>
          <div><div className="stat-label">Data</div><div>{st.data_quality ?? "—"}</div></div>
          <div><div className="stat-label">AI Cycle</div><div>{st.ai_cycle ?? "—"}</div></div>
        </div>
        <div className="text-sm">{s.reason}</div>
        {s.next_action && (
          <div className="text-sm"><span className="text-terminal-muted">Next: </span>{s.next_action}</div>
        )}
        {Array.isArray(s.first_cycle_will) && s.first_cycle_will.length > 0 && (
          <div>
            <div className="stat-label">First AI cycle will</div>
            <ul className="text-xs text-terminal-muted mt-1 space-y-0.5">
              {s.first_cycle_will.map((step: string, i: number) => <li key={i}>• {step}</li>)}
            </ul>
          </div>
        )}
        {s.estimated && (
          <div className="text-xs text-terminal-muted">{s.estimated}</div>
        )}
        {s.discipline && (
          <div className="text-xs text-terminal-accent">{s.discipline}</div>
        )}
      </div>
    );
  }

  const bt = s.best_trade || {};
  const pe = s.premium_expansion || {};
  const iv = s.institutional_view || {};
  const dna = s.market_dna || {};

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      {/* Kill switch banner */}
      {s.kill_switch?.active && (
        <div className="panel border-terminal-bear/60 bg-terminal-bear/10 py-2.5">
          <div className="text-sm font-bold text-terminal-bear tracking-wider">KILL SWITCH ACTIVE — FORCE WAIT</div>
          <div className="text-xs text-gray-200 mt-1">{(s.kill_switch.reasons || []).join("; ")}</div>
        </div>
      )}

      {/* Headline card */}
      <section className="panel">
        <div className="panel-title">AI Chief Strategist</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Stat label="Market View" value={s.market_view} tone={viewTone(s.market_view)} />
          <Stat label="Confidence" value={`${s.confidence ?? 0}%`} />
          <Stat label="Risk View" value={s.risk_view} tone={riskTone(s.risk_view)} />
          <Stat label="Final Action" value={s.final_action} tone={actionTone(s.final_action)} />
        </div>
        {s.reason && <div className="text-xs text-terminal-muted mt-3">{s.reason}</div>}
      </section>

      <div className="grid sm:grid-cols-2 gap-4">
        {/* Best trade */}
        <section className="panel">
          <div className="panel-title">Best Trade</div>
          {bt.is_trade ? (
            <div className="grid grid-cols-2 gap-3">
              <Stat label="Strike" value={bt.strike ? `${bt.strike} ${bt.type ?? ""}` : "—"} />
              <Stat label="Premium" value={fmt(bt.premium)} />
              <Stat label="Entry" value={fmt(bt.entry)} />
              <Stat label="Stop" value={fmt(bt.stop)} tone="text-terminal-bear" />
              <div className="col-span-2">
                <div className="stat-label">Targets</div>
                <div className="stat-value text-terminal-bull">
                  {(bt.targets || []).map((t: number) => fmt(t)).join(" / ")}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-sm text-terminal-warn">No high-probability trade right now — WAIT.</div>
          )}
        </section>

        {/* Premium expansion + Market DNA */}
        <section className="panel space-y-3">
          <div>
            <div className="panel-title">Premium Expansion</div>
            <div className="grid grid-cols-3 gap-3">
              <Stat label="Class" value={pe.class ?? "—"} />
              <Stat label="Exp. Move" value={pe.expected_move != null ? `${fmt(pe.expected_move)} pts` : "—"} />
              <Stat label="Runner" value={pe.runner_probability != null ? `${pe.runner_probability}%` : "—"} />
            </div>
          </div>
          <div className="pt-2 border-t border-terminal-border/40">
            <div className="panel-title">Market DNA</div>
            <div className="grid grid-cols-3 gap-3">
              <Stat label="Match" value={`${dna.match_pct ?? 0}%`} />
              <Stat label="Hist. Win" value={dna.historical_win_rate != null ? `${dna.historical_win_rate}%` : "—"} />
              <Stat label="Samples" value={dna.matches ?? 0} />
            </div>
            <div className="text-[10px] text-terminal-muted mt-1">{dna.note}</div>
          </div>
        </section>
      </div>

      {/* Probability ladder */}
      {s.probability_ladder?.ready && (
        <section className="panel">
          <div className="panel-title">Probability Ladder — touch odds (not certainty)</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {(s.probability_ladder.rungs || []).map((r: any) => (
              <Stat key={r.level} label={`${r.level} @ ${r.price}`} value={`${r.probability}%`}
                    tone={r.band === "VERY HIGH" || r.band === "HIGH" ? "text-terminal-bull" : r.band === "MEDIUM" ? "text-terminal-warn" : "text-terminal-bear"} />
            ))}
            {s.probability_ladder.stop_loss && (
              <Stat label={`SL @ ${s.probability_ladder.stop_loss.price}`}
                    value={`${s.probability_ladder.stop_loss.probability}%`} tone="text-terminal-bear" />
            )}
          </div>
        </section>
      )}

      {/* Entry Zone + Premium Forecast (Phase 27 / 26) */}
      {(s.entry_zone?.ready || s.premium_forecast?.ready) && (
        <div className="grid sm:grid-cols-2 gap-4">
          {s.entry_zone?.ready && (
            <section className="panel">
              <div className="panel-title">Entry Zone</div>
              <div className={`text-lg font-bold ${s.entry_zone.zone === "BEST ENTRY" || s.entry_zone.zone === "GOOD ENTRY" ? "text-terminal-bull" : s.entry_zone.zone === "LATE ENTRY" ? "text-terminal-warn" : "text-terminal-bear"}`}>
                {s.entry_zone.zone} <span className="text-xs text-terminal-muted">({s.entry_zone.score}/100)</span>
              </div>
              <div className="text-xs text-gray-300 mt-1">{s.entry_zone.reason}</div>
            </section>
          )}
          {s.premium_forecast?.ready && (
            <section className="panel">
              <div className="panel-title">Premium Forecast — {s.premium_forecast.classification}</div>
              <div className="grid grid-cols-4 gap-2 text-center">
                {Object.entries(s.premium_forecast.forecasts).map(([h, v]: [string, any]) => (
                  <Stat key={h} label={h} value={`₹${v.premium}`}
                        tone={v.change_pct >= 0 ? "text-terminal-bull" : "text-terminal-bear"} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {/* Institutional view */}
      <section className="panel">
        <div className="panel-title">Institutional View</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Stat label="Dominance" value={iv.dominance ?? "—"} />
          <Stat label="Trapped" value={iv.trapped ?? "—"} tone="text-terminal-warn" />
          <Stat label="Buyer Strength" value={iv.buyer_strength ?? "—"} tone="text-terminal-bull" />
          <Stat label="Seller Strength" value={iv.seller_strength ?? "—"} tone="text-terminal-bear" />
        </div>
        {!!iv.likely?.length && (
          <div className="text-xs text-gray-300 mt-2">Likely: {iv.likely.join("  ·  ")}</div>
        )}
      </section>

      {/* Options Professor (Phase 30) */}
      {s.options_professor?.ready && (
        <section className="panel">
          <div className="panel-title">Options Professor — {s.options_professor.side}</div>
          <div className="space-y-1.5 text-sm">
            {Object.entries(s.options_professor.explanations || {}).map(([k, v]: [string, any]) => (
              <div key={k} className="border-t border-terminal-border/40 pt-1.5 first:border-0 first:pt-0">
                <span className="text-[11px] text-terminal-accent capitalize">{k.replace(/_/g, " ")}</span>
                <div className="text-xs text-gray-200">{v}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Permanent questions — answered proactively */}
      <section className="panel">
        <div className="panel-title">Answered For You</div>
        <div className="space-y-2.5">
          {(s.questions || []).map((a: any, i: number) => (
            <div key={i} className="border-t border-terminal-border/40 pt-2 first:border-0 first:pt-0">
              <div className="text-[11px] text-terminal-accent">{a.q}</div>
              <div className="text-sm">{a.answer}</div>
              {!!a.points?.length && (
                <ul className="mt-1 space-y-0.5 text-[11px] text-terminal-muted">
                  {a.points.map((p: string, j: number) => <li key={j}>▸ {p}</li>)}
                </ul>
              )}
            </div>
          ))}
        </div>
      </section>

      <p className="text-[10px] text-terminal-muted text-center">{s.disclaimer}</p>
    </div>
  );
}
