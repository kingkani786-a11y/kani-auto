"use client";
// ProChart — native candlestick chart rendered from OUR broker data via
// lightweight-charts. No TradingView embed, no fallback chart: the chart is
// strictly bound to the selected symbol; on symbol/timeframe change the old
// chart data is replaced atomically and the instance is destroyed on unmount.

import { useCallback, useEffect, useRef, useState } from "react";
import {
  createChart, ColorType, CrosshairMode, IChartApi, ISeriesApi,
  IPriceLine, LineStyle, UTCTimestamp,
} from "lightweight-charts";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";

export interface Candle {
  time: number; open: number; high: number; low: number; close: number; volume?: number;
}

export interface TradeLines {
  entry?: number | null;
  stop?: number | null;
  targets?: (number | null | undefined)[];
}

// Phase B — institutional / strike zones drawn directly on the chart
export interface ChartZone {
  price: number;
  title: string;
  color: string;
  dashed?: boolean;
}

const IST_OFFSET = 19800; // lightweight-charts renders UTC; shift to IST
const TF_SECONDS: Record<string, number> = {
  "1s": 1, "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
  "1H": 3600, "4H": 14400, "1D": 86400,
};

// client-side cache: instant symbol/timeframe switching
const cache = new Map<string, { ts: number; data: Candle[] }>();

async function fetchCandles(symbol: string, tf: string): Promise<Candle[]> {
  const key = `${symbol}:${tf}`;
  const hit = cache.get(key);
  if (hit && Date.now() - hit.ts < 20000) return hit.data;
  let lastErr: Error = new Error("No Data Available");
  for (let attempt = 0; attempt < 3; attempt++) {       // retry transient failures
    try {
      const data = await api.candlesTf(tf, symbol) as Candle[];
      if (!Array.isArray(data) || data.length === 0) throw new Error("No Data Available");
      cache.set(key, { ts: Date.now(), data });
      return data;
    } catch (e: any) {
      lastErr = e;
      const msg = String(e.message || "");
      // hard stops: invalid input, empty history, or broker cooldown —
      // retrying would be pointless (or actively harmful for rate limits)
      if (msg === "Invalid Symbol" || msg === "No Data Available" ||
          msg.toLowerCase().includes("rate limit") || msg.toLowerCase().includes("cooldown")) {
        throw e;
      }
      await new Promise((r) => setTimeout(r, 500 * (attempt + 1)));
    }
  }
  throw lastErr;
}

export function ProChart({
  symbol, tvLabel, tf, lines, zones, projection, noTradeZone, onCandles,
}: {
  symbol: string;
  tvLabel: string;          // strict display mapping, e.g. NSE:NIFTY
  tf: string;
  lines: TradeLines;
  zones?: ChartZone[];
  projection?: any;         // candle_projection (cone + paths) for chart overlay
  noTradeZone?: boolean;
  onCandles?: (c: Candle[]) => void;
}) {
  const holderRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const priceLinesRef = useRef<IPriceLine[]>([]);
  const projSeriesRef = useRef<any[]>([]);              // Phase B.1 projected series
  const lastCandleRef = useRef<Candle | null>(null);
  const boundRef = useRef("");                          // symbol:tf the series holds
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { spot } = useMarket();

  // ---- create chart once; destroy on unmount ----
  useEffect(() => {
    const el = holderRef.current;
    if (!el) return;
    const chart = createChart(el, {
      layout: {
        background: { type: ColorType.Solid, color: "#11161f" },
        textColor: "#8b96a8",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(29,37,51,0.5)" },
        horzLines: { color: "rgba(29,37,51,0.5)" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#1d2533" },
      timeScale: { borderColor: "#1d2533", timeVisible: true, secondsVisible: false },
      autoSize: true,
    });
    const series = chart.addCandlestickSeries({
      upColor: "#16c784", downColor: "#ea3943",
      wickUpColor: "#16c784", wickDownColor: "#ea3943",
      borderVisible: false,
    });
    const vol = chart.addHistogramSeries({
      priceScaleId: "vol", priceFormat: { type: "volume" },
    });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    chartRef.current = chart;
    seriesRef.current = series;
    volRef.current = vol;
    return () => {                                     // full destroy — never reused
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      volRef.current = null;
    };
  }, []);

  // ---- load data when symbol/timeframe changes (atomic rebind) ----
  const load = useCallback(async (silent = false) => {
    if (!seriesRef.current) return;
    const want = `${symbol}:${tf}`;
    if (!silent) { setLoading(true); setError(""); }
    try {
      const candles = await fetchCandles(symbol, tf);
      if (`${symbol}:${tf}` !== want || !seriesRef.current) return; // raced — drop
      seriesRef.current.setData(candles.map((c) => ({
        time: (c.time + IST_OFFSET) as UTCTimestamp,
        open: c.open, high: c.high, low: c.low, close: c.close,
      })));
      volRef.current?.setData(candles.map((c) => ({
        time: (c.time + IST_OFFSET) as UTCTimestamp,
        value: c.volume || 0,
        color: c.close >= c.open ? "rgba(22,199,132,0.35)" : "rgba(234,57,67,0.35)",
      })));
      lastCandleRef.current = candles[candles.length - 1];
      boundRef.current = want;
      chartRef.current?.timeScale().scrollToRealTime();
      onCandles?.(candles);
      setError("");
    } catch (e: any) {
      if (`${symbol}:${tf}` !== want) return;
      seriesRef.current?.setData([]);                  // never show a stale/wrong chart
      volRef.current?.setData([]);
      boundRef.current = "";
      setError(e.message || "Chart failed to load");
    } finally {
      if (`${symbol}:${tf}` === want) setLoading(false);
    }
  }, [symbol, tf, onCandles]);

  useEffect(() => {
    load();
    const t = setInterval(() => load(true), 30000);    // background refresh
    return () => clearInterval(t);
  }, [load]);

  // ---- live tick: extend/update the current candle from the spot feed ----
  useEffect(() => {
    const s = seriesRef.current;
    const last = lastCandleRef.current;
    if (!s || !last || !spot?.ltp || spot.symbol !== symbol) return;
    if (boundRef.current !== `${symbol}:${tf}`) return; // series holds another symbol
    const step = TF_SECONDS[tf] ?? 60;
    const bucket = Math.floor(spot.ts / step) * step;
    const px = spot.ltp;
    if (bucket > last.time) {
      const fresh = { time: bucket, open: px, high: px, low: px, close: px, volume: 0 };
      lastCandleRef.current = fresh;
      s.update({ time: (bucket + IST_OFFSET) as UTCTimestamp, open: px, high: px, low: px, close: px });
    } else {
      last.high = Math.max(last.high, px);
      last.low = Math.min(last.low, px);
      last.close = px;
      s.update({
        time: (last.time + IST_OFFSET) as UTCTimestamp,
        open: last.open, high: last.high, low: last.low, close: last.close,
      });
    }
  }, [spot, symbol, tf]);

  // ---- trade overlay: entry / SL / target price lines ----
  useEffect(() => {
    const s = seriesRef.current;
    if (!s) return;
    priceLinesRef.current.forEach((l) => s.removePriceLine(l));
    priceLinesRef.current = [];
    if (error || boundRef.current !== `${symbol}:${tf}`) return;
    const mk = (price: number, color: string, title: string, style = LineStyle.Dashed) =>
      priceLinesRef.current.push(
        s.createPriceLine({ price, color, lineWidth: 1, lineStyle: style, axisLabelVisible: true, title }));
    if (lines.entry) mk(lines.entry, "#22d3ee", "ENTRY", LineStyle.Solid);
    if (lines.stop) mk(lines.stop, "#ea3943", "SL");
    (lines.targets || []).forEach((t, i) => { if (t) mk(t, "#16c784", `T${i + 1}`); });
    // Phase B — institutional / strike zones (VWAP, gamma wall, value area, strikes)
    (zones || []).forEach((z) => { if (z.price) mk(z.price, z.color, z.title,
      z.dashed ? LineStyle.Dotted : LineStyle.Dashed); });
  }, [lines, zones, error, symbol, tf]);

  // ---- Phase B.1: projected cone + expected/failure paths into the future ----
  useEffect(() => {
    const chart = chartRef.current;
    projSeriesRef.current.forEach((s) => { try { chart?.removeSeries(s); } catch {} });
    projSeriesRef.current = [];
    if (!chart || error || boundRef.current !== `${symbol}:${tf}`) return;
    const base = lastCandleRef.current?.time;
    const step = TF_SECONDS[tf] || 300;
    if (!base || !projection?.ready || !projection.cone?.length) return;
    try {
      const t = (i: number) => (base + i * step + IST_OFFSET) as UTCTimestamp;
      const spot = projection.spot;
      const cone = projection.cone, cand = projection.candles || [];
      const series = (color: string, width: number, style: LineStyle) =>
        chart.addLineSeries({ color, lineWidth: width as any, lineStyle: style,
          lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false });
      const mkLine = (color: string, width: number, style: LineStyle,
                      pts: { t: number; v: number }[]) => {
        const s = series(color, width, style);
        s.setData(pts.map((p) => ({ time: t(p.t), value: p.v })));
        projSeriesRef.current.push(s);
      };
      // expected path (green), upper/lower cone bounds (faint), failure (red)
      mkLine("#16c784", 2, LineStyle.Solid,
        [{ t: 0, v: spot }, ...cone.map((c: any) => ({ t: c.i, v: c.mid }))]);
      mkLine("#3b82f6", 1, LineStyle.Dotted,
        [{ t: 0, v: spot }, ...cone.map((c: any) => ({ t: c.i, v: c.upper }))]);
      mkLine("#3b82f6", 1, LineStyle.Dotted,
        [{ t: 0, v: spot }, ...cone.map((c: any) => ({ t: c.i, v: c.lower }))]);
      mkLine("#ea3943", 1, LineStyle.Dashed,
        [{ t: 0, v: spot }, ...cand.map((c: any) => ({ t: c.i, v: c.failure_close }))]);
    } catch { /* never break the chart */ }
  }, [projection, error, symbol, tf]);

  return (
    <div className="relative h-[380px] sm:h-[480px]">
      <div ref={holderRef} className="absolute inset-0" />
      {/* symbol watermark — always shows exactly what the chart is bound to */}
      <div className="absolute top-2 left-3 z-10 text-[11px] font-mono text-terminal-muted pointer-events-none">
        {tvLabel} · {tf}
      </div>
      {noTradeZone && !loading && !error && (
        <div className="absolute top-2 right-16 z-10 px-2 py-0.5 rounded bg-terminal-warn/15 border border-terminal-warn/40 text-terminal-warn text-[10px] font-mono pointer-events-none">
          NO TRADE ZONE
        </div>
      )}
      {loading && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-terminal-panel/70">
          <div className="w-8 h-8 border-2 border-terminal-border border-t-terminal-accent rounded-full animate-spin" />
        </div>
      )}
      {!loading && error && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-2 bg-terminal-panel/85">
          <div className="text-sm text-terminal-bear font-mono">
            {error === "Invalid Symbol" ? "Invalid Symbol" : error === "No Data Available" ? "No Data Available" : error}
          </div>
          <button onClick={() => load()}
            className="px-3 py-1.5 rounded border border-terminal-border text-xs hover:border-terminal-accent">
            RETRY
          </button>
        </div>
      )}
    </div>
  );
}
