"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";

const KIND_TONE: Record<string, string> = {
  ENTRY: "text-terminal-bull", TARGET: "text-terminal-bull", ARMED: "text-terminal-accent",
  SL: "text-terminal-bear", SETUP: "text-terminal-warn", SCANNER: "text-terminal-warn",
  SYSTEM: "text-terminal-muted",
};

export default function ScannerPage() {
  const router = useRouter();
  const { scanRows, alerts, status } = useMarket();
  const [tg, setTg] = useState({ telegram_bot_token: "", telegram_chat_id: "" });
  const [cfgMsg, setCfgMsg] = useState("");
  const [breadth, setBreadth] = useState<any>(null);
  const [learning, setLearning] = useState<any>(null);

  useEffect(() => {
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission();
    }
    const load = () => {
      api.breadth().then(setBreadth).catch(() => {});
      api.learning().then(setLearning).catch(() => {});
    };
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  async function saveTg() {
    try {
      const r = await api.alertsConfig(tg);
      setCfgMsg(r.telegram_enabled ? "✓ Telegram alerts enabled" : "Telegram cleared");
    } catch (e: any) {
      setCfgMsg(e.message);
    }
  }

  async function analyze(symbol: string) {
    try {
      await api.setSymbol(symbol);
      router.push("/");
    } catch {}
  }

  return (
    <div className="space-y-4">
      {(breadth || learning) && (
        <div className="grid sm:grid-cols-2 gap-4">
          {breadth && (
            <section className="panel py-3">
              <div className="panel-title">Market Breadth (scanned universe: {breadth.universe ?? 0})</div>
              <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-sm font-mono">
                <span><span className="stat-label mr-1">ADV</span><span className="text-terminal-bull">{breadth.advances}</span></span>
                <span><span className="stat-label mr-1">DEC</span><span className="text-terminal-bear">{breadth.declines}</span></span>
                <span><span className="stat-label mr-1">A/D</span>{breadth.ratio ?? "—"}</span>
                <span><span className="stat-label mr-1">NEW HI</span><span className="text-terminal-bull">{breadth.new_highs}</span></span>
                <span><span className="stat-label mr-1">NEW LO</span><span className="text-terminal-bear">{breadth.new_lows}</span></span>
                <span className={breadth.bias === "BULLISH" ? "text-terminal-bull font-bold" : breadth.bias === "BEARISH" ? "text-terminal-bear font-bold" : "text-terminal-muted"}>
                  {breadth.bias ?? ""}
                </span>
              </div>
            </section>
          )}
          {learning && (
            <section className="panel py-3">
              <div className="panel-title">Self-Learning Memory ({learning.samples} outcomes)</div>
              {learning.samples === 0 ? (
                <p className="text-xs text-terminal-muted">Signal outcomes accumulate here and feed back into thresholds and grading.</p>
              ) : (
                <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-sm font-mono">
                  <span><span className="stat-label mr-1">OVERALL</span>{learning.overall_accuracy ?? "—"}%</span>
                  {Object.entries(learning.by_regime || {}).slice(0, 3).map(([r, v]: [string, any]) => (
                    <span key={r}><span className="stat-label mr-1">{r.replace(/_/g, " ")}</span>
                      <span className={v.accuracy >= 60 ? "text-terminal-bull" : "text-terminal-bear"}>{v.accuracy}%</span>
                      <span className="text-terminal-muted text-xs"> ({v.n})</span></span>
                  ))}
                </div>
              )}
            </section>
          )}
        </div>
      )}

      <section className="panel overflow-x-auto">
        <div className="panel-title">Trade Scanner — opportunity ranking, every 60s</div>
        {!status?.connected ? (
          <p className="text-sm text-terminal-muted">Connect in Settings to start scanning.</p>
        ) : scanRows.length === 0 ? (
          <p className="text-sm text-terminal-muted">First scanner pass lands within a minute of connecting.</p>
        ) : (
          <table className="w-full text-xs font-mono whitespace-nowrap">
            <thead>
              <tr className="stat-label text-left">
                {["Rank", "Symbol", "LTP", "Chg%", "Signals", "Prob", "Risk", "Exp. Reward", "Score", ""].map((h) => (
                  <th key={h} className="pb-2 pr-3 font-normal">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {scanRows.map((r, i) => (
                <tr key={r.symbol} className="border-t border-terminal-border/40">
                  <td className="py-1.5 pr-3 text-terminal-muted">#{i + 1}</td>
                  <td className="pr-3 font-bold">{r.symbol}</td>
                  <td className="pr-3">{r.ltp.toLocaleString("en-IN")}</td>
                  <td className={`pr-3 ${r.change_pct >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
                    {r.change_pct >= 0 ? "+" : ""}{r.change_pct}%
                  </td>
                  <td className="pr-3">
                    {r.breakout && <span className="text-terminal-bull mr-2">BREAKOUT</span>}
                    {r.breakdown && <span className="text-terminal-bear mr-2">BREAKDOWN</span>}
                    {r.volume_surge && <span className="text-terminal-warn mr-2">VOL SURGE</span>}
                    {Math.abs(r.oi_shift_pct) > 2 && (
                      <span className="text-terminal-accent">OI {r.oi_shift_pct >= 0 ? "+" : ""}{r.oi_shift_pct}%</span>
                    )}
                  </td>
                  <td className="pr-3">{(r as any).probability_pct ?? "—"}%</td>
                  <td className={`pr-3 ${((r as any).risk_score ?? 0) > 60 ? "text-terminal-bear" : ""}`}>{(r as any).risk_score ?? "—"}</td>
                  <td className="pr-3">{(r as any).expected_reward ?? "—"}</td>
                  <td className="pr-3">
                    <div className="flex items-center gap-1.5">
                      <div className="w-16 h-1.5 rounded bg-terminal-bg overflow-hidden">
                        <div className={r.bias === "BULL" ? "bg-terminal-bull h-full" : "bg-terminal-bear h-full"}
                          style={{ width: `${r.score}%` }} />
                      </div>
                      {r.score}
                    </div>
                  </td>
                  <td>
                    <button onClick={() => analyze(r.symbol)}
                      className="px-2 py-1 rounded border border-terminal-border text-[10px] hover:border-terminal-accent">
                      ANALYZE
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <div className="grid lg:grid-cols-2 gap-4">
        <section className="panel">
          <div className="panel-title">Alert Feed</div>
          {alerts.length === 0 ? (
            <p className="text-sm text-terminal-muted">Entry, target, SL, setup and scanner alerts appear here (and as browser notifications).</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {alerts.map((a) => (
                <div key={a.id} className="flex gap-2 text-xs border-t border-terminal-border/40 pt-2">
                  <span className={`font-bold shrink-0 w-16 ${KIND_TONE[a.kind] ?? ""}`}>{a.kind}</span>
                  <div>
                    <div className="font-semibold">{a.title}</div>
                    <div className="text-terminal-muted">{a.body}</div>
                  </div>
                  <span className="ml-auto text-terminal-muted shrink-0">{a.ts.slice(11, 16)}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-title">Telegram Alerts</div>
          <p className="text-xs text-terminal-muted mb-3">
            Create a bot with @BotFather, get your chat id from @userinfobot, and alerts mirror to Telegram.
          </p>
          <div className="space-y-2">
            <input value={tg.telegram_bot_token}
              onChange={(e) => setTg({ ...tg, telegram_bot_token: e.target.value })}
              placeholder="Bot token"
              className="w-full bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-xs font-mono focus:border-terminal-accent outline-none" />
            <input value={tg.telegram_chat_id}
              onChange={(e) => setTg({ ...tg, telegram_chat_id: e.target.value })}
              placeholder="Chat ID"
              className="w-full bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-xs font-mono focus:border-terminal-accent outline-none" />
            <div className="flex gap-2">
              <button onClick={saveTg}
                className="px-4 py-2 rounded-lg bg-terminal-accent text-black text-xs font-bold">SAVE</button>
              <button onClick={() => api.alertsTest().catch(() => {})}
                className="px-4 py-2 rounded-lg border border-terminal-border text-xs hover:border-terminal-accent">SEND TEST</button>
            </div>
            {cfgMsg && <div className="text-xs text-terminal-bull">{cfgMsg}</div>}
          </div>
        </section>
      </div>
    </div>
  );
}
