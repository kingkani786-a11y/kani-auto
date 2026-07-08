"use client";
// Market Replay — step through any historical session minute-by-minute,
// watching candles, AI decision markers, and (when recorded) OI/PCR evolve.

import { useEffect, useRef, useState } from "react";
import {
  createChart, ColorType, IChartApi, ISeriesApi, UTCTimestamp,
} from "lightweight-charts";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";
import type { SymbolInfo } from "@/lib/types";

const IST = 19800;

interface Marker {
  time: number; decision: string; score: number; trend: string;
  structure_event?: string; alignment: number; adx: number; momentum: number;
}

export default function ReplayPage() {
  const { status } = useMarket();
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [symbol, setSymbol] = useState("NIFTY");
  const [date, setDate] = useState(() => {
    const d = new Date(Date.now() - 86400000);
    return d.toISOString().slice(0, 10);
  });
  const [session, setSession] = useState<any>(null);
  const [idx, setIdx] = useState(0);          // candles revealed so far
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(4);      // candles per second when playing
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const holderRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    api.symbols().then(setSymbols).catch(() => {});
  }, []);

  // chart instance
  useEffect(() => {
    if (!holderRef.current) return;
    const chart = createChart(holderRef.current, {
      layout: { background: { type: ColorType.Solid, color: "#11161f" }, textColor: "#8b96a8", fontSize: 11 },
      grid: { vertLines: { color: "rgba(29,37,51,0.5)" }, horzLines: { color: "rgba(29,37,51,0.5)" } },
      rightPriceScale: { borderColor: "#1d2533" },
      timeScale: { borderColor: "#1d2533", timeVisible: true, secondsVisible: false },
      autoSize: true,
    });
    seriesRef.current = chart.addCandlestickSeries({
      upColor: "#16c784", downColor: "#ea3943",
      wickUpColor: "#16c784", wickDownColor: "#ea3943", borderVisible: false,
    });
    chartRef.current = chart;
    return () => { chart.remove(); chartRef.current = null; seriesRef.current = null; };
  }, []);

  // render revealed candles + markers up to idx
  useEffect(() => {
    const s = seriesRef.current;
    if (!s || !session) return;
    const visible = session.candles.slice(0, idx);
    s.setData(visible.map((c: any) => ({
      time: (c.time + IST) as UTCTimestamp,
      open: c.open, high: c.high, low: c.low, close: c.close,
    })));
    const cutoff = visible.length ? visible[visible.length - 1].time : 0;
    s.setMarkers(
      (session.markers as Marker[])
        .filter((m) => m.time <= cutoff && m.decision !== "NO TRADE")
        .map((m) => ({
          time: (m.time + IST) as UTCTimestamp,
          position: m.decision === "BULLISH" ? "belowBar" as const : "aboveBar" as const,
          color: m.decision === "BULLISH" ? "#16c784" : "#ea3943",
          shape: m.decision === "BULLISH" ? "arrowUp" as const : "arrowDown" as const,
          text: `${m.decision[0]} ${m.score}`,
        })));
    chartRef.current?.timeScale().scrollToRealTime();
  }, [session, idx]);

  // playback timer
  useEffect(() => {
    if (!playing || !session) return;
    const t = setInterval(() => {
      setIdx((i) => {
        if (i >= session.candles.length) { setPlaying(false); return i; }
        return i + 1;
      });
    }, 1000 / speed);
    return () => clearInterval(t);
  }, [playing, speed, session]);

  async function load() {
    setBusy(true); setError(""); setPlaying(false);
    try {
      const r = await api.replay(symbol, date);
      setSession(r);
      setIdx(Math.min(30, r.candles.length));
    } catch (e: any) {
      setSession(null);
      setError(e.message || "Replay failed");
    } finally {
      setBusy(false);
    }
  }

  const lastMarker: Marker | undefined = session?.markers
    ?.filter((m: Marker) => idx > 0 && m.time <= session.candles[Math.max(idx - 1, 0)]?.time)
    ?.slice(-1)[0];
  const lastMemory = session?.chain_history
    ?.filter((r: any) => idx > 0 && new Date(r.ts).getTime() / 1000 <= (session.candles[Math.max(idx - 1, 0)]?.time ?? 0) + IST)
    ?.slice(-1)[0];
  const cur = session?.candles[Math.max(idx - 1, 0)];

  return (
    <div className="space-y-4">
      <section className="panel">
        <div className="panel-title">Market Replay</div>
        <div className="flex flex-wrap items-center gap-2">
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}
            className="bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm font-mono">
            {(symbols.length ? symbols : [{ symbol: "NIFTY" } as SymbolInfo]).map((s) => (
              <option key={s.symbol} value={s.symbol}>{s.symbol}</option>
            ))}
          </select>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
            className="bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm font-mono" />
          <button onClick={load} disabled={busy || !status?.connected}
            className="px-4 py-2 rounded-lg bg-terminal-accent text-black text-sm font-bold disabled:opacity-50">
            {busy ? "LOADING…" : "LOAD SESSION"}
          </button>
          {!status?.connected && <span className="text-xs text-terminal-muted">Connect in Settings first</span>}
          {error && <span className="text-xs text-terminal-bear">✕ {error}</span>}
        </div>
      </section>

      {session && (
        <>
          <section className="panel p-0 overflow-hidden">
            <div className="relative h-[380px] sm:h-[460px]">
              <div ref={holderRef} className="absolute inset-0" />
              <div className="absolute top-2 left-3 z-10 text-[11px] font-mono text-terminal-muted pointer-events-none">
                REPLAY · {session.symbol} · {session.date}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 px-4 py-3 border-t border-terminal-border">
              <button onClick={() => setPlaying(!playing)}
                className="px-4 py-1.5 rounded-lg bg-terminal-accent text-black text-xs font-bold w-20">
                {playing ? "PAUSE" : "PLAY"}
              </button>
              <button onClick={() => setIdx((i) => Math.min(i + 1, session.candles.length))}
                className="px-3 py-1.5 rounded-lg border border-terminal-border text-xs hover:border-terminal-accent">
                +1m STEP
              </button>
              <button onClick={() => { setIdx(Math.min(30, session.candles.length)); setPlaying(false); }}
                className="px-3 py-1.5 rounded-lg border border-terminal-border text-xs hover:border-terminal-accent">
                RESET
              </button>
              <div className="flex gap-1 ml-2">
                {[1, 4, 10].map((s) => (
                  <button key={s} onClick={() => setSpeed(s)}
                    className={`px-2 py-1 rounded text-[10px] font-mono ${speed === s ? "bg-terminal-accent text-black font-bold" : "text-terminal-muted border border-terminal-border"}`}>
                    {s}x
                  </button>
                ))}
              </div>
              <input type="range" min={1} max={session.candles.length} value={idx}
                onChange={(e) => setIdx(Number(e.target.value))}
                className="flex-1 min-w-32 accent-cyan-400" />
              <span className="text-[11px] font-mono text-terminal-muted w-24 text-right">
                {idx}/{session.candles.length} · {cur ? new Date((cur.time + IST) * 1000).toISOString().slice(11, 16) : "—"}
              </span>
            </div>
          </section>

          <div className="grid sm:grid-cols-2 gap-4">
            <section className="panel">
              <div className="panel-title">AI Decision at Cursor</div>
              {!lastMarker ? (
                <p className="text-sm text-terminal-muted">Step forward — first decision lands 15 minutes in.</p>
              ) : (
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div><div className="stat-label">Decision</div>
                    <div className={`stat-value font-bold ${lastMarker.decision === "BULLISH" ? "text-terminal-bull" : lastMarker.decision === "BEARISH" ? "text-terminal-bear" : "text-terminal-muted"}`}>
                      {lastMarker.decision}</div></div>
                  <div><div className="stat-label">Score</div><div className="stat-value">{lastMarker.score}</div></div>
                  <div><div className="stat-label">Trend / ADX</div><div className="stat-value">{lastMarker.trend} / {lastMarker.adx}</div></div>
                  <div><div className="stat-label">MTF Alignment</div><div className="stat-value">{lastMarker.alignment}%</div></div>
                  <div><div className="stat-label">Structure</div><div className="stat-value">{lastMarker.structure_event ?? "—"}</div></div>
                  <div><div className="stat-label">Momentum</div><div className="stat-value">{lastMarker.momentum}%</div></div>
                </div>
              )}
            </section>
            <section className="panel">
              <div className="panel-title">Option Chain Memory at Cursor</div>
              {!lastMemory ? (
                <p className="text-sm text-terminal-muted">{session.note}</p>
              ) : (
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div><div className="stat-label">PCR</div><div className="stat-value">{lastMemory.pcr ?? "—"}</div></div>
                  <div><div className="stat-label">Max Pain</div><div className="stat-value">{lastMemory.max_pain ?? "—"}</div></div>
                  <div><div className="stat-label">Call OI</div><div className="stat-value">{lastMemory.call_oi?.toLocaleString?.("en-IN") ?? "—"}</div></div>
                  <div><div className="stat-label">Put OI</div><div className="stat-value">{lastMemory.put_oi?.toLocaleString?.("en-IN") ?? "—"}</div></div>
                  <div><div className="stat-label">ATM IV</div><div className="stat-value">{lastMemory.atm_iv != null ? `${(lastMemory.atm_iv * 100).toFixed(1)}%` : "—"}</div></div>
                  <div><div className="stat-label">Snapshot</div><div className="stat-value">{String(lastMemory.ts).slice(11, 16)}</div></div>
                </div>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
