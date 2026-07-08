# CLOUD AI TRADER X PRO V10.0 — INSTITUTIONAL AI TRADING DECISION TERMINAL

**V10 upgrade (extends V7.5, no rebuild):** the platform now leads with a **3-second decision view**. A new decision-synthesis engine (`engines/decision.py`) collapses the full 12-layer intelligence packet + lifecycle + portfolio into one simple screen: market state (🔥 TRENDING / ⚡ SCALPING / 🔄 RANGE / 🚫 AVOID), opportunity level, conviction, the action (BUY CALL / BUY PUT / WAIT / NO TRADE), **recommended + max-safe lots** from confidence scaling against the risk budget, entry-timing window (🚀 OPEN / ⏳ WAIT / ⚠ LAST CHANCE), action state (📈 HOLD / 💰 BOOK PARTIAL / ➕ ADD / 🛑 EXIT), and a single plain-English reason. The dashboard hides OI/PCR/Greeks/confidence-% behind a one-click **/advanced** page (all V6/V7.5 panels preserved there) and the **/command** center remains. Strict rules added: every signal must carry entry+SL+T1/T2/T3 or it's blocked; **R:R to the first target must clear 1:2** (level geometry retuned to SL 1.0×ATR, targets 2.0/3.0/4.5×ATR) else NO TRADE; lot sizing scales with conviction (A=full, B=half, C=quarter). Timeframes add **1s** (seeded from 1m, refined live) with **default 5m**. Backend stays complex; frontend is ultra-simple — the Golden Rule.

# V7.5 — NEAR-INSTITUTIONAL EDITION

**V7.5 upgrade (extends V6, no rebuild):** broker stability layer (global request gate with dynamic throttle, per-minute budget, escalating smart cooldown, request analytics + broker health score); advanced market-regime AI (expansion/exhaustion, accumulation/distribution, markup/markdown, short-covering/long-liquidation, gamma squeeze, vol expansion/compression — shown as phase chips); order-flow intelligence (aggression, delta imbalance, liquidity vacuum, hidden accumulation/distribution → Order Flow Score); depth-of-market engine (bid/ask walls, liquidity score — when the broker provides depth); probability lab (EV, expected reward/drawdown, regime accuracy); AI decision audit (confirmed vs failed layers, probability, threshold trace on every signal); advanced safety engine (hard NO-TRADE vetoes on extreme volatility, liquidity vacuum, dynamic confidence < 60, broker cooldown, poor data); data-quality engine (`/api/health/data` validates quotes/candles/chain/Greeks/signals for missing/corrupt/delayed); portfolio intelligence (correlation risk, concentration, portfolio heat, capital efficiency, risk clusters); AI execution assistant (allocation %, max risk, risk-adjusted reward, trade suitability); regime-tagged self-learning with stored PnL; and the **Institutional Command Center** (`/command`) unifying regime, probability, order flow, breadth, learning, broker stability, decision audit, top opportunities and alerts. System health gains broker-stability + data-quality + cache/memory diagnostics.

# V6.0 — ULTIMATE INSTITUTIONAL EDITION

**V6 upgrade:** native chart engine (`lightweight-charts` fed by broker data — no TradingView embed, fixes all NSE/MCX rendering; strict symbol binding, destroy-on-switch, live tick candles, loading/no-data/invalid states, client+server caching with retries), smart entry panel (Breakout/Reversal/Momentum, Auto Mode from AI signal or candle engine, levels drawn on-chart), adaptive confirmation thresholds per regime, dynamic confidence shown as five components, regime-aware self-learning memory (outcomes by regime feed thresholds and grading), anomaly detection (unusual OI/volume/IV/sudden moves → alerts), AI market coach (what's missing, what must happen next, when to avoid), AI trade mentor (entry/exit/patience/discipline/risk scores per closed trade), top-5 ranked strikes with P(ITM), opportunity ranking (probability/risk/expected reward) + market breadth on the scanner, and a market replay engine (`/replay`) to step through any historical session minute-by-minute with AI decision markers.

# V4.0

**V4 upgrade:** stock module (search ANY NSE/BSE symbol incl. NIFTY 500, watchlist + favorites at `/stocks`), 60-second trade scanner with Watchlist AI alerts (`/scanner`), signal lifecycle engine (SETUP→WATCH→ARMED→TRIGGERED→ENTRY→TARGET→EXIT) with trigger/invalidation prices, expiry engine (gamma wall, max-pain shift, OI migration, pinning, squeeze), market profile (initial balance, day type, auction structure), A/B/C signal grading (A ≥ 85, B 70–85, C 60–70, else NO TRADE), historical market memory with signal-outcome accuracy feedback, alert engine (in-app + browser push + Telegram + SMTP email), portfolio risk engine (risk-based position sizing, exposure, max DD), secure login (set `CAT_APP_PASSWORD`; token sessions persist per device), per-timeframe candle reload incl. 4H (≥500 candles), backtests for 2022–2026 with Sharpe + expectancy, and journal grades/reasons/screenshots. Markets: index options, stocks (cash), futures and commodities — analysis only, never order placement.

**X upgrade:** signals now come from a 10-layer confluence engine (trend, structure, option chain, smart money, Greeks, volume profile, multi-timeframe, regime, probability, risk) with a mandatory-confirmation gate — if trend, structure, OI and MTF don't all agree, the answer is NO TRADE. New: option strike selector with premium levels, early-warning setups, AI market narrator, paper trading with post-trade reviews, 2022–2025 backtesting, and a system health dashboard (`/paper`, `/backtest`, `/health`). Key endpoints: `GET /api/intelligence`, `GET /api/health/system`, `POST /api/paper/open`, `POST /api/backtest`.


Browser-based AI trading analytics terminal for Indian **index** (NIFTY, BANKNIFTY, SENSEX, FINNIFTY, MIDCPNIFTY) and **commodity** (GOLD, SILVER, CRUDEOIL, NATURALGAS) markets. Works in Safari, Chrome, and mobile browsers via a URL.

> **Disclaimer:** This system produces analytics and informational signals only. It never places, modifies, or cancels orders, and nothing here is investment advice.

## Architecture

```
cloud-ai-trader/
├── backend/                FastAPI service
│   ├── app/
│   │   ├── main.py         App entrypoint + /ws WebSocket endpoint
│   │   ├── config.py       Static settings (env-driven)
│   │   ├── core/state.py   Runtime state — credentials live ONLY here (memory)
│   │   ├── broker/         DhanHQ v2 REST client + instrument registry
│   │   ├── engines/        greeks, technicals, index analytics,
│   │   │                   smart money, signal engine, risk engine
│   │   ├── services/       market_service (all background loops), journal
│   │   ├── api/routes.py   REST API
│   │   └── ws/manager.py   WebSocket broadcast
│   └── db/schema.sql       Supabase schema (journal + signal history)
├── frontend/               Next.js 15 + React 19 + TypeScript + Tailwind
│   ├── app/                Dashboard, Settings, Journal pages
│   ├── components/         Chart, panels, option chain, status bar
│   └── lib/                API client, WebSocket store, types
├── mcp-server/             MCP server exposing the terminal as agent tools
└── README.md
```

## The connection contract

The entire system is **idle at boot**: no API calls, no data fetching, no calculations. Everything starts only after the user enters **Client ID + Access Token** in Settings and clicks **SAVE & CONNECT**, which:

1. validates the credentials against the broker (`/v2/fundlimit`),
2. on success starts the engines — spot every **3 s**, option chain + Greeks every **15 s**, AI analysis every **3 min**,
3. streams everything to the browser over WebSocket.

Saving a new token (Dhan rotates it daily) tears down the old session and reconnects automatically — no restart. The token is held in backend process memory only; it is never persisted and never echoed back to the browser (only its last 4 characters).

## Broker

Built for **DhanHQ v2** (auth = client id + daily access token, exactly matching the requirement). To use another broker, implement the same five methods in `backend/app/broker/` (`validate`, `get_ltp`, `get_quote`, `get_expiries`, `get_option_chain`, `get_intraday_candles`).

**Commodity contracts:** MCX futures roll monthly. Set the active contract `security_id` for GOLD/SILVER/CRUDEOIL/NATURALGAS in `backend/app/broker/instruments.py` from the [Dhan scrip master](https://images.dhan.co/api-data/api-scrip-master.csv).

## Run locally

### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Optional `backend/.env`:
```env
CAT_SUPABASE_URL=https://xxxx.supabase.co
CAT_SUPABASE_SERVICE_KEY=eyJ...
CAT_CONFIDENCE_THRESHOLD=65
CAT_FRONTEND_ORIGIN=https://your-frontend.example.com
```
Without Supabase the journal works in-memory (lost on restart).

### Frontend
```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```
Env (`frontend/.env.local`) for production:
```env
BACKEND_URL=https://your-backend.example.com      # REST rewrite target
NEXT_PUBLIC_WS_URL=wss://your-backend.example.com/ws
```

### MCP server (optional)
```bash
cd mcp-server
pip install -r requirements.txt
CAT_BACKEND_URL=http://localhost:8000 python server.py
```
Register in Claude Code: `claude mcp add cloud-ai-trader -- python /path/to/mcp-server/server.py`

### Supabase
Run `backend/db/schema.sql` in the Supabase SQL editor, then set the two `CAT_SUPABASE_*` env vars. The backend uses the service-role key; RLS is enabled so anon keys can't read the tables.

## Deploy

**Backend (Railway / Render / Fly.io / any VM):**
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
- Needs a single always-on instance (state + loops are in-process). Do not autoscale horizontally.
- Put it behind HTTPS (the access token transits this API).
- Set `CAT_FRONTEND_ORIGIN` to your frontend URL to lock down CORS.

**Frontend (Vercel):**
- Import `frontend/`, set `BACKEND_URL` and `NEXT_PUBLIC_WS_URL` env vars.
- The dashboard is mobile-first and installable to the home screen.

**Checklist**
- [ ] HTTPS on both services (WebSocket must be `wss://` from an https page)
- [ ] `CAT_FRONTEND_ORIGIN` set (no `*` in production)
- [ ] Supabase schema applied + service key set (optional)
- [ ] MCX commodity security IDs updated for the current contract month
- [ ] Confidence threshold tuned in Settings

## Signal engine (how a signal is born)

No single indicator can fire a signal. Seven factor scores (0–100) are blended:

| Factor | Weight | Source |
|---|---|---|
| Greeks | 25% | ATM delta skew (broker Greeks or Black-Scholes fallback) |
| OI | 20% | Writing / build-up structure (smart-money engine) |
| PCR | 15% | Chain-wide put/call OI ratio |
| Trend | 15% | EMA 9/21 regime |
| VWAP | 10% | Price distance from session VWAP |
| ADX | 10% | Trend strength (amplifies trend side only) |
| Volume | 5% | Expansion + momentum |

A `BUY CE / BUY PE` (index) or `BUY/SELL FUTURES` (commodity) signal fires only when the winning composite ≥ threshold (default 65%) **and** beats the opposite side by ≥ 10 points; otherwise `NO TRADE`. Stops and three targets are ATR-derived (1.2× SL; 1.5× / 2.5× / 4× targets). The risk engine downgrades or warns on chop (ADX < 18), poor data quality, and low confidence.
