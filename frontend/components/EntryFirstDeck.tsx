"use client";
// ENTRY-FIRST DECK — Sections 1–6. Pure presentation over existing store data
// (main signal + strike + decision + lifecycle + warning). No logic changes.

import { useMarket } from "@/lib/store";

const fmt = (n?: number | null, d = 2) =>
  n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: d });

const ACTION_TONE: Record<string, string> = {
  "BUY CALL": "text-terminal-bull", "BUY CE": "text-terminal-bull",
  "BUY PUT": "text-terminal-bear", "BUY PE": "text-terminal-bear",
  "BUY FUTURES": "text-terminal-bull", "SELL FUTURES": "text-terminal-bear",
  WAIT: "text-terminal-warn", "NO TRADE": "text-terminal-muted",
};

function Chip({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div className="bg-terminal-bg rounded-lg px-3 py-2 border border-terminal-border/50">
      <div className="text-[9px] uppercase tracking-wider text-terminal-muted">{label}</div>
      <div className={`font-mono text-sm font-bold ${tone ?? ""}`}>{value}</div>
    </div>
  );
}

const qualTone = (g?: string) =>
  g === "A" || g === "A+" ? "text-terminal-bull" : g === "B" ? "text-terminal-accent" :
  g === "C" ? "text-terminal-warn" : "text-terminal-muted";

// Regime Intelligence — static advice map (display only, no computation)
const REGIME_PLAY: Record<string, { best: string; avoid: string; expect: string }> = {
  TRENDING: { best: "Trend pullback entries", avoid: "Counter-trend fades", expect: "Directional follow-through" },
  HIGH_MOMENTUM: { best: "Momentum / breakout", avoid: "Mean-reversion", expect: "Strong continuation" },
  RANGE_BOUND: { best: "Fade extremes", avoid: "Breakout chasing", expect: "Rotation between S/R" },
  VOLATILE: { best: "Wait / reduce size", avoid: "Aggressive scalping", expect: "Wide two-sided swings" },
  LOW_MOMENTUM: { best: "Wait", avoid: "Forcing trades", expect: "Choppy, low follow-through" },
  EXPIRY_PINNING: { best: "Wait", avoid: "Aggressive scalping", expect: "Price magnetism near gamma wall" },
};

// Strike quality grade from existing StrikeReco fields (no new compute)
function strikeGrade(s: any): { grade: string; slippage: string; spreadScore: number } | null {
  if (!s) return null;
  const sel = s.selection_score ?? 0;
  const spreadScore = Math.max(0, Math.min(100, Math.round(100 - (s.spread_pct ?? 2) * 12)));
  const grade = sel >= 85 ? "A+" : sel >= 75 ? "A" : sel >= 62 ? "B" : sel >= 50 ? "C" : "D";
  const slippage = (s.spread_pct ?? 2) < 1 ? "Low" : (s.spread_pct ?? 2) < 2.5 ? "Medium" : "High";
  return { grade, slippage, spreadScore };
}

const MANDATORY = ["trend", "structure", "oi", "mtf"];
const LAYER_NAME: Record<string, string> = { trend: "Trend", structure: "Structure", oi: "OI", mtf: "MTF" };

// compact inline chip for the context / risk strips
function Tag({ k, v, tone }: { k: string; v: React.ReactNode; tone?: string }) {
  return (
    <span className="inline-flex items-baseline gap-1 whitespace-nowrap">
      <span className="text-[9px] uppercase tracking-wider text-terminal-muted">{k}</span>
      <span className={`font-mono text-xs font-semibold ${tone ?? ""}`}>{v}</span>
    </span>
  );
}

export function EntryFirstDeck() {
  const { signal, decision, strike, layers, lifecycle, warning, spot, status } = useMarket();
  const L = layers as any;
  const isIndex = status?.market_type === "INDEX";
  const num = (n?: number | null, d = 0) =>
    n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: d });
  const biasTone = (b?: string) =>
    b === "BULLISH" || b === "FAVORABLE" ? "text-terminal-bull" :
    b === "BEARISH" || b === "RISKY" ? "text-terminal-bear" : "text-terminal-muted";
  const action = decision?.action ?? signal?.signal ?? "WAIT";
  const isTrade = !!decision?.is_trade && !!strike;
  const ep = L?.entry_probability?.score;
  const execScore = strike?.selection_score ?? null;
  const conf = signal?.dynamic_confidence ?? signal?.confidence;
  const riskPts = strike ? Math.round(((strike.premium_entry ?? 0) - (strike.premium_stop_loss ?? 0)) * 100) / 100 : null;
  const spreadScore = strike ? Math.max(0, Math.min(100, Math.round(100 - (strike.spread_pct ?? 2) * 12))) : null;
  const trig = lifecycle?.trigger_price;
  const trigDist = trig && spot?.ltp ? Math.abs(spot.ltp - trig) : null;
  const lastExit = (lifecycle?.history || []).filter((h) => h.to === "EXIT").slice(-1)[0];

  // Entry Readiness 2.0 — which mandatory layers aren't confirming + points gap
  const dom = (signal?.bull_score ?? 0) >= (signal?.bear_score ?? 0) ? "BULL" : "BEAR";
  const favKey = dom === "BULL" ? "score_bull" : "score_bear";
  const excludedLayers = new Set<string>((L?._instrument_mode?.excluded || []) as string[]);
  const missing = MANDATORY
    .filter((k) => !excludedLayers.has(k))   // option-only layers N/A on chain-less instruments
    .map((k) => ({ k, fav: Number(L?.[k]?.[favKey] ?? 50) }))
    .filter((m) => m.fav < 55)
    .map((m) => ({ name: LAYER_NAME[m.k], gap: Math.round(55 - m.fav) }));
  const pointsNeeded = missing.reduce((a, m) => a + m.gap, 0);
  const eta = lifecycle?.state === "TRIGGERED" || lifecycle?.state === "ENTRY" ? "now"
    : lifecycle?.state === "ARMED" ? "imminent" : lifecycle?.state === "WATCH" ? "near" : "—";
  const sg = strikeGrade(strike);
  const regimePlay = REGIME_PLAY[L?.regime?.regime as string];
  const session = L?.session;
  const intel = L?.intelligence;
  const primary = decision?.primary_action ?? "WAIT";
  const PRIMARY_TONE: Record<string, string> = {
    ENTER: "text-terminal-bull border-terminal-bull/60 bg-terminal-bull/15",
    HOLD: "text-terminal-accent border-terminal-accent/50 bg-terminal-accent/10",
    TRAIL: "text-terminal-accent border-terminal-accent/50 bg-terminal-accent/10",
    EXIT: "text-terminal-bear border-terminal-bear/60 bg-terminal-bear/15",
    WAIT: "text-terminal-warn border-terminal-warn/50 bg-terminal-warn/10",
  };
  const clarityTone = (lab?: string) =>
    lab === "VERY CLEAR" || lab === "CLEAR" ? "text-terminal-bull" :
    lab === "MODERATE" ? "text-terminal-warn" : "text-terminal-bear";

  return (
    <div className="space-y-3">
      {/* FINAL DECISION — single primary action + the 6 answers + intelligence */}
      {intel && (
        <section className="panel">
          <div className="flex items-center gap-3 mb-3">
            <div className={`px-4 py-2 rounded-lg border text-2xl font-black font-mono ${PRIMARY_TONE[primary] ?? PRIMARY_TONE.WAIT}`}>
              {primary}
            </div>
            <div className="text-sm">
              <div className="font-semibold">{intel.summary?.whats_happening}</div>
              <div className="text-terminal-muted text-xs">{intel.summary?.move_type}</div>
            </div>
            <div className="ml-auto text-right">
              <div className="stat-label">Decision Clarity</div>
              <div className={`font-bold ${clarityTone(intel.decision_clarity?.label)}`}>
                {intel.decision_clarity?.label} ({intel.decision_clarity?.score})
              </div>
            </div>
          </div>
          {/* intelligence chips — Animal Clarity: current animal kept SEPARATE
              from expansion potential (they answer different questions) */}
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs">
            <Tag k="Current Animal" v={`${intel.market_animal?.animal} ${intel.market_animal?.confidence}%`} />
            <Tag k="Expansion Potential" v={intel.expansion?.class}
              tone={intel.expansion?.runner_probability >= 60 ? "text-terminal-bull" : "text-terminal-muted"} />
            <Tag k="Runner Prob" v={`${intel.expansion?.runner_probability}%`}
              tone={intel.expansion?.runner_probability >= 60 ? "text-terminal-bull" : "text-terminal-muted"} />
            <Tag k="Lifespan" v={intel.market_animal?.lifespan} />
            <Tag k="Data" v={intel.data_confidence}
              tone={intel.data_confidence === "High" ? "text-terminal-bull" : intel.data_confidence === "Low" ? "text-terminal-bear" : "text-terminal-warn"} />
            {(intel.failure_patterns || []).length > 0 && (
              <span className="text-[11px] text-terminal-bear">⚠ {intel.failure_patterns.join(" · ")}</span>
            )}
          </div>
        </section>
      )}

      {/* SECTION 1 — TOP EXECUTION CARD */}
      <section className="panel">
        <div className="flex flex-wrap items-center gap-3 mb-3">
          <div className={`text-3xl font-black font-mono tracking-tight ${ACTION_TONE[action] ?? "text-terminal-muted"}`}>
            {action}
          </div>
          {signal?.grade && signal.grade !== "NO TRADE" && (
            <span className={`px-2.5 py-1 rounded-lg text-sm font-bold ${qualTone(signal.grade)} border border-current/30`}>
              {signal.grade} GRADE
            </span>
          )}
          <span className="ml-auto text-xs text-terminal-muted">{decision?.reason ?? ""}</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          <Chip label="Confidence" value={conf != null ? `${Math.round(conf)}%` : "—"} />
          <Chip label="Signal Score" value={signal?.confidence != null ? `${Math.round(signal.confidence)}/100` : "—"} />
          <Chip label="Execution" value={execScore != null ? `${Math.round(execScore)}/100` : "—"} />
          <Chip label="Trade Quality" value={signal?.grade ?? "—"} tone={qualTone(signal?.grade)} />
          <Chip label="Entry Probability" value={ep != null ? `${Math.round(ep)}/100` : "—"} />
        </div>
      </section>

      {/* MARKET CONTEXT strip (Row 2/3) — VIX · bias · regime · strength ·
          PCR · Max Pain · Gamma Wall. All from streamed layers (no new calls). */}
      {L?.global_context && (
        <section className="panel py-2.5 flex flex-wrap items-center gap-x-5 gap-y-2">
          <span className="text-[10px] uppercase tracking-widest text-terminal-muted">Context</span>
          <Tag k="VIX" v={L?.vix_correlation?.vix ?? "—"} />
          <Tag k="Bias" v={L.global_context.bias ?? "—"} tone={biasTone(L.global_context.bias)} />
          <Tag k="Condition" v={L.global_context.condition ?? "—"} tone={biasTone(L.global_context.condition)} />
          <Tag k="Regime" v={String(L?.regime?.regime ?? "—").replace(/_/g, " ")} />
          <Tag k="Strength" v={`${num(L?.market_strength?.score)} ${String(L?.market_strength?.label ?? "").replace(/_/g, " ")}`} />
          {isIndex && <Tag k="PCR" v={num(L?.oi?.pcr, 2)} tone={(L?.oi?.pcr ?? 1) > 1 ? "text-terminal-bull" : "text-terminal-bear"} />}
          {isIndex && <Tag k="Max Pain" v={num(L?.oi?.max_pain)} />}
          {isIndex && L?.expiry?.gamma_wall && <Tag k="Gamma Wall" v={num(L.expiry.gamma_wall)} />}
          {session?.label && <Tag k="Session" v={session.label} tone={session.favorable_for_entry ? "text-terminal-bull" : "text-terminal-warn"} />}
        </section>
      )}

      {/* REGIME INTELLIGENCE — what works now (static advice over live regime) */}
      {regimePlay && (
        <section className="panel py-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-[11px]">
          <span className="text-[10px] uppercase tracking-widest text-terminal-muted">Regime Play</span>
          <Tag k="Best" v={regimePlay.best} tone="text-terminal-bull" />
          <Tag k="Avoid" v={regimePlay.avoid} tone="text-terminal-bear" />
          <Tag k="Expect" v={regimePlay.expect} />
        </section>
      )}

      <div className="grid lg:grid-cols-3 gap-3">
        {/* SECTION 2 — STRIKE RECOMMENDATION */}
        <section className="panel">
          <div className="panel-title">Recommended Strike</div>
          {!isTrade ? (
            <p className="text-sm text-terminal-muted">No active trade — strike appears on a BUY signal.</p>
          ) : (
            <>
              <div className="flex items-baseline gap-2 mb-2">
                <span className={`text-xl font-bold font-mono ${strike!.type === "CE" ? "text-terminal-bull" : "text-terminal-bear"}`}>
                  {fmt(strike!.strike, 0)} {strike!.type}
                </span>
                {sg && <span className={`ml-auto px-2 py-0.5 rounded text-xs font-bold border border-current/30 ${qualTone(sg.grade)}`}>Grade {sg.grade}</span>}
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-[11px]">
                <Kv k="Premium" v={fmt(strike!.premium_entry)} />
                <Kv k="Execution" v={`${fmt(strike!.selection_score, 0)}/100`} />
                <Kv k="Spread Score" v={`${sg?.spreadScore ?? spreadScore}/100`} />
                <Kv k="Slippage" v={sg?.slippage ?? "—"} tone={sg?.slippage === "Low" ? "text-terminal-bull" : sg?.slippage === "High" ? "text-terminal-bear" : ""} />
                <Kv k="Delta" v={fmt(strike!.delta, 3)} />
                <Kv k="P(ITM)" v={`${fmt((strike as any).prob_itm_pct, 0)}%`} />
              </div>
            </>
          )}
        </section>

        {/* SECTION 3 — ENTRY PLAN */}
        <section className="panel">
          <div className="panel-title">Entry Plan</div>
          {!isTrade ? (
            <p className="text-sm text-terminal-muted">Waiting for a qualifying entry.</p>
          ) : (
            <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
              <Kv k="Entry" v={fmt(strike!.premium_entry)} tone="text-terminal-accent" big />
              <Kv k="Stop Loss" v={fmt(strike!.premium_stop_loss)} tone="text-terminal-bear" big />
              <Kv k="Risk / lot" v={riskPts != null ? `${fmt(riskPts)} pts` : "—"} />
              <Kv k="Hold" v={(layers as any)?.future_path ? "Intraday" : "—"} />
            </div>
          )}
        </section>

        {/* SECTION 4 — TARGET PANEL */}
        <section className="panel">
          <div className="panel-title">Targets</div>
          {!isTrade ? (
            <p className="text-sm text-terminal-muted">Targets set on entry.</p>
          ) : (
            <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
              <Kv k="Target 1" v={fmt(strike!.premium_target1)} tone="text-terminal-bull" />
              <Kv k="Target 2" v={fmt(strike!.premium_target2)} tone="text-terminal-bull" />
              <Kv k="Target 3" v={fmt(strike!.premium_target3)} tone="text-terminal-bull" />
              <Kv k="Reward:Risk" v={signal?.reward_risk ? `1:${signal.reward_risk}` : "—"} />
            </div>
          )}
        </section>
      </div>

      {/* RISK & PROTECTION strip (Row 4) — Capital Protection · No-Trade Zone ·
          Trap Detection · Order Flow · Futures. Decision-critical guardrails,
          all from streamed layers (no new API / compute). */}
      {L?.capital_protection && (
        <section className="panel py-2.5 flex flex-wrap items-center gap-x-5 gap-y-2">
          <span className="text-[10px] uppercase tracking-widest text-terminal-muted">Risk</span>
          <Tag k="Capital" v={`${L.capital_protection.category} ${num(L.capital_protection.capital_risk)}`}
            tone={L.capital_protection.category === "CRITICAL" ? "text-terminal-bear" :
              L.capital_protection.category === "ELEVATED" ? "text-terminal-warn" :
              L.capital_protection.category === "ACCEPTABLE" ? "text-terminal-accent" : "text-terminal-bull"} />
          <Tag k="No-Trade Zone" v={L?.no_trade_zone?.status ?? "—"}
            tone={L?.no_trade_zone?.active ? "text-terminal-bear" : "text-terminal-bull"} />
          <Tag k="Traps" v={L?.traps?.detected ? `${num(L.traps.trap_confidence)}%` : "CLEAR"}
            tone={L?.traps?.detected ? "text-terminal-bear" : "text-terminal-bull"} />
          <Tag k="Order Flow" v={num(L?.order_flow?.score)}
            tone={(L?.order_flow?.score ?? 50) > 55 ? "text-terminal-bull" : (L?.order_flow?.score ?? 50) < 45 ? "text-terminal-bear" : "text-terminal-muted"} />
          {L?.futures?.buildup && L.futures.buildup !== "Neutral" && (
            <Tag k="Futures" v={`${L.futures.buildup} ${num(L.futures.confirmation_score)}%`}
              tone={L.futures.relation === "CONFIRMS" ? "text-terminal-bull" : L.futures.relation === "CONTRADICTS" ? "text-terminal-bear" : "text-terminal-muted"} />
          )}
        </section>
      )}

      <div className="grid lg:grid-cols-2 gap-3">
        {/* SECTION 5 — TRADE STATUS (current vs last closed, never mixed) */}
        <section className="panel">
          <div className="panel-title">Trade Status</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-terminal-bg rounded-lg p-3 border border-terminal-border/50">
              <div className="stat-label mb-1">Current Signal</div>
              <div className="text-base font-bold font-mono text-terminal-accent">{lifecycle?.state ?? "WAITING"}</div>
              {lifecycle?.targets_hit ? (
                <div className="text-[11px] text-terminal-muted mt-1">{lifecycle.targets_hit} target(s) hit</div>
              ) : null}
            </div>
            <div className="bg-terminal-bg rounded-lg p-3 border border-terminal-border/50">
              <div className="stat-label mb-1">Last Closed Trade</div>
              {lastExit ? (
                <>
                  <div className="text-base font-bold font-mono">{(lastExit.note || "closed").toUpperCase().includes("STOP") ? "SL HIT" : "TARGET"}</div>
                  <div className="text-[11px] text-terminal-muted mt-1">{lastExit.note}</div>
                </>
              ) : (
                <div className="text-sm text-terminal-muted">No closed trade yet</div>
              )}
            </div>
          </div>
        </section>

        {/* SECTION 6 — ENTRY READINESS 2.0 (why not ready + what's missing) */}
        <section className="panel">
          <div className="panel-title">Entry Readiness</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <Kv k="Readiness" v={warning?.preparation != null ? `${warning.preparation}%`
              : lifecycle?.state === "ARMED" || lifecycle?.state === "TRIGGERED" ? "High" : "—"} />
            <Kv k="Setup Conf." v={warning?.confidence != null ? `${warning.confidence}%` : "—"} />
            <Kv k="Trigger Dist" v={trigDist != null ? `${fmt(trigDist)} pts` : "—"} />
            <Kv k="ETA" v={eta} />
          </div>
          {/* Signal Aging (Rule 11) — freshness + late-entry risk */}
          {lifecycle?.updated && (() => {
            const ageMin = Math.max(0, (Date.now() / 1000 - lifecycle.updated) / 60);
            const fresh = ageMin < 2 ? "FRESH" : ageMin < 6 ? "RECENT" : "AGING";
            const lateRisk = (isTrade && trigDist != null && trigDist > 0) || ageMin > 8;
            return (
              <div className="mt-2 pt-2 border-t border-terminal-border/50 text-[11px] flex gap-4">
                {/* RC1.16.10 — this measures time since the lifecycle tracker
                    last updated, NOT setup age (that lives on Signal Maturity's
                    AGE). Two different quantities had one label and diverged
                    the moment bias flipped (26m vs 224m on one screen). */}
                <span><span className="text-terminal-muted">Setup updated </span><span className="font-mono">{ageMin < 1 ? "<1m ago" : `${ageMin.toFixed(0)}m ago`} · {fresh}</span></span>
                <span><span className="text-terminal-muted">Late-entry risk </span>
                  <span className={lateRisk ? "text-terminal-warn font-bold" : "text-terminal-bull"}>{lateRisk ? "Elevated" : "Low"}</span></span>
              </div>
            );
          })()}
          {!isTrade && missing.length > 0 && (
            <div className="mt-2 pt-2 border-t border-terminal-border/50 text-[11px]">
              <span className="text-terminal-muted">Missing to arm: </span>
              {missing.map((m, i) => (
                <span key={m.name} className="font-mono text-terminal-warn">
                  {m.name} +{m.gap}{i < missing.length - 1 ? " · " : ""}
                </span>
              ))}
              <span className="text-terminal-muted"> (need ~{pointsNeeded} pts)</span>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function Kv({ k, v, tone, big }: { k: string; v: React.ReactNode; tone?: string; big?: boolean }) {
  return (
    <div>
      <div className="stat-label">{k}</div>
      <div className={`font-mono ${big ? "text-lg font-bold" : "text-sm"} ${tone ?? ""}`}>{v}</div>
    </div>
  );
}
