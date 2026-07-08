"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";

interface SearchHit { symbol: string; name: string; security_id: number; exchange: string }

export default function StocksPage() {
  const router = useRouter();
  const { status } = useMarket();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [favorites, setFavorites] = useState<string[]>([]);
  const [quotes, setQuotes] = useState<Record<string, { ltp: number; change_pct: number }>>({});
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const debounce = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const load = useCallback(async () => {
    try {
      const r = await api.watchlist();
      setWatchlist(r.watchlist);
      setFavorites(r.favorites);
      setQuotes(r.quotes || {});
    } catch {}
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [load]);

  function onSearch(v: string) {
    setQ(v);
    clearTimeout(debounce.current);
    if (v.trim().length < 2) {
      setHits([]);
      return;
    }
    debounce.current = setTimeout(async () => {
      try {
        setHits(await api.stockSearch(v));
        setMsg("");
      } catch (e: any) {
        setMsg(e.message);
      }
    }, 300);
  }

  async function add(h: SearchHit) {
    setBusy(true);
    try {
      await api.watchlistAdd({ symbol: h.symbol, security_id: h.security_id, exchange: h.exchange });
      setHits([]);
      setQ("");
      await load();
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function analyze(symbol: string) {
    setBusy(true);
    try {
      await api.setSymbol(symbol);
      router.push("/");
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setBusy(false);
    }
  }

  const sorted = [...watchlist].sort((a, b) =>
    Number(favorites.includes(b)) - Number(favorites.includes(a)) || a.localeCompare(b));

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <section className="panel">
        <div className="panel-title">Stock Dashboard — Search Any NSE / BSE Symbol</div>
        <input
          value={q}
          onChange={(e) => onSearch(e.target.value)}
          placeholder={status?.connected ? "Search NIFTY 500, any NSE or BSE stock… (e.g. RELIANCE)" : "Connect in Settings first"}
          disabled={!status?.connected}
          className="w-full bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2.5 text-sm font-mono focus:border-terminal-accent outline-none disabled:opacity-50"
        />
        {msg && <div className="mt-2 text-xs text-terminal-bear">{msg}</div>}
        {hits.length > 0 && (
          <div className="mt-2 border border-terminal-border rounded-lg divide-y divide-terminal-border/50 max-h-72 overflow-y-auto">
            {hits.map((h) => (
              <button
                key={`${h.exchange}-${h.security_id}`}
                onClick={() => add(h)}
                disabled={busy}
                className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-terminal-bg"
              >
                <span className="font-mono text-sm">{h.symbol}
                  <span className="ml-2 text-[10px] text-terminal-muted">{h.exchange}</span>
                </span>
                <span className="text-xs text-terminal-muted truncate ml-3">{h.name}</span>
                <span className="text-terminal-accent text-xs ml-3 shrink-0">+ Watchlist</span>
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-title">Watchlist ({watchlist.length}) — ★ favorites first</div>
        {watchlist.length === 0 ? (
          <p className="text-sm text-terminal-muted">Search above to add stocks. The scanner and Watchlist AI monitor everything here every minute.</p>
        ) : (
          <div className="divide-y divide-terminal-border/40">
            {sorted.map((s) => {
              const qd = quotes[s];
              const fav = favorites.includes(s);
              return (
                <div key={s} className="flex items-center gap-2 py-2">
                  <button onClick={() => api.favoriteToggle(s).then(load)}
                    className={`text-lg leading-none ${fav ? "text-terminal-warn" : "text-terminal-border"}`}
                    title="Toggle favorite">★</button>
                  <span className="font-mono text-sm w-28 truncate">{s}</span>
                  <span className="font-mono text-sm ml-auto">{qd ? qd.ltp.toLocaleString("en-IN") : "—"}</span>
                  <span className={`font-mono text-xs w-16 text-right ${(qd?.change_pct ?? 0) >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
                    {qd ? `${qd.change_pct >= 0 ? "+" : ""}${qd.change_pct}%` : ""}
                  </span>
                  <button onClick={() => analyze(s)} disabled={busy || !status?.connected}
                    className="px-2.5 py-1 rounded border border-terminal-accent/50 text-terminal-accent text-[11px] hover:bg-terminal-accent hover:text-black disabled:opacity-40">
                    ANALYZE
                  </button>
                  <button onClick={() => api.watchlistRemove(s).then(load)}
                    className="px-2 py-1 rounded border border-terminal-border text-terminal-muted text-[11px] hover:border-terminal-bear hover:text-terminal-bear">
                    ✕
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
