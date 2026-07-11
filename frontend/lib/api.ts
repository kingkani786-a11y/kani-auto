// REST client. All paths go through the Next.js rewrite to the FastAPI backend.
// When the backend has CAT_APP_PASSWORD set, every request carries the session
// token from localStorage; a 401 bounces the user to /login.

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("cat_token") || "";
}

export function setToken(t: string) {
  localStorage.setItem("cat_token", t);
}

// On the web, API calls are relative ("/api/...") and proxied by Next.js.
// In packaged apps (Capacitor/Electron) there is no proxy, so they call the
// hosted backend directly via NEXT_PUBLIC_API_BASE. Default "" keeps web
// behaviour identical — this is purely additive.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Auth-Token": getToken(),
      ...(init?.headers || {}),
    },
  });
  if (!r.ok) {
    let msg = `HTTP ${r.status}`;
    try {
      const j = await r.json();
      msg = j.detail || msg;
    } catch {}
    if (r.status === 401 && msg === "Login required" && typeof window !== "undefined"
        && location.pathname !== "/login") {
      location.href = "/login";
    }
    throw new Error(msg);
  }
  return r.json();
}

export const api = {
  status: () => req<any>("/api/status"),
  symbols: () => req<any[]>("/api/symbols"),
  connect: (client_id: string, access_token: string) =>
    req<any>("/api/settings/connect", {
      method: "POST",
      body: JSON.stringify({ client_id, access_token }),
    }),
  disconnect: () => req<any>("/api/settings/disconnect", { method: "POST" }),
  getSettings: () => req<any>("/api/settings"),
  setThreshold: (confidence_threshold: number) =>
    req<any>("/api/settings/threshold", {
      method: "PUT",
      body: JSON.stringify({ confidence_threshold }),
    }),
  setSymbol: (symbol: string) =>
    req<any>("/api/symbol", { method: "POST", body: JSON.stringify({ symbol }) }),
  overview: () => req<any>("/api/market/overview"),
  optionChain: () => req<any>("/api/market/optionchain"),
  candlesTf: (tf: string, symbol?: string) =>
    req<any[]>(`/api/market/candles/${tf}${symbol ? `?symbol=${encodeURIComponent(symbol)}` : ""}`),
  intelligence: () => req<any>("/api/intelligence"),
  lifecycle: () => req<any>("/api/lifecycle"),
  systemHealth: () => req<any>("/api/health/system"),
  moveAlerts: () => req<any>("/api/move-alerts"),
  briefing: () => req<any>("/api/briefing"),
  // AI Cortex (Proposal #013 Phase A — optional LLM layer)
  cortexStatus: () => req<any>("/api/cortex/status"),
  cortexSnapshot: () => req<any>("/api/cortex/snapshot"),
  cortexAsk: (role: string, question: string) =>
    req<any>("/api/cortex/ask", { method: "POST", body: JSON.stringify({ role, question }) }),
  cortexEodReport: () => req<any>("/api/cortex/eod-report", { method: "POST" }),
  cortexAnalyze: (force = false) => req<any>(`/api/cortex/analyze${force ? "?force=true" : ""}`),
  aiTimeline: (limit = 60) => req<any>(`/api/ai-timeline?limit=${limit}`),
  weekendAi: () => req<any>("/api/weekend-ai"),
  weekendAiRun: () => req<any>("/api/weekend-ai/run", { method: "POST" }),
  // auth
  authCheck: () => req<any>("/api/auth/check"),
  login: (password: string) =>
    req<any>("/api/auth/login", { method: "POST", body: JSON.stringify({ password }) }),
  // stocks
  stockSearch: (q: string) => req<any[]>(`/api/stocks/search?q=${encodeURIComponent(q)}`),
  watchlist: () => req<any>("/api/watchlist"),
  watchlistAdd: (s: { symbol: string; security_id: number; exchange: string }) =>
    req<any>("/api/watchlist", { method: "POST", body: JSON.stringify(s) }),
  watchlistRemove: (symbol: string) =>
    req<any>(`/api/watchlist/${symbol}`, { method: "DELETE" }),
  favoriteToggle: (symbol: string) =>
    req<any>(`/api/favorites/${symbol}`, { method: "POST" }),
  // scanner + alerts
  scanner: () => req<any[]>("/api/scanner"),
  alerts: () => req<any[]>("/api/alerts"),
  alertsConfig: (cfg: Record<string, string>) =>
    req<any>("/api/alerts/config", { method: "PUT", body: JSON.stringify(cfg) }),
  alertsTest: () => req<any>("/api/alerts/test", { method: "POST" }),
  // portfolio
  portfolioRisk: () => req<any>("/api/portfolio/risk"),
  portfolioConfig: (capital: number, risk_per_trade_pct: number) =>
    req<any>("/api/portfolio/config", {
      method: "PUT",
      body: JSON.stringify({ capital, risk_per_trade_pct }),
    }),
  // paper / backtest / journal
  paper: () => req<any>("/api/paper"),
  paperOpen: (body: Record<string, unknown>) =>
    req<any>("/api/paper/open", { method: "POST", body: JSON.stringify(body) }),
  paperClose: (id: string, exit_price?: number) =>
    req<any>(`/api/paper/close/${id}`, { method: "POST", body: JSON.stringify({ exit_price }) }),
  backtest: (symbol: string, year: number) =>
    req<any>("/api/backtest", { method: "POST", body: JSON.stringify({ symbol, year }) }),
  replay: (symbol: string, date: string) =>
    req<any>("/api/replay", { method: "POST", body: JSON.stringify({ symbol, date }) }),
  breadth: () => req<any>("/api/breadth"),
  learning: () => req<any>("/api/learning"),
  analyticsPerformance: () => req<any>("/api/analytics/performance"),
  audit: () => req<any>("/api/audit"),
  brain: (question: string) =>
    req<any>("/api/brain", { method: "POST", body: JSON.stringify({ question }) }),
  brainAuto: () => req<any[]>("/api/brain/auto"),
  strategist: () => req<any>("/api/strategist"),
  marketDna: () => req<any>("/api/dna"),
  evolution: (period = "weekly") => req<any>(`/api/evolution?period=${period}`),
  simulator: () => req<any>("/api/simulator"),
  research: () => req<any>("/api/research"),
  reportCard: () => req<any>("/api/report-card"),
  dailyReview: () => req<any>("/api/daily-review"),
  healthCenter: () => req<any>("/api/health/center"),
  validate: () => req<any>("/api/validate"),
  safeMode: () => req<any>("/api/safemode"),
  healthPersistence: () => req<any>("/api/health/persistence"),
  professor: () => req<any>("/api/professor"),
  roadmap: () => req<any>("/api/roadmap"),
  weights: () => req<any>("/api/weights"),
  weightsQueue: () => req<any>("/api/weights/queue", { method: "POST" }),
  weightAction: (action: "approve" | "simulate" | "apply" | "reject" | "revert", weight_key: string) =>
    req<any>(`/api/weights/${action}`, { method: "POST", body: JSON.stringify({ weight_key }) }),
  evolutionNightly: () => req<any>("/api/evolution/nightly"),
  runNightly: () => req<any>("/api/evolution/run-nightly", { method: "POST" }),
  journal: () => req<any[]>("/api/journal"),
  addJournal: (entry: Record<string, unknown>) =>
    req<any>("/api/journal", { method: "POST", body: JSON.stringify(entry) }),
};
