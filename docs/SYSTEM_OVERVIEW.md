# Cloud AI Trader Explorer — Full System Overview (A → Z)

*Portable reference: what this software is, what every part does, and how it
runs. Written so a new engineer on any machine can understand the whole system.
Last updated: 2026-07-11.*

---

## 1. What it is (one paragraph)

Cloud AI Trader Explorer is a **decision-support Trading Operating System** for
Indian index/options markets (NIFTY / SENSEX / FINNIFTY / CRUDEOIL …). It reads
live market data from the DhanHQ broker, runs a large deterministic analysis
engine to produce an explainable BUY / WAIT / NO-TRADE decision, and layers an
optional **AI cortex** (Gemini, provider-agnostic) on top for explanation,
research, reports, radio narration and self-review.

**It NEVER places orders.** It is analysis and decision-support only. Every
number is measured or honestly labelled "building/insufficient" — nothing is
fabricated.

---

## 2. Core doctrine (the non-negotiable laws)

1. **No orders, ever.** The system decides and explains; the human acts.
2. **Capital protection > profit.** Kill-switch and safe-mode hard vetoes can
   never be weakened.
3. **Never fabricate** data, probabilities, or confidence. Honest
   building/insufficient/LEARNING states instead.
4. **The LLM never decides.** BUY/WAIT/EXIT/SL/strike come ONLY from the
   deterministic Decision Engine. The LLM only explains/researches/teaches/
   summarizes/proposes.
5. **No auto rule changes.** The AI may propose; production changes require
   human approval (the Phase-22 weight-approval pipeline).
6. **One State → One Source → One Truth → Many Consumers** (Rule 10). Voice,
   AI, and dashboard are consumers of published engine state — never authors.
7. **Two-Layer law.** Opportunity/observation layers run parallel to the
   Decision layer; if they ever disagree, the execution gate wins.

Full doctrine: `docs/DECISION_DOCTRINE.md`, `docs/QUALITY.md`, `docs/AI_OS_VISION.md`.

---

## 3. Tech stack & layout

| Part | Tech | Location |
|---|---|---|
| Backend | Python 3.14, FastAPI, uvicorn, httpx, numpy, pydantic | `backend/app/` |
| Broker | DhanHQ v2 REST (Client ID + Access Token, in-memory only) | `backend/app/broker/` |
| Frontend | Next.js 15 / React / TypeScript, Tailwind | `frontend/` |
| Persistence | Supabase (optional; falls back to in-memory) | `backend/app/services/persistence.py` |
| AI layer | Gemini via `google-genai` (provider-agnostic) | `backend/app/services/cortex/` |
| Realtime | WebSocket (`/ws`) broadcast + REST polling | `backend/app/ws/`, `frontend/lib/store.tsx` |
| Packaging | PWA (service worker) · Capacitor (Android/iOS) · Electron (Win/Mac) | `frontend/public/`, `frontend/electron/` |
| Always-on | macOS LaunchAgents `com.cloudaitrader.{backend,frontend}` | `~/Library/LaunchAgents/` |

**Credentials never persist.** Broker Client ID + Access Token live only in
`core.state` (in-memory); the Dhan token expires daily → morning re-connect.
The Gemini key lives in `backend/.env` as `CAT_GEMINI_API_KEY` (git-ignored).

---

## 4. Data flow (the pipeline)

```
Dhan API (quotes, option chain, Greeks, OI, futures, candles)
        │
        ▼
  Decision Engine  (55 deterministic engines — Section 6)
        │  publishes → core.state (spot, decision, intelligence, signal, …)
        ├────────────────────────────► Dashboard (React) via WS + REST
        │
        ▼
  Context Builder (published snapshot only — Rule 10)
        │
        ▼
  AI Cortex (Gemini)  →  Analysis · Radio · Reports · Research · Chat
        │  (Safety Layer + Cost Controller wrap every call)
        ▼
  Dashboard cards + Voice
```

Tier discipline (cost + safety):
- **Tier 1 (per tick, seconds):** deterministic engine only — no LLM ever.
- **Tier 2 (on demand):** AI chat, analysis, teacher — Gemini per request.
- **Tier 3 (scheduled, 2–4/day + weekends):** EOD report, weekend research.

---

## 5. Runtime cadence

| Loop | Interval | Job |
|---|---|---|
| Spot | 2s | live price |
| Option chain / Greeks | 5s | CE/PE, OI, ΔOI, futures, Greeks |
| AI cycle | 30s | decision, narrator, structure, intelligence packet |
| Scanner | 120s | multi-symbol scan |
| Nightly audit | 23:59 IST | self-tuning evolution report (proposals only) |
| Weekend AI | hourly (market closed) | Research → Review → Plan (Gemini) |

All broker-gated except the nightly audit and Weekend AI (broker-independent).
Cadence is env-overridable via `CAT_*` in `backend/app/config.py`.

---

## 6. The Decision Engine — 55 engines (grouped)

Everything here is **deterministic** (no LLM). Location: `backend/app/engines/`.

**Market structure & trend**
`technicals` · `structure` · `mtf` (multi-timeframe) · `market_context` ·
`regime` · `market_dna` (historical similarity) · `market_path` · `index_analytics`

**Order flow & options**
`orderflow` · `dom` (depth) · `smart_money` · `institutional_scores` ·
`volume_profile` · `market_profile` · `greeks` · `strike_selector`
(Black-Scholes reprice) · `expiry` · `premium_forecast` · `gamma_shield`

**Signals & probability**
`signal_engine` · `confluence` · `probability` · `probability_ladder` ·
`alpha_engine` · `anomaly` · `candle_projection` · `technicals`

**Entry / decision**
`decision` · `decision_intelligence` · `entry_checklist` · `entry_zone` ·
`entry_score_timeline` · `execution_gate` (the hard gate) · `execution_card` ·
`signal_maturity` · `confidence_evolution` · `confidence_explainer`

**Risk & capital protection**
`risk` · `portfolio_risk` · `capital_protection` · `guards` · `lifecycle`

**Scalping & fast signals**
`scalp_radar` (V3 execution suite) · `index_radar` · `early_warning`

**Exit & forward**
`exit_intelligence` · `future` (scenarios/war-room) · `futures` (confirmation) ·
`addon_flow`

**Context & meta**
`global_context` (US/DXY/gold/crude/VIX — ±3 confidence, never a gate) ·
`quality` · `narrator` · `options_professor` · `market_clock`

The **execution gate** (`execution_gate.py`) is the single arbiter: it blocks a
BUY unless Trend/Structure/OI/MTF/Liquidity/Greeks/Premium checks pass, and
records *why* it blocked (blocker research) for explainability.

---

## 7. Services layer — 30 modules

Location: `backend/app/services/`.

**Orchestration:** `market_service` (the main loop; owns all background tasks).
**State/realtime:** `core.state` (single source of truth), `ws/manager`.
**Persistence & memory:** `persistence` (Supabase), `memory`, `journal`.
**Learning & evidence:** `verdicts` (gate-efficiency ledger), `validation`
(report card / daily review), `evolution` (nightly self-tuning → proposals),
`historical_learning`, `missed_winner`, `premium_accuracy`, `audit`,
`analytics`, `calibration` (inside validation).
**Capital protection:** `kill_switch`, `safe_mode`.
**Opportunity/scan:** `scanner`, `opportunity`, `move_detector` (MODE),
`scalp_state`, `index_radar`.
**Trading tools:** `paper` (paper trading), `backtest`, `replay`,
`research_lab`, `weight_approval` (Phase-22 human-approval pipeline).
**Feeds/health:** `global_feed`, `data_quality`, `health_center`.
**Q&A:** `brain` (rule-based Q&A over existing state).
**Alerts:** `alerts` (feed + WS + Telegram + email; the event bus).

---

## 8. The AI Cortex — `backend/app/services/cortex/`

Optional LLM layer. **Disabled unless a key is present; the engine runs
identically without it.** Provider-agnostic (Gemini now; Claude/others via
config — swap is a settings change, not a rewrite).

| Module | Job |
|---|---|
| `context_builder` | The ONLY engine→LLM bridge. Emits the published structured snapshot (trend/score, liquidity/score, structure, decision, blockers, confidence). Raw candles NEVER sent. |
| `safety` | Code-enforced hard NOs. Flags any trade-directive language in LLM output; always attaches the engine's authoritative decision. Prompt-injection-safe. |
| `cost_controller` | Mandatory budget guard. Per-IST-day ₹ cap + call cap; ledger resets at IST midnight; per-model ₹ estimate. |
| `prompts` | The owner's Master Prompt (charter) + 7 role prompts (explainer/analyst/teacher/reviewer/planner/developer/research). |
| `provider` | `cortex.ask(role, context, question)`; auto-detects Gemini/Anthropic; lazy SDK import; wires cost + safety around every call; `thinking_budget=0`. |
| `analysis` | AI Analysis card — 4 blocks (WHY/NEXT/WATCH/CHANGE), cached by decision-band so dashboard polls are ~free. |
| `report` | End-of-day AI review, grounded in measured ledgers. |

Plus (in `services/`): `weekend_ai` (weekend Research/Review/Plan),
`ai_timeline` (the day's transition story), `system_verify` (health + score).

---

## 9. API — 100 endpoints (by area)

Base: `/api/*` (Next.js proxies to FastAPI). Auth: `X-Auth-Token` when
`CAT_APP_PASSWORD` is set.

- **Connect/status:** `/settings/connect` `/settings/disconnect` `/status` `/symbols` `/symbol`
- **Market data:** `/market/overview` `/market/optionchain` `/market/candles/{tf}`
- **Decision/intelligence:** `/intelligence` `/decision` `/signal/latest` `/lifecycle` `/execution-gate` `/execution-card` `/checklist` `/maturity` `/confidence` `/entry-score`
- **AI Cortex:** `/cortex/status` `/cortex/snapshot` `/cortex/ask` `/cortex/analyze` `/cortex/eod-report`
- **AI OS:** `/ai-timeline` `/weekend-ai` `/weekend-ai/run` `/ai-changelog` `/system-verify` `/version` `/briefing` `/brain` `/brain/auto` `/strategist`
- **Learning/evidence:** `/report-card` `/daily-review` `/verdicts` `/premium-accuracy` `/audit` `/validate` `/evolution` `/evolution/nightly` `/evolution/run-nightly` `/historical-learning` `/learning` `/analytics/performance`
- **Weights (Phase-22):** `/weights` `/weights/queue` `/weights/{approve,simulate,apply,reject,revert}`
- **Tools:** `/paper` `/paper/open` `/paper/close/{id}` `/backtest` `/replay` `/simulator` `/research` `/dna` `/future` `/exit` `/scalp` `/professor` `/roadmap`
- **Scan/watchlist:** `/scanner` `/opportunities` `/move-alerts` `/stocks/search` `/watchlist` `/favorites/{symbol}` `/breadth`
- **Risk/portfolio:** `/portfolio/config` `/portfolio/risk` `/safemode` `/gamma-shield`
- **Alerts:** `/alerts` `/alerts/config` `/alerts/test`
- **Health:** `/health/system` `/health/data` `/health/center` `/health/persistence` `/self-check` `/global` `/missed-winners`

Full list: `grep '@router' backend/app/api/routes.py`.

---

## 10. Frontend — 24 pages

Location: `frontend/app/`. Home (`/`) is the command dashboard.

`ai-workspace` (AI Chat/Reports/Weekend AI) · `advanced` (full analysis) ·
`strategist` · `command` · `cockpit` · `brain` · `dna` · `simulator` ·
`evolution` · `research` · `weights` · `future` · `warroom` · `stocks` ·
`scanner` · `paper` · `backtest` · `replay` · `analytics` · `report-card` ·
`audit` · `journal` · `health` · `settings` · `login`.

**Home dashboard cards (this session's AI additions):** AI Analysis (4-block +
Engine-Verified badge) · AI Timeline · System Verify (health + unified status) ·
Build Version (self-verify) · AI Changelog · Voice Narrator (AI Radio).

---

## 11. AI OS roadmap (where it's going)

Governance: build **Foundation → Intelligence → Automation**; each layer must
pass `docs/PRODUCTION_CHECKLIST.md` before the next. 12-layer target (FAIOS):
Data OS · Decision Engine · AI Cortex · Memory · Research · Evolution ·
Dashboard Intelligence · Entry Intelligence · AI Radio · AI Architect ·
Knowledge OS · Simulation Intelligence. Full vision + laws:
`docs/AI_OS_VISION.md`; proposals: `docs/PROPOSALS.md`.

**Shipped this cycle (all live):** AI Cortex (provider-agnostic) · AI Analysis ·
AI Timeline · AI Radio v1.0 · AI Workspace · Weekend AI · System Verify ·
Build Version · AI Changelog + PWA deploy-visibility fix.
**Pending:** AI Radio live-speech verification (market-hours).
**Not built:** Entry Intelligence · AI Council · Knowledge OS · News/Calendar/
FII-DII feeds · AI Architect · Phase-3 Automation.

---

## 12. How to run it (any machine)

**Backend**
```
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# optional AI: .venv/bin/pip install google-genai   (or anthropic)
# create backend/.env: CAT_SUPABASE_URL / CAT_SUPABASE_SERVICE_KEY (optional),
#                      CAT_AI_PROVIDER=gemini, CAT_GEMINI_API_KEY=... (optional)
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend**
```
cd frontend
npm install
npm run build && npm run start        # http://localhost:3000
```

Then open the dashboard → **Settings** → enter Dhan Client ID + Access Token →
**Save & Connect**. Nothing runs until connected (deliberate). The Dhan token
expires daily; re-connect each morning before 09:15.

**Always-on (macOS):** LaunchAgents auto-start both services; see
`docs/DEPLOYMENT.md` and `docs/ALWAYS_ON.md`. Packaged apps (mobile/desktop):
`npm run cap:*` / `npm run desktop:*`.

**Self-verify a deploy:** `curl /api/version` (backend commit + AI) and the
dashboard's Build Version panel (frontend/backend commit + Match ✅).

---

## 13. Documentation map (`docs/`)

| File | What |
|---|---|
| `SYSTEM_OVERVIEW.md` | **This file — A-to-Z reference** |
| `AI_OS_VISION.md` | FAIOS 12-layer vision + all AI laws |
| `DECISION_DOCTRINE.md` | Trading decision rules |
| `QUALITY.md` | Display-honesty rules, Entry Command Center spec |
| `PROPOSALS.md` | Every proposal (#001–#015) with evidence |
| `PRODUCTION_CHECKLIST.md` | Per-layer production-ready status |
| `RELEASE_NOTES.md` | Chronological change log (RC + AI-A entries) |
| `ARCHITECTURE.md` | System architecture + backlogs |
| `INCIDENTS.md` | Post-mortems (Incident #001 …) |
| `DEPLOYMENT.md` / `ALWAYS_ON.md` | Run/deploy runbook |
| `KNOWN_LIMITATIONS.md` | Honest limitations |
| `RC_STATUS.md` | Release-candidate status |
| `VALIDATION_REPORTS.md` | Measured validation data |
| `CHANGELOG.md` | Legacy changelog |

---

## 14. The one-line summary

**A broker-connected, doctrine-bound, deterministic options-decision engine
with an optional provider-agnostic AI cortex on top — explainable, auditable,
cost-capped, and constitutionally forbidden from placing orders or letting the
AI make trading decisions.**
