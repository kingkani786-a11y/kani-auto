"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { JournalEntry } from "@/lib/types";

const EMPTY = { market: "", signal: "", entry: "", exit: "", stop_loss: "", target: "", pnl: "", confidence: "", notes: "", reason: "", grade: "", screenshot: "" };

export default function JournalPage() {
  const [rows, setRows] = useState<JournalEntry[]>([]);
  const [form, setForm] = useState<Record<string, string>>(EMPTY);
  const [busy, setBusy] = useState(false);

  const load = () => api.journal().then(setRows).catch(() => {});
  useEffect(() => { load(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const num = (v: string) => (v === "" ? null : Number(v));
      await api.addJournal({
        market: form.market, signal: form.signal, notes: form.notes,
        reason: form.reason, grade: form.grade, screenshot: form.screenshot,
        entry: num(form.entry), exit: num(form.exit), stop_loss: num(form.stop_loss),
        target: num(form.target), pnl: num(form.pnl), confidence: num(form.confidence),
      });
      setForm(EMPTY);
      await load();
    } finally {
      setBusy(false);
    }
  }

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  const input = (k: string, ph: string, type = "text", required = false) => (
    <input
      key={k} value={form[k]} onChange={set(k)} placeholder={ph} type={type} required={required}
      step="any"
      className="bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm font-mono focus:border-terminal-accent outline-none"
    />
  );

  const totalPnl = rows.reduce((a, r) => a + (Number(r.pnl) || 0), 0);

  return (
    <div className="space-y-4">
      <section className="panel">
        <div className="panel-title">Add Trade</div>
        <form onSubmit={submit} className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {input("market", "Market (e.g. NIFTY)", "text", true)}
          {input("signal", "Signal (e.g. BUY CE)", "text", true)}
          {input("entry", "Entry", "number")}
          {input("exit", "Exit", "number")}
          {input("stop_loss", "Stop Loss", "number")}
          {input("target", "Target", "number")}
          {input("pnl", "P/L", "number")}
          {input("confidence", "Confidence %", "number")}
          {input("reason", "Reason for trade")}
          <select value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value })}
            className="bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm font-mono focus:border-terminal-accent outline-none">
            <option value="">Grade…</option>
            <option value="A">A Grade</option>
            <option value="B">B Grade</option>
            <option value="C">C Grade</option>
          </select>
          {input("screenshot", "Screenshot URL")}
          <input
            value={form.notes} onChange={set("notes")} placeholder="Notes"
            className="col-span-2 sm:col-span-3 bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm focus:border-terminal-accent outline-none"
          />
          <button disabled={busy} className="rounded-lg bg-terminal-accent text-black font-bold text-sm py-2 disabled:opacity-50">
            {busy ? "SAVING…" : "ADD ENTRY"}
          </button>
        </form>
      </section>

      <section className="panel overflow-x-auto">
        <div className="panel-title flex justify-between">
          <span>Trade Journal ({rows.length})</span>
          <span className={totalPnl >= 0 ? "text-terminal-bull" : "text-terminal-bear"}>
            Net P/L: {totalPnl.toLocaleString("en-IN")}
          </span>
        </div>
        {rows.length === 0 ? (
          <p className="text-sm text-terminal-muted">No trades recorded yet.</p>
        ) : (
          <table className="w-full text-xs font-mono whitespace-nowrap">
            <thead>
              <tr className="stat-label text-left">
                {["Date", "Time", "Market", "Signal", "Entry", "Exit", "SL", "Target", "P/L", "Conf%"].map((h) => (
                  <th key={h} className="pb-2 pr-3 font-normal">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t border-terminal-border/40">
                  <td className="py-1.5 pr-3">{r.date}</td>
                  <td className="pr-3">{r.time}</td>
                  <td className="pr-3">{r.market}</td>
                  <td className="pr-3">{r.signal}</td>
                  <td className="pr-3">{r.entry ?? "—"}</td>
                  <td className="pr-3">{r.exit ?? "—"}</td>
                  <td className="pr-3">{r.stop_loss ?? "—"}</td>
                  <td className="pr-3">{r.target ?? "—"}</td>
                  <td className={`pr-3 ${(Number(r.pnl) || 0) >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
                    {r.pnl ?? "—"}
                  </td>
                  <td>{r.confidence ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
