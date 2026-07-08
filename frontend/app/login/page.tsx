"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";
import { friendlyMessage } from "@/lib/status";

export default function LoginPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // if the backend has no password configured, skip the gate entirely
    api.authCheck().then((r) => {
      if (!r.login_required) router.replace("/");
    }).catch(() => {});
  }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const r = await api.login(password);
      setToken(r.token || "");
      router.replace("/");
    } catch (err: any) {
      setError(friendlyMessage(err.message) || "Incorrect password");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto mt-24 panel">
      <div className="text-center mb-5">
        <div className="font-bold text-lg">
          <span className="text-terminal-accent">CLOUD</span> AI TRADER
        </div>
        <div className="text-xs text-terminal-muted mt-1">Secure access — works across all your devices</div>
      </div>
      <form onSubmit={submit} className="space-y-4">
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoFocus
          placeholder="Workstation password"
          className="w-full bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2.5 text-sm focus:border-terminal-accent outline-none"
        />
        <button
          disabled={busy}
          className="w-full py-2.5 rounded-lg bg-terminal-accent text-black font-bold text-sm disabled:opacity-50"
        >
          {busy ? "CHECKING…" : "UNLOCK"}
        </button>
      </form>
      {error && <div className="mt-3 text-sm text-terminal-bear text-center">✕ {error}</div>}
    </div>
  );
}
