"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";
import type { SymbolInfo } from "@/lib/types";
import dynamic from "next/dynamic";
import type { Candle, TradeLines } from "@/components/ProChart";
import { SafeBoundary } from "@/components/SafeBoundary";
import { EntryFirstDeck } from "@/components/EntryFirstDeck";
import { ScalpRadarPanel } from "@/components/ScalpRadarPanel";
import { ExitIntelligencePanel } from "@/components/ExitIntelligencePanel";
import { DecisionMatrix } from "@/components/DecisionMatrix";
import { KillSwitchBanner } from "@/components/KillSwitchBanner";
import { SafeModeBanner } from "@/components/SafeModeBanner";
import { MarketStatusBanner } from "@/components/MarketStatusBanner";
import { friendlyMessage } from "@/lib/status";
import { ProbabilityLadder } from "@/components/ProbabilityLadder";
import { DecisionIntelligence } from "@/components/DecisionIntelligence";
import { ExecutionControlCenter } from "@/components/ExecutionControlCenter";
import { ExecutionCard } from "@/components/ExecutionCard";
import { EntryScoreTimeline } from "@/components/EntryScoreTimeline";
import { AlphaPanel } from "@/components/AlphaPanel";
import { AIHealthStrip } from "@/components/AIHealthStrip";
import { AIAnalysisCard } from "@/components/AIAnalysisCard";
import { AITimelineCard } from "@/components/AITimelineCard";
import { PremiumRadar } from "@/components/PremiumRadar";
import { HotNow } from "@/components/HotNow";
import { EarlyWarning } from "@/components/EarlyWarning";
import { AIAttention } from "@/components/AIAttention";
import { AIThinkingPanel } from "@/components/AIThinkingPanel";
import { BuildVersion } from "@/components/BuildVersion";
import { SystemVerify } from "@/components/SystemVerify";
import { AIChangelog } from "@/components/AIChangelog";
import { StrikeQueue } from "@/components/StrikeQueue";
import { PremiumTimeline } from "@/components/PremiumTimeline";
import { DailyReview } from "@/components/DailyReview";
import { MarketPathPanel } from "@/components/MarketPathPanel";
import { FinalDecisionHeader } from "@/components/FinalDecisionHeader";
import { MissedWinners } from "@/components/MissedWinners";
import { MissedMoveProtection } from "@/components/MissedMoveProtection";
import { VoiceAssistant } from "@/components/VoiceAssistant";
import { LiveCandleCommand } from "@/components/LiveCandleCommand";
import { SmartAlertBar } from "@/components/SmartAlertBar";
import { GammaShield } from "@/components/GammaShield";
import { PointCaptureStrip } from "@/components/PointCaptureStrip";
import { ScalpingTool } from "@/components/ScalpingTool";
import { IndexRadar } from "@/components/IndexRadar";
import { OpportunityBoard } from "@/components/OpportunityBoard";
import { TradeManagement } from "@/components/TradeManagement";
import { MarketMemory } from "@/components/MarketMemory";
import { GlobalStrip } from "@/components/GlobalStrip";
import { FeedDiagnostics } from "@/components/FeedDiagnostics";
import { SignalMaturity } from "@/components/SignalMaturity";
import { EntryChecklist } from "@/components/EntryChecklist";
import { ConfidenceEvolution } from "@/components/ConfidenceEvolution";
import { CandleProjection } from "@/components/CandleProjection";
import { EntryZonePremium } from "@/components/EntryZonePremium";

// Lazy-load the heavy chart (lightweight-charts) so the entry-first cards —
// signal, strike, entry, targets, execution, scalp — paint first.
const ProChart = dynamic(
  () => import("@/components/ProChart").then((m) => m.ProChart),
  { ssr: false, loading: () => (
    <div className="h-[380px] sm:h-[480px] flex items-center justify-center text-terminal-muted text-sm">
      <div className="w-7 h-7 border-2 border-terminal-border border-t-terminal-accent rounded-full animate-spin" />
    </div>
  ) }
);

const TIMEFRAMES = ["1s", "1m", "3m", "5m", "15m", "30m", "1H"];

const fmt = (n?: number | null, d = 2) =>
  n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: d });

export default function Dashboard() {
  const { status, spot, decision, lastError, layers, strike } = useMarket();
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [tf, setTf] = useState("5m");                         // default: 5m
  const [lines, setLines] = useState<TradeLines>({});
  const [switching, setSwitching] = useState(false);
  // V29.x — Trading Mode (one-screen execution) vs Research Mode (full depth)
  const [mode, setMode] = useState<"Trading" | "Research">("Trading");

  useEffect(() => {
    api.symbols().then(setSymbols).catch(() => {});
    const saved = (typeof window !== "undefined" && localStorage.getItem("cat_mode")) as any;
    if (saved === "Trading" || saved === "Research") setMode(saved);
  }, []);

  const setModePersist = (m: typeof mode) => {
    setMode(m);
    try { localStorage.setItem("cat_mode", m); } catch {}
  };
  const showMiddle = mode === "Research";       // Market section (Research only)
  const showBottom = mode === "Research";       // Deep Analysis section (Research only)

  const onCandles = useCallback((_c: Candle[]) => {}, []);
  const onLines = useCallback((l: TradeLines) => setLines(l), []);

  // draw the decision's levels straight on the chart
  useEffect(() => {
    if (decision?.is_trade) {
      setLines({ entry: decision.entry, stop: decision.stop_loss,
                 targets: [decision.target1, decision.target2, decision.target3] });
    } else {
      setLines({});
    }
  }, [decision]);

  if (status && !status.connected) {
    return (
      <div className="max-w-md mx-auto mt-20 panel text-center">
        <div className="text-4xl mb-3">🔌</div>
        <h2 className="text-lg font-semibold mb-2">Not Connected</h2>
        <p className="text-sm text-terminal-muted mb-5">
          Enter your Client ID and Access Token, then press SAVE &amp; CONNECT.
        </p>
        <Link href="/settings" className="inline-block px-5 py-2.5 rounded-lg bg-terminal-accent text-black font-semibold text-sm">
          Open Settings
        </Link>
      </div>
    );
  }

  const symbol = status?.symbol ?? "NIFTY";
  const current = symbols.find((s) => s.symbol === symbol);
  const tvLabel = current?.tv_symbol ?? symbol;
  const sp = spot?.symbol === symbol ? spot : null;
  const live = !!sp?.ts && Date.now() / 1000 - sp.ts < 12;

  // Phase B — institutional / strike zones drawn on the chart
  const L: any = layers || {};
  const zones = [
    { price: L.trend?.vwap, title: "VWAP", color: "#6366f1", dashed: true },
    { price: L.expiry?.gamma_wall, title: "γ Wall", color: "#a855f7", dashed: true },
    { price: L.volume_profile?.poc, title: "POC", color: "#9ca3af", dashed: true },
    { price: L.structure?.resistance, title: "R", color: "#9ca3af" },
    { price: L.structure?.support, title: "S", color: "#9ca3af" },
    { price: (strike as any)?.strike, title: `★ ${(strike as any)?.type ?? ""}`, color: "#eab308" },
  ].filter((z) => typeof z.price === "number" && z.price > 0);

  async function pickSymbol(s: string) {
    if (s === symbol) return;
    setSwitching(true);
    try { await api.setSymbol(s); } catch {}
    setSwitching(false);
  }

  return (
    <div className="space-y-4">
      {/* V3.0 — Smart Alert Bar (sticky, single latest critical alert) */}
      <SafeBoundary name="Smart Alerts">
        <SmartAlertBar />
      </SafeBoundary>

      {/* ⚡ EARLY WARNING — the earliest catch, before the move even starts */}
      <SafeBoundary name="Early Warning">
        <EarlyWarning />
      </SafeBoundary>

      {/* 🔥 HOT NOW — action-first, the top opportunity at the very top */}
      <SafeBoundary name="Hot Now">
        <HotNow />
      </SafeBoundary>

      {/* 👀 AI Attention — where the radar's focus is now */}
      <SafeBoundary name="AI Attention Focus">
        <AIAttention />
      </SafeBoundary>

      {/* V20 ACTION-FIRST ORDER (user design review): decision → strike/plan →
          capture → index → shields; diagnostics move BELOW the action stack. */}

      {/* Premium Radar — the option buyer's live premium view (always-on) */}
      <SafeBoundary name="Premium Radar">
        <PremiumRadar />
      </SafeBoundary>

      {/* AI Thinking Now — the engine's live reasoning made visible */}
      <SafeBoundary name="AI Thinking">
        <AIThinkingPanel />
      </SafeBoundary>

      {/* AI Analysis — Gemini explains the live decision (cost-cached) */}
      <SafeBoundary name="AI Analysis">
        <AIAnalysisCard />
      </SafeBoundary>

      {/* AI Timeline — the day's market story (engine transitions) */}
      <SafeBoundary name="AI Timeline">
        <AITimelineCard />
      </SafeBoundary>

      {/* THE decision card — first thing on screen */}
      <SafeBoundary name="Live Candle">
        <LiveCandleCommand tf={tf} />
      </SafeBoundary>

      {/* V26 — AI Market Opportunity Board (staged scan; click → strike engine) */}
      <SafeBoundary name="Opportunity Board">
        <OpportunityBoard />
      </SafeBoundary>

      {/* V13 — AI Index Selector (best market before strike, per V20 flow) */}
      <SafeBoundary name="Index Radar">
        <IndexRadar />
      </SafeBoundary>

      {/* V28 — AI Trade Management (shows only while a trade is live) */}
      <SafeBoundary name="Trade Management">
        <TradeManagement />
      </SafeBoundary>

      {/* V16 — Scalping Tool: strike + entry details, visible while PREPARING */}
      <SafeBoundary name="Scalping Tool">
        <ScalpingTool />
      </SafeBoundary>

      {/* V9 §5 — Point Capture strip (points realistically available now) */}
      <SafeBoundary name="Point Capture">
        <PointCaptureStrip />
      </SafeBoundary>

      {/* V8 §8 — Gamma Shield (shows only when WATCH/HIGH/SPIKE) */}
      <SafeBoundary name="Gamma Shield">
        <GammaShield />
      </SafeBoundary>

      {/* diagnostics — single health source (System Verify replaced the old
          duplicate AI SELF-CHECK panel; owner: one health source only) */}
      <SafeBoundary name="System Verify">
        <SystemVerify />
      </SafeBoundary>
      <SafeBoundary name="AI Health">
        <AIHealthStrip />
      </SafeBoundary>
      <SafeBoundary name="Feed Diagnostics">
        <FeedDiagnostics />
      </SafeBoundary>
      <SafeBoundary name="Missed Winners">
        <MissedWinners />
      </SafeBoundary>
      <SafeBoundary name="Missed Move Protection">
        <MissedMoveProtection />
      </SafeBoundary>
      <SafeBoundary name="Voice Assistant">
        <VoiceAssistant />
      </SafeBoundary>

      {/* V1.0 P3 — Final Signal banner removed: the Hero Decision header is the
          single decision source; duplicates caused brain overload. */}

      {lastError && friendlyMessage(lastError) && (
        // Recoverable status, not a crash — amber, calm, never a raw exception.
        <div className="panel border-terminal-warn/40 text-terminal-warn text-sm py-2.5">
          {friendlyMessage(lastError)}
        </div>
      )}

      {/* TOP BAR */}
      <div className="panel py-2.5 flex flex-wrap items-center gap-x-4 gap-y-2">
        <select value={symbol} onChange={(e) => pickSymbol(e.target.value)} disabled={switching}
          className="bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm font-mono font-bold focus:border-terminal-accent outline-none disabled:opacity-60">
          <optgroup label="INDEX">
            {symbols.filter((s) => s.market_type === "INDEX").map((s) => <option key={s.symbol} value={s.symbol}>{s.symbol}</option>)}
          </optgroup>
          <optgroup label="COMMODITY">
            {symbols.filter((s) => s.market_type === "COMMODITY").map((s) => <option key={s.symbol} value={s.symbol}>{s.symbol}</option>)}
          </optgroup>
          {current === undefined && <option value={symbol}>{symbol}</option>}
        </select>

        <div className="flex gap-0.5 bg-terminal-bg rounded-lg p-0.5 border border-terminal-border">
          {TIMEFRAMES.map((t) => (
            <button key={t} onClick={() => setTf(t)}
              className={`px-2.5 py-1 text-[11px] font-mono rounded-md transition-colors ${
                tf === t ? "bg-terminal-accent text-black font-bold" : "text-terminal-muted hover:text-white"}`}>
              {t}
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-3">
          <span key={sp?.ts}
            className={`font-mono text-lg font-bold ${sp?.tick_dir === "up" ? "tick-up" : sp?.tick_dir === "down" ? "tick-down" : ""}`}>
            {fmt(sp?.ltp)}
          </span>
          <span className={`font-mono text-xs ${(sp?.change ?? 0) >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
            {sp ? `${sp.change >= 0 ? "+" : ""}${fmt(sp.change)} (${sp.change_pct ?? 0}%)` : ""}
          </span>
          <span className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-bold tracking-wider ${
            live ? "bg-terminal-bull/15 text-terminal-bull" : "bg-terminal-warn/15 text-terminal-warn"}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${live ? "bg-terminal-bull animate-pulse" : "bg-terminal-warn"}`} />
            {live ? "LIVE" : "DELAYED"}
          </span>
        </div>
      </div>

      {/* PHASE 4/11 — calm Market-Closed banner (amber, with countdown) */}
      <SafeBoundary name="Market Status">
        <MarketStatusBanner />
      </SafeBoundary>

      {/* Market-closed Daily Review — keeps the screen alive after hours */}
      <SafeBoundary name="Daily Review">
        <DailyReview />
      </SafeBoundary>

      {/* PHASE D — Safe Mode (disaster recovery) — highest-priority banner */}
      <SafeBoundary name="Safe Mode">
        <SafeModeBanner />
      </SafeBoundary>

      {/* PHASE 14 — Kill Switch (capital-protection veto) above the action */}
      <SafeBoundary name="Kill Switch">
        <KillSwitchBanner />
      </SafeBoundary>

      {/* V29.x — Trading Mode (one screen) vs Research Mode (full depth) */}
      <div className="flex items-center justify-end gap-2">
        <div className="flex gap-0.5 bg-terminal-bg rounded-lg p-0.5 border border-terminal-border">
          {(["Trading", "Research"] as const).map((m) => (
            <button key={m} onClick={() => setModePersist(m)}
              className={`px-3 py-1 text-[11px] rounded-md transition-colors ${
                mode === m ? "bg-terminal-accent text-black font-bold" : "text-terminal-muted hover:text-white"}`}>
              {m === "Trading" ? "⚡ Trading" : "🔬 Research"}
            </button>
          ))}
        </div>
      </div>

      {/* Research-mode quick links to the deep-analysis pages */}
      {mode === "Research" && (
        <div className="flex flex-wrap gap-1.5">
          {[["🧠 AI Workspace", "/ai-workspace"], ["Analysis", "/advanced"], ["Market DNA", "/dna"], ["Simulator", "/simulator"],
            ["Evolution", "/evolution"], ["Research Lab", "/research"], ["Report Card", "/report-card"],
            ["Audit", "/audit"], ["Replay", "/replay"], ["Brain", "/brain"]].map(([label, href]) => (
            <Link key={href} href={href}
              className="text-[11px] px-2.5 py-1 rounded-full border border-terminal-border text-terminal-muted hover:border-terminal-accent hover:text-white">
              {label}
            </Link>
          ))}
        </div>
      )}

      {/* ═══ TOP — DECISION ═══
          Trading mode = ONE decision card + ladder + entry gauge (no WAIT repeated).
          Research mode reveals the full per-engine breakdown. */}
      <div className="text-[10px] font-bold tracking-widest text-terminal-muted pt-1">DECISION</div>

      {/* V2.1 — everything else (Execution Card, Strike Queue, all scores)
          lives in Research. Trading mode = the one card above + evidence. */}

      {showMiddle && (
        <>
          <SafeBoundary name="Final Decision"><FinalDecisionHeader /></SafeBoundary>
          <SafeBoundary name="Execution Card"><ExecutionCard /></SafeBoundary>
          <SafeBoundary name="Strike Queue"><StrikeQueue /></SafeBoundary>
          <SafeBoundary name="Market Path"><MarketPathPanel /></SafeBoundary>
          <SafeBoundary name="Alpha"><AlphaPanel /></SafeBoundary>
          <SafeBoundary name="Entry Score Timeline"><EntryScoreTimeline /></SafeBoundary>
          <SafeBoundary name="Premium Roadmap"><PremiumTimeline /></SafeBoundary>
          <SafeBoundary name="Execution Control Center"><ExecutionControlCenter /></SafeBoundary>
          <SafeBoundary name="Decision Intelligence"><DecisionIntelligence /></SafeBoundary>
          <SafeBoundary name="Entry Deck"><EntryFirstDeck /></SafeBoundary>
          <SafeBoundary name="Entry Checklist"><EntryChecklist /></SafeBoundary>
          <SafeBoundary name="Signal Maturity"><SignalMaturity /></SafeBoundary>
          {/* V32 Layer-6 — historical analogue days (Research; context, not prediction) */}
          <SafeBoundary name="Market Memory"><MarketMemory /></SafeBoundary>
          {/* Global context — live feed when reachable; honest waiting line otherwise */}
          <SafeBoundary name="Global Context"><GlobalStrip /></SafeBoundary>
        </>
      )}

      {/* ═══ MIDDLE — MARKET (Professional + Institutional) ═══ */}
      {showMiddle && (
        <>
          <div className="text-[10px] font-bold tracking-widest text-terminal-muted pt-2">MARKET</div>
          <SafeBoundary name="Entry Zone & Premium"><EntryZonePremium /></SafeBoundary>
          <SafeBoundary name="Candle Projection"><CandleProjection /></SafeBoundary>
          <SafeBoundary name="Probability Ladder"><ProbabilityLadder /></SafeBoundary>
          <SafeBoundary name="Confidence Evolution"><ConfidenceEvolution /></SafeBoundary>
          <SafeBoundary name="Decision Matrix"><DecisionMatrix /></SafeBoundary>
          <SafeBoundary name="Live Chart">
            <div className="panel p-0 overflow-hidden">
              <ProChart symbol={symbol} tvLabel={tvLabel} tf={tf} lines={lines} zones={zones}
                projection={(decision as any)?.candle_projection}
                noTradeZone={!decision?.is_trade} onCandles={onCandles} />
            </div>
          </SafeBoundary>
        </>
      )}

      {/* EXIT INTELLIGENCE — always shown while a trade is live (capital safety) */}
      <SafeBoundary name="Exit Intelligence"><ExitIntelligencePanel /></SafeBoundary>

      {/* ═══ BOTTOM — DEEP ANALYSIS (Institutional only) ═══ */}
      {showBottom && (
        <>
          <div className="text-[10px] font-bold tracking-widest text-terminal-muted pt-2">DEEP ANALYSIS</div>
          <SafeBoundary name="Scalp Radar"><ScalpRadarPanel /></SafeBoundary>
        </>
      )}

      <div className="flex justify-center">
        <Link href="/advanced"
          className="text-xs text-terminal-muted hover:text-terminal-accent border border-terminal-border rounded-lg px-4 py-2">
          Show full analysis (layers, option chain, Greeks, strike engine) →
        </Link>
      </div>

      {/* Production observability (owner: Trust by Verification) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SafeBoundary name="Build Version">
          <BuildVersion />
        </SafeBoundary>
        <SafeBoundary name="AI Changelog">
          <AIChangelog />
        </SafeBoundary>
      </div>
    </div>
  );
}
