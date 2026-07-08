"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";
import { friendlyMessage } from "@/lib/status";

export default function SettingsPage() {
  const router = useRouter();
  const { status, refreshStatus } = useMarket();
  const [clientId, setClientId] = useState("");
  const [token, setToken] = useState("");
  const [tokenTail, setTokenTail] = useState("");
  const [threshold, setThreshold] = useState(65);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    api.getSettings().then((s) => {
      setClientId(s.client_id || "");
      setTokenTail(s.token_tail || "");
      setThreshold(s.confidence_threshold ?? 65);
    }).catch(() => {});
  }, []);

  async function saveConnect(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      // Validates token -> tears down any old session -> starts all engines.
      const res = await api.connect(clientId.trim(), token.trim());
      await refreshStatus();
      // Success even if market closed / data subscription missing — show the
      // server's friendly status, never an error.
      setMsg({ ok: true, text: res?.message || "Connected. Market engines are running." });
      setToken("");
      setTimeout(() => router.push("/"), 900);
    } catch (err: any) {
      setMsg({ ok: false, text: friendlyMessage(err.message) || "Connection failed" });
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    try {
      await api.disconnect();
      await refreshStatus();
      setMsg({ ok: true, text: "Disconnected. All engines stopped." });
    } finally {
      setBusy(false);
    }
  }

  async function saveThreshold() {
    try {
      await api.setThreshold(threshold);
      setMsg({ ok: true, text: `Signal threshold set to ${threshold}%` });
    } catch (err: any) {
      setMsg({ ok: false, text: friendlyMessage(err.message) });
    }
  }

  return (
    <div className="max-w-lg mx-auto space-y-4">
      <section className="panel">
        <div className="panel-title">Broker Credentials</div>
        <p className="text-xs text-terminal-muted mb-4">
          Only Client ID and Access Token are required — no API secret, password or OTP.
          The token rotates daily; paste the new one here any time and reconnect happens
          automatically, no restart needed. The token is held in server memory only and
          is never written to the database.
        </p>
        <form onSubmit={saveConnect} className="space-y-4">
          <div>
            <label className="stat-label block mb-1.5">Client ID</label>
            <input
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              required
              minLength={3}
              autoComplete="off"
              className="w-full bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2.5 text-sm font-mono focus:border-terminal-accent outline-none"
              placeholder="e.g. 1100012345"
            />
          </div>
          <div>
            <label className="stat-label block mb-1.5">
              Access Token {tokenTail && <span className="normal-case">— current ends in …{tokenTail}</span>}
            </label>
            <textarea
              value={token}
              onChange={(e) => setToken(e.target.value)}
              required
              minLength={20}
              rows={4}
              autoComplete="off"
              className="w-full bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2.5 text-xs font-mono focus:border-terminal-accent outline-none resize-none"
              placeholder="Paste today's access token"
            />
          </div>
          <button
            type="submit"
            disabled={busy}
            className="w-full py-3 rounded-lg bg-terminal-accent text-black font-bold text-sm tracking-wide disabled:opacity-50"
          >
            {busy ? "VALIDATING…" : "SAVE & CONNECT"}
          </button>
        </form>
        {status?.connected && (
          <button
            onClick={disconnect}
            disabled={busy}
            className="w-full mt-3 py-2.5 rounded-lg border border-terminal-bear/50 text-terminal-bear text-sm font-semibold"
          >
            DISCONNECT
          </button>
        )}
        {msg && (
          <div className={`mt-4 text-sm ${msg.ok ? "text-terminal-bull" : "text-terminal-bear"}`}>
            {msg.ok ? "✓" : "✕"} {msg.text}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-title">Signal Engine</div>
        <label className="stat-label block mb-2">
          Confidence threshold — {threshold}%
        </label>
        <input
          type="range"
          min={50}
          max={95}
          value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))}
          className="w-full accent-cyan-400"
        />
        <p className="text-xs text-terminal-muted mt-1 mb-3">
          Signals fire only when the weighted composite score exceeds this value.
        </p>
        <button
          onClick={saveThreshold}
          className="px-4 py-2 rounded-lg border border-terminal-border text-sm hover:border-terminal-accent"
        >
          Save Threshold
        </button>
      </section>
    </div>
  );
}
