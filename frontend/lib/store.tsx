"use client";
// Global market store fed by the WebSocket. One socket per browser tab.

import React, {
  createContext, useContext, useEffect, useRef, useState, useCallback,
} from "react";
import type {
  Alert, Analytics, ChainRow, Decision, GreekLeg, Layers, LifecycleState, Risk,
  ScanRow, Signal, SmartMoney, Spot, Status, StrikeReco, Warning,
} from "./types";
import { api } from "./api";

interface Store {
  status: Status | null;
  spot: Spot | null;
  analytics: Analytics;
  greeks: { ce?: GreekLeg; pe?: GreekLeg };
  smartMoney: SmartMoney | null;
  signal: Signal | null;
  risk: Risk | null;
  chain: ChainRow[];
  atm: number | null;
  layers: Layers;
  strike: StrikeReco | null;
  warning: Warning | null;
  narrative: string[];
  lifecycle: LifecycleState | null;
  alerts: Alert[];
  scanRows: ScanRow[];
  strikes: StrikeReco[];
  coach: string[];
  decision: Decision | null;
  scalp: any | null;
  exitIntel: any | null;
  killSwitch: any | null;
  safeMode: any | null;
  wsOk: boolean;
  lastError: string;
  refreshStatus: () => Promise<void>;
}

const Ctx = createContext<Store | null>(null);

export function MarketProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [spot, setSpot] = useState<Spot | null>(null);
  const [analytics, setAnalytics] = useState<Analytics>({});
  const [greeks, setGreeks] = useState<Store["greeks"]>({});
  const [smartMoney, setSmartMoney] = useState<SmartMoney | null>(null);
  const [signal, setSignal] = useState<Signal | null>(null);
  const [risk, setRisk] = useState<Risk | null>(null);
  const [chain, setChain] = useState<ChainRow[]>([]);
  const [atm, setAtm] = useState<number | null>(null);
  const [layers, setLayers] = useState<Layers>({});
  const [strike, setStrike] = useState<StrikeReco | null>(null);
  const [warning, setWarning] = useState<Warning | null>(null);
  const [narrative, setNarrative] = useState<string[]>([]);
  const [lifecycle, setLifecycle] = useState<LifecycleState | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [scanRows, setScanRows] = useState<ScanRow[]>([]);
  const [strikes, setStrikes] = useState<StrikeReco[]>([]);
  const [coach, setCoach] = useState<string[]>([]);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [scalp, setScalp] = useState<any | null>(null);
  const [exitIntel, setExitIntel] = useState<any | null>(null);
  const [killSwitch, setKillSwitch] = useState<any | null>(null);
  const [safeMode, setSafeMode] = useState<any | null>(null);
  const [wsOk, setWsOk] = useState(false);
  const [lastError, setLastError] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      const s = await api.status();
      setStatus(s);
      if (s.kill_switch) setKillSwitch(s.kill_switch);
      if (s.safe_mode) setSafeMode(s.safe_mode);
      if (s.connected) {
        const o = await api.overview();
        setSpot(o.spot?.ltp ? o.spot : null);
        setAnalytics(o.analytics || {});
        setGreeks(o.greeks || {});
        setSmartMoney(o.smart_money || null);
        setSignal(o.signal?.signal ? o.signal : null);
        setRisk(o.risk?.risk_level ? o.risk : null);
        const x = await api.intelligence().catch(() => null);
        if (x?.layers) {
          setLayers(x.layers);
          setStrike(x.strike ?? null);
          setWarning(x.warning ?? null);
          setNarrative(x.narrative ?? []);
          setStrikes(x.strikes ?? []);
          setCoach(x.coach ?? []);
          if (x.decision) setDecision(x.decision);
          if (x.lifecycle) setLifecycle(x.lifecycle);
        }
        if (o.decision?.action) setDecision(o.decision);
        const [al, sc] = await Promise.all([
          api.alerts().catch(() => []), api.scanner().catch(() => []),
        ]);
        setAlerts(al);
        setScanRows(sc);
      }
    } catch {}
  }, []);

  useEffect(() => {
    let stop = false;
    let retry: ReturnType<typeof setTimeout>;

    function open() {
      if (stop) return;
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const url =
        process.env.NEXT_PUBLIC_WS_URL || `${proto}://${location.hostname}:8000/ws`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setWsOk(true);
      ws.onclose = () => {
        setWsOk(false);
        retry = setTimeout(open, 3000);
      };
      ws.onmessage = (ev) => {
        try {
          const { channel, data } = JSON.parse(ev.data);
          if (channel === "status") setStatus(data);
          else if (channel === "reset") {
            // HARD symbol isolation — wipe every analysis slice on switch so no
            // prior symbol's values linger while the new symbol loads.
            setSpot(null); setAnalytics({}); setGreeks({}); setSmartMoney(null);
            setChain([]); setAtm(null); setLayers({}); setStrike(null);
            setWarning(null); setNarrative([]); setStrikes([]); setCoach([]);
            setSignal(null); setRisk(null); setLifecycle(null); setDecision(null);
            setScalp(null); setExitIntel(null);
          } else if (channel === "spot") {
            setSpot(data);
            setLastError(""); // data flowing again — clear stale banner
          } else if (channel === "analytics") {
            setAnalytics(data.analytics || {});
            setGreeks(data.greeks || {});
            setSmartMoney(data.smart_money || null);
            setChain(data.option_chain?.chain || []);
            setAtm(data.option_chain?.atm ?? null);
          } else if (channel === "signal") {
            setSignal(data.signal);
            setRisk(data.risk);
            if (data.layers) setLayers(data.layers);
            setStrike(data.strike ?? null);
            setWarning(data.warning ?? null);
            setNarrative(data.narrative ?? []);
            setStrikes(data.strikes ?? []);
            setCoach(data.coach ?? []);
            if (data.decision) setDecision(data.decision);
            if (data.exit_intel) setExitIntel(data.exit_intel);
            if (data.kill_switch) setKillSwitch(data.kill_switch);
            if (data.safe_mode) setSafeMode(data.safe_mode);
            if (data.lifecycle) setLifecycle(data.lifecycle);
          } else if (channel === "lifecycle") {
            setLifecycle(data);
          } else if (channel === "alert") {
            setAlerts((prev) => [data, ...prev].slice(0, 100));
            if (typeof Notification !== "undefined" && Notification.permission === "granted") {
              new Notification(data.title, { body: data.body });
            }
          } else if (channel === "scanner") {
            setScanRows(data || []);
          } else if (channel === "scalp") {
            setScalp(data || null);
          } else if (channel === "scalp_mgmt") {
            setScalp((prev: any) => (prev ? { ...prev, management: data } : prev));
          } else if (channel === "error") {
            setLastError(data.message || "");
          }
        } catch {}
      };
    }

    open();
    refreshStatus();
    const ping = setInterval(() => wsRef.current?.readyState === 1 && wsRef.current.send("ping"), 25000);
    return () => {
      stop = true;
      clearTimeout(retry);
      clearInterval(ping);
      wsRef.current?.close();
    };
  }, [refreshStatus]);

  return (
    <Ctx.Provider
      value={{ status, spot, analytics, greeks, smartMoney, signal, risk, chain, atm, layers, strike, warning, narrative, lifecycle, alerts, scanRows, strikes, coach, decision, scalp, exitIntel, killSwitch, safeMode, wsOk, lastError, refreshStatus }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useMarket(): Store {
  const v = useContext(Ctx);
  if (!v) throw new Error("useMarket outside MarketProvider");
  return v;
}
