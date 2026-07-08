"use client";
// Full analytical view — every detailed panel from V6/V7.5 lives here so the
// main dashboard stays ultra-simple (V10 Golden Rule). Nothing was removed
// from the platform; it's one click away.

import Link from "next/link";
import { useMarket } from "@/lib/store";
import { MarketOverview, GreeksPanel, SmartMoneyPanel } from "@/components/OverviewPanels";
import { SignalPanel, ExplanationPanel, RiskPanel } from "@/components/SignalPanels";
import { OptionChainTable } from "@/components/OptionChainTable";
import { LayersPanel, StrikePanel, NarratorPanel, EarlyWarningPanel } from "@/components/XPanels";
import { DecisionView } from "@/components/DecisionView";
import { ConfidenceMeter } from "@/components/ConfidenceMeter";
import { MarketNarratorPanel } from "@/components/MarketNarratorPanel";
import { DecisionExplainer } from "@/components/DecisionExplainer";
import { FuturesPanel } from "@/components/FuturesPanel";
import { DataQualityPanel } from "@/components/DataQualityPanel";
import { SafeBoundary } from "@/components/SafeBoundary";

export default function AdvancedPage() {
  const { status } = useMarket();

  if (status && !status.connected) {
    return (
      <div className="max-w-md mx-auto mt-20 panel text-center">
        <p className="text-sm text-terminal-muted mb-4">Connect first to see full analysis.</p>
        <Link href="/settings" className="inline-block px-5 py-2.5 rounded-lg bg-terminal-accent text-black font-semibold text-sm">
          Open Settings
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-sm font-bold tracking-wide text-terminal-muted uppercase">Full Analysis — {status?.symbol}</h1>
        <Link href="/" className="text-xs text-terminal-accent border border-terminal-border rounded-lg px-3 py-1.5">
          ← Back to decision view
        </Link>
      </div>

      <EarlyWarningPanel />

      {/* moved off the entry-first dashboard: confidence + narrator + explainer */}
      <div className="grid lg:grid-cols-2 gap-4">
        <SafeBoundary name="AI Confidence"><ConfidenceMeter /></SafeBoundary>
        <SafeBoundary name="AI Market Narrator"><MarketNarratorPanel /></SafeBoundary>
      </div>
      <div className="grid lg:grid-cols-3 gap-4">
        <SafeBoundary name="Futures Intelligence"><FuturesPanel /></SafeBoundary>
        <SafeBoundary name="Decision Explainer"><DecisionExplainer /></SafeBoundary>
        <SafeBoundary name="Data Quality"><DataQualityPanel /></SafeBoundary>
      </div>

      {/* full decision detail (capital protection, no-trade-zone, traps, roadmap) */}
      <SafeBoundary name="Decision Center"><DecisionView /></SafeBoundary>

      <div className="grid lg:grid-cols-3 gap-4">
        <MarketOverview />
        <SignalPanel />
        <LayersPanel />
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <StrikePanel />
        <NarratorPanel />
        <div className="space-y-4">
          <RiskPanel />
          <SmartMoneyPanel />
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <ExplanationPanel />
        <div className="lg:col-span-2">
          <OptionChainTable />
        </div>
      </div>

      <GreeksPanel />
    </div>
  );
}
