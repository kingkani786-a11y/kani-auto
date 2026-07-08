"use client";
// Smart Entry Panel — manual levels or Auto Mode. Auto suggestions come from
// the live AI signal when one is active, otherwise from candle strength
// (ATR), price location vs recent extremes, and momentum. The levels feed
// straight into the chart overlay (entry/SL/target price lines).

import { useEffect, useMemo, useState } from "react";
import type { Candle, TradeLines } from "./ProChart";
import { useMarket } from "@/lib/store";

export type EntryType = "Breakout" | "Reversal" | "Momentum";
type RiskLevel = "Low" | "Medium" | "High";

const RISK_SL_MULT: Record<RiskLevel, number> = { Low: 1.0, Medium: 1.3, High: 1.7 };

function suggest(candles: Candle[], type: EntryType, risk: RiskLevel) {
  if (candles.length < 25) return null;
  const recent = candles.slice(-20);
  const atr = recent.reduce((a, c) => a + (c.high - c.low), 0) / recent.length;
  const close = candles[candles.length - 1].close;
  const hi = Math.max(...recent.map((c) => c.high));
  const lo = Math.min(...recent.map((c) => c.low));
  const mom = close / candles[candles.length - 11].close - 1; // 10-bar momentum

  let dir: 1 | -1;
  let entry: number;
  if (type === "Breakout") {
    dir = close - lo > hi - close ? 1 : -1;            // break the nearer extreme
    entry = dir === 1 ? hi + 0.15 * atr : lo - 0.15 * atr;
  } else if (type === "Reversal") {
    dir = mom >= 0 ? -1 : 1;                            // fade the move
    entry = close;
  } else {
    dir = mom >= 0 ? 1 : -1;                            // ride the move
    entry = close;
  }
  const slDist = RISK_SL_MULT[risk] * 1.2 * atr;
  const r = (n: number) => Math.round(n * 100) / 100;
  return {
    entry: r(entry),
    stop: r(entry - dir * slDist),
    t1: r(entry + dir * 1.5 * atr),
    t2: r(entry + dir * 2.5 * atr),
    t3: r(entry + dir * 4.0 * atr),
    dir,
  };
}

export function EntryPanel({
  candles, onLines,
}: {
  candles: Candle[];
  onLines: (l: TradeLines) => void;
}) {
  const { signal, lifecycle } = useMarket();
  const [entryType, setEntryType] = useState<EntryType>("Breakout");
  const [risk, setRisk] = useState<RiskLevel>("Medium");
  const [auto, setAuto] = useState(true);
  const [form, setForm] = useState({ entry: "", stop: "", t1: "", t2: "", t3: "" });

  const liveSignal = signal && signal.signal !== "NO TRADE" ? signal : null;

  const autoLevels = useMemo(() => {
    if (!auto) return null;
    if (liveSignal?.entry && liveSignal.stop_loss) {
      return {
        entry: liveSignal.entry, stop: liveSignal.stop_loss,
        t1: liveSignal.target1 ?? null, t2: liveSignal.target2 ?? null,
        t3: liveSignal.target3 ?? null, source: "AI SIGNAL",
      };
    }
    const s = suggest(candles, entryType, risk);
    return s ? { ...s, source: "CANDLE ENGINE" } : null;
  }, [auto, liveSignal, candles, entryType, risk]);

  // push whichever levels are active onto the chart
  useEffect(() => {
    if (auto && autoLevels) {
      onLines({ entry: autoLevels.entry, stop: autoLevels.stop,
                targets: [autoLevels.t1, autoLevels.t2, autoLevels.t3] });
    } else {
      const n = (v: string) => (v === "" ? null : Number(v) || null);
      onLines({ entry: n(form.entry), stop: n(form.stop),
                targets: [n(form.t1), n(form.t2), n(form.t3)] });
    }
  }, [auto, autoLevels, form, onLines]);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  const num = (v?: number | null) =>
    v === null || v === undefined ? "—" : v.toLocaleString("en-IN", { maximumFractionDigits: 2 });

  const field = (label: string, key: keyof typeof form, autoVal?: number | null, tone = "") => (
    <div>
      <div className="stat-label mb-1">{label}</div>
      {auto ? (
        <div className={`font-mono text-sm py-1.5 ${tone}`}>{num(autoVal)}</div>
      ) : (
        <input value={form[key]} onChange={set(key)} type="number" step="any" placeholder="0.00"
          className="w-full bg-terminal-bg border border-terminal-border rounded-lg px-2.5 py-1.5 text-sm font-mono focus:border-terminal-accent outline-none" />
      )}
    </div>
  );

  return (
    <section className="panel h-full">
      <div className="panel-title flex items-center justify-between">
        <span>Entry System</span>
        <button onClick={() => setAuto(!auto)}
          className={`px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wide transition-colors ${
            auto ? "bg-terminal-accent text-black" : "bg-terminal-bg border border-terminal-border text-terminal-muted"
          }`}>
          AUTO {auto ? "ON" : "OFF"}
        </button>
      </div>

      <div className="space-y-3">
        <div>
          <div className="stat-label mb-1.5">Entry Type</div>
          <div className="flex gap-1">
            {(["Breakout", "Reversal", "Momentum"] as EntryType[]).map((t) => (
              <button key={t} onClick={() => setEntryType(t)}
                className={`flex-1 px-1 py-1.5 rounded-lg text-[11px] border transition-colors ${
                  entryType === t
                    ? "border-terminal-accent text-terminal-accent bg-terminal-accent/10"
                    : "border-terminal-border text-terminal-muted hover:text-white"
                }`}>
                {t}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="stat-label mb-1.5">Risk Level</div>
          <div className="flex gap-1">
            {(["Low", "Medium", "High"] as RiskLevel[]).map((r) => (
              <button key={r} onClick={() => setRisk(r)}
                className={`flex-1 px-1 py-1.5 rounded-lg text-[11px] border transition-colors ${
                  risk === r
                    ? r === "High" ? "border-terminal-bear text-terminal-bear bg-terminal-bear/10"
                      : r === "Low" ? "border-terminal-bull text-terminal-bull bg-terminal-bull/10"
                      : "border-terminal-warn text-terminal-warn bg-terminal-warn/10"
                    : "border-terminal-border text-terminal-muted hover:text-white"
                }`}>
                {r}
              </button>
            ))}
          </div>
        </div>

        {auto && autoLevels && "source" in autoLevels && (
          <div className="text-[10px] text-terminal-muted">
            Suggested by <span className="text-terminal-accent font-bold">{autoLevels.source}</span>
            {autoLevels.source === "CANDLE ENGINE" &&
              ` · ${"dir" in autoLevels && autoLevels.dir === 1 ? "LONG" : "SHORT"} bias`}
          </div>
        )}
        {auto && !autoLevels && (
          <div className="text-[11px] text-terminal-muted">Waiting for chart data to suggest levels…</div>
        )}

        <div className="grid grid-cols-2 gap-x-3 gap-y-2 pt-1 border-t border-terminal-border/50">
          {field("Entry Price", "entry", autoLevels?.entry, "text-terminal-accent")}
          {field("Stop Loss", "stop", autoLevels?.stop, "text-terminal-bear")}
          {field("Target 1", "t1", autoLevels?.t1, "text-terminal-bull")}
          {field("Target 2", "t2", autoLevels?.t2, "text-terminal-bull")}
          {field("Target 3", "t3", autoLevels?.t3, "text-terminal-bull")}
          <div>
            <div className="stat-label mb-1">R : R (T2)</div>
            <div className="font-mono text-sm py-1.5">
              {(() => {
                const e = auto ? autoLevels?.entry : Number(form.entry);
                const s = auto ? autoLevels?.stop : Number(form.stop);
                const t = auto ? autoLevels?.t2 : Number(form.t2);
                if (!e || !s || !t || e === s) return "—";
                return `${(Math.abs(t - e) / Math.abs(e - s)).toFixed(2)} : 1`;
              })()}
            </div>
          </div>
        </div>

        {lifecycle && lifecycle.state !== "SETUP" && (
          <div className="text-[10px] text-terminal-muted pt-1 border-t border-terminal-border/50">
            Lifecycle: <span className="text-terminal-accent font-bold">{lifecycle.state}</span>
            {lifecycle.trigger_price ? ` · trigger ${num(lifecycle.trigger_price)}` : ""}
          </div>
        )}
        <p className="text-[9px] text-terminal-muted leading-relaxed">
          Levels are drawn on the chart instantly. Decision-support only — no orders are placed.
        </p>
      </div>
    </section>
  );
}
