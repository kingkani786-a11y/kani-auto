"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMarket } from "@/lib/store";

function Dot({ on, warn }: { on: boolean; warn?: boolean }) {
  const color = on ? (warn ? "bg-terminal-warn" : "bg-terminal-bull") : "bg-terminal-bear";
  return <span className={`inline-block w-2 h-2 rounded-full ${color} ${on ? "animate-pulse" : ""}`} />;
}

export function StatusBar() {
  const { status, wsOk } = useMarket();
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
        </div>
      </div>
    </header>
  );
}
