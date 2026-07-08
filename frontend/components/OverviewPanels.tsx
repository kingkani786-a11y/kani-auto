"use client";
// Market Overview, Greeks Dashboard, and Smart Money panels.

import { useMarket } from "@/lib/store";

const fmt = (n?: number | null, d = 2) =>
  n === undefined || n === null || Number.isNaN(n) ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: d });

const fmtL = (n?: number) =>
  n === undefined || n === null ? "—" : Math.abs(n) >= 1e7 ? `${(n / 1e7).toFixed(2)}Cr` : Math.abs(n) >= 1e5 ? `${(n / 1e5).toFixed(2)}L` : fmt(n, 0);

function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: "bull" | "bear" | "warn" }) {
  const color =
    tone === "bull" ? "text-terminal-bull" : tone === "bear" ? "text-terminal-bear" : tone === "warn" ? "text-terminal-warn" : "";
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${color}`}>{value}</div>
    </div>
  );
}

const trendTone = (t?: string) => (t === "BULLISH" ? "bull" : t === "BEARISH" ? "bear" : undefined);

export function MarketOverview() {
  const { status, spot, signal, risk, analytics } = useMarket();
  const tech = signal?.tech;
  return (
    <section className="panel">
      <div className="panel-title">Market Overview</div>
      <div className="flex items-baseline gap-3 mb-4">
        <span className="text-2xl font-mono font-bold">{status?.symbol ?? "—"}</span>
        <span
          key={spot?.ts}
          className={`text-3xl font-mono ${spot?.tick_dir === "up" ? "tick-up" : spot?.tick_dir === "down" ? "tick-down" : ""}`}
        >
          {fmt(spot?.ltp)}
        </span>
        <span className={`text-sm font-mono ${(spot?.change ?? 0) >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
          {spot ? `${spot.change >= 0 ? "+" : ""}${fmt(spot.change)}` : ""}
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3">
        <Stat label="Market Type" value={status?.market_type ?? "—"} />
        <Stat label="Trend" value={tech?.trend ?? "—"} tone={trendTone(tech?.trend)} />
        <Stat label="Momentum" value={tech ? `${fmt(tech.momentum, 2)}%` : "—"} tone={tech && tech.momentum >= 0 ? "bull" : "bear"} />
        <Stat label="Volatility (ATR)" value={fmt(tech?.atr)} />
        <Stat label="Strength (ADX)" value={fmt(tech?.adx, 1)} />
        <Stat label="Confidence" value={signal ? `${signal.confidence}%` : "—"} />
        <Stat label="VWAP" value={fmt(tech?.vwap)} />
        <Stat label="Max Pain" value={fmt(analytics.max_pain, 0)} />
        <Stat label="Data Quality" value={risk?.data_quality ?? status?.data_quality ?? "—"} tone={risk?.data_quality !== "GOOD" ? "warn" : undefined} />
      </div>
    </section>
  );
}

export function GreeksPanel() {
  const { greeks, analytics, status } = useMarket();
  if (status?.market_type === "COMMODITY") return null;
  const rows: [string, keyof NonNullable<typeof greeks.ce>][] = [
    ["Delta", "delta"], ["Gamma", "gamma"], ["Theta", "theta"], ["Vega", "vega"], ["IV", "iv"],
  ];
  return (
    <section className="panel">
      <div className="panel-title">Greeks — ATM {fmt(analytics.atm_strike, 0)} ({analytics.expiry ?? "—"})</div>
      <table className="w-full text-sm font-mono">
        <thead>
          <tr className="stat-label text-left">
            <th className="pb-2 font-normal">Greek</th>
            <th className="pb-2 font-normal text-terminal-bull">CALL</th>
            <th className="pb-2 font-normal text-terminal-bear">PUT</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, key]) => (
            <tr key={key} className="border-t border-terminal-border/50">
              <td className="py-1.5 text-terminal-muted">{label}</td>
              <td className="py-1.5">{fmt(greeks.ce?.[key], key === "gamma" ? 5 : 3)}</td>
              <td className="py-1.5">{fmt(greeks.pe?.[key], key === "gamma" ? 5 : 3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="grid grid-cols-3 gap-3 mt-4">
        <Stat label="PCR" value={fmt(analytics.pcr, 3)} tone={(analytics.pcr ?? 1) > 1 ? "bull" : "bear"} />
        <Stat label="Call OI" value={fmtL(analytics.call_oi)} />
        <Stat label="Put OI" value={fmtL(analytics.put_oi)} />
        <Stat label="Call OI Δ" value={fmtL(analytics.call_oi_change)} tone={(analytics.call_oi_change ?? 0) > 0 ? "bear" : "bull"} />
        <Stat label="Put OI Δ" value={fmtL(analytics.put_oi_change)} tone={(analytics.put_oi_change ?? 0) > 0 ? "bull" : "bear"} />
      </div>
    </section>
  );
}

const FLOW_LABELS: Record<string, { text: string; tone: "bull" | "bear" }> = {
  PUT_WRITING: { text: "Put Writing", tone: "bull" },
  CALL_WRITING: { text: "Call Writing", tone: "bear" },
  SHORT_COVERING: { text: "Short Covering", tone: "bull" },
  LONG_BUILDUP: { text: "Long Build-Up", tone: "bull" },
  SHORT_BUILDUP: { text: "Short Build-Up", tone: "bear" },
  LONG_UNWINDING: { text: "Long Unwinding", tone: "bear" },
  NEUTRAL: { text: "Neutral", tone: "bull" },
};

export function SmartMoneyPanel() {
  const { smartMoney } = useMarket();
  const acts = smartMoney?.activities ?? [];
  return (
    <section className="panel">
      <div className="panel-title">Smart Money</div>
      <div className="flex flex-wrap gap-2">
        {acts.length === 0 && <span className="text-sm text-terminal-muted">No notable flow detected</span>}
        {acts.map((a) => {
          const f = FLOW_LABELS[a] ?? { text: a, tone: "bull" as const };
          return (
            <span
              key={a}
              className={`px-2.5 py-1 rounded-full text-xs border ${
                f.tone === "bull"
                  ? "border-terminal-bull/40 text-terminal-bull bg-terminal-bull/10"
                  : "border-terminal-bear/40 text-terminal-bear bg-terminal-bear/10"
              }`}
            >
              {f.text}
            </span>
          );
        })}
      </div>
      {smartMoney?.bias && (
        <div className="mt-3">
          <span className="stat-label">Net Bias </span>
          <span className={`stat-value ${smartMoney.bias === "BULLISH" ? "text-terminal-bull" : smartMoney.bias === "BEARISH" ? "text-terminal-bear" : ""}`}>
            {smartMoney.bias}
          </span>
        </div>
      )}
    </section>
  );
}
