"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMarket } from "@/lib/store";
import { api } from "@/lib/api";

function Dot({ on, warn }: { on: boolean; warn?: boolean }) {
  const color = on ? (warn ? "bg-terminal-warn" : "bg-terminal-bull") : "bg-terminal-bear";
  return <span className={`inline-block w-2 h-2 rounded-full ${color} ${on ? "animate-pulse" : ""}`} />;
}

// V7 Market Independence Phase A (owner, 2026-07-23) — one chip per registered
// exchange, so "system is idle" and "NSE happens to be closed right now" read
// as two different things. NOT_CONFIGURED (Currency — Dhan CDS access
// unverified, parked) renders grey, never a fabricated red/green.
const EXCHANGE_LABEL: Record<string, string> = { INDEX: "NSE", COMMODITY: "MCX", CURRENCY: "Currency" };
const EXCHANGE_ORDER = ["INDEX", "COMMODITY", "CURRENCY"];

function ActiveMarketStrip({ exchanges, autoSwitch, onToggleAuto }: {
  exchanges: Record<string, any> | undefined;
  autoSwitch: boolean | undefined;
  onToggleAuto: () => void;
}) {
  if (!exchanges) return null;
  return (
    <span className="hidden md:flex items-center gap-2.5 pl-2 border-l border-terminal-border">
      <span className="text-[9px] text-terminal-muted uppercase tracking-wide">Active Market</span>
      {EXCHANGE_ORDER.map((mt) => {
        const ex = exchanges[mt];
        if (!ex) return null;
        const configured = ex.status !== "NOT_CONFIGURED";
        return (
          <span key={mt} className="flex items-center gap-1" title={configured ? ex.status : ex.reason}>
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${
              !configured ? "bg-terminal-muted/40" : ex.is_open ? "bg-terminal-bull animate-pulse" : "bg-terminal-bear"
            }`} />
            {EXCHANGE_LABEL[mt] || mt}
          </span>
        );
      })}
      <button
        onClick={onToggleAuto}
        title="Auto-switch to whichever registered market is open (NSE closed -> MCX open -> switch). Off pins the current symbol through its own close."
        className={`text-[9px] px-1.5 py-0.5 rounded border ${
          autoSwitch ? "border-terminal-bull/50 text-terminal-bull" : "border-terminal-border text-terminal-muted"
        }`}
      >
        {autoSwitch ? "AUTO" : "MANUAL"}
      </button>
    </span>
  );
}

export function StatusBar() {
  const { status, wsOk, refreshStatus } = useMarket();
  const path = usePathname();
  const nav = [
    { href: "/", label: "Dashboard" },
    { href: "/cockpit", label: "Command Center" },
    { href: "/advanced", label: "Analysis" },
    { href: "/command", label: "Command" },
    { href: "/brain", label: "AI Brain" },
    { href: "/strategist", label: "Chief Strategist" },
    { href: "/dna", label: "Market DNA" },
    { href: "/simulator", label: "Simulator" },
    { href: "/evolution", label: "Evolution" },
    { href: "/research", label: "Research Lab" },
    { href: "/weights", label: "Weights" },
    { href: "/future", label: "AI Future" },
    { href: "/warroom", label: "War Room" },
    { href: "/stocks", label: "Stocks" },
    { href: "/scanner", label: "Scanner" },
    { href: "/paper", label: "Paper" },
    { href: "/backtest", label: "Backtest" },
    { href: "/replay", label: "Replay" },
    { href: "/analytics", label: "Analytics" },
    { href: "/report-card", label: "Report Card" },
    { href: "/audit", label: "Audit" },
    { href: "/journal", label: "Journal" },
    { href: "/health", label: "Health" },
    { href: "/settings", label: "Settings" },
  ];

  return (
    <header className="sticky top-0 z-40 bg-terminal-bg/95 backdrop-blur border-b border-terminal-border">
      <div className="max-w-[1500px] mx-auto px-3 sm:px-5 h-14 flex items-center gap-4">
        <div className="font-bold tracking-tight text-sm sm:text-base">
          <span className="text-terminal-accent">CLOUD</span> AI TRADER
        </div>
        <nav className="flex gap-1 text-xs overflow-x-auto">
          {nav.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                path === n.href
                  ? "bg-terminal-panel text-white border border-terminal-border"
                  : "text-terminal-muted hover:text-white"
              }`}
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-4 text-[11px] text-terminal-muted">
          <span className="hidden sm:flex items-center gap-1.5">
            <Dot on={wsOk} /> WS
          </span>
          <span className="flex items-center gap-1.5">
            <Dot on={!!status?.connected} /> {status?.connected ? "CONNECTED" : "OFFLINE"}
          </span>
          <span className="hidden sm:flex items-center gap-1.5">
            <Dot on={!!status?.market_open} warn={!status?.market_open} />
            {status?.market_open ? "MARKET OPEN" : "MARKET CLOSED"}
          </span>
          <ActiveMarketStrip
            exchanges={status?.market_exchanges}
            autoSwitch={status?.auto_market_switch}
            onToggleAuto={async () => {
              await api.setAutoMarketSwitch(!status?.auto_market_switch);
              await refreshStatus();
            }}
          />
        </div>
      </div>
    </header>
  );
}
