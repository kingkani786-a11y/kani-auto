# ARCHITECTURE — Cloud AI Trader X Pro (Architecture-Frozen, RC1)

**Stack**: FastAPI backend (always-on via LaunchAgent, port 8000) · Next.js 15
frontend (port 3000) · DhanHQ v2 broker (Client ID + Access Token, in-memory
only, never persisted) · Supabase persistence (7 tables). Advisory-only —
no order placement code exists.

## The full lifecycle (every link live)

```
Market → Opportunity → Strike → Gate → Decision → (Execution by human)
      → Verdict → Learning → Evidence → Proposal → Approval → Improvement
```

## Engine map (frozen set)

| Engine | Role | Key module |
|---|---|---|
| Confluence (12-layer) | directional scoring, mandatory gate, adaptive threshold, calibration FORCE-WAIT | `engines/confluence.py` |
| Universal Strike Engine | chain-capability detected per instrument (index/stock/MCX identical); ranking, premium plan | `engines/strike_selector.py`, `_option_tick` |
| Opportunity Engine | staged L1 quotes → L2 chains (top-N, spaced, cooldown-deferential) → L3 full engine on click | `services/opportunity.py` |
| Execution Gate | ONE authoritative BUY/WAIT/NO-TRADE + quality bar | `engines/execution_gate.py` |
| Verdict Engine | blocked-side shadow trades → CAPITAL_SAVED / MISSED_WINNER / NEUTRAL, per-module + per-regime, verdict confidence | `services/verdicts.py` |
| Audit tracker | taken-side WINNER/LOSER settle | `services/audit.py` |
| Exit / Re-entry / Cycle | trade management, banded exits, re-entry safety rule, chained forecast | `engines/exit_intelligence.py` |
| Historical Learning | 5-yr daily setups, vol-regime & DOW splits, analogue days (Market Memory), nightly refresh | `services/historical_learning.py` |
| Market DNA / Memory | live pattern snapshots + similarity | `engines/market_dna.py`, memory service |
| Kill Switch / Safe Mode / Capital Protection / Traps / NTZ / Gamma Shield | capital protection stack (overrides everything) | respective engines |
| Weight Approval | QUEUE → APPROVE → SIMULATE → APPLY (human-only) | `services/weight_approval.py` |
| Scanner + Index Radar | L1 momentum ranking (batch quotes) | `services/scanner.py`, `engines/index_radar.py` |

## Data-integrity guards (never fabricate)

- Universal LTP parser (11+ payload shapes), MarketClosedError-first resolution
- **Put-call parity chain sanity** at ingest (every instrument) AND at
  opportunity publish — parity-violating chains are rejected loudly
- Strike-step inference for stock chains; sorted expiries (nearest-first)
- Intraday expected-move horizon (1-day sigma cap), to-expiry kept separately
- Instrument-aware N/A (chain-less contracts never blocked on option layers)
- Rate budget: chain deep-scans defer when broker cooldown is active

## Modes

- **Trading** — decision-first stack (Mission/Command → Opportunity → Index →
  Strike/Plan/Qty → Point Capture → shields → diagnostics)
- **Research** — all analytics, learning, memory, evolution, audit

## Market State & Time Source Map (RC1.16, Rule 10)

**Market-open truth — one computational source, no cache:**

```
is_market_open() / market_status()  (app/core/state.py, pure functions,
                                      recompute fresh on every call)
        │
        ▼
AppState.status()  (aggregates market_open + market_status + data_quality +
                     kill_switch + safe_mode + server_time)
        │
        ├── HTTP: every route that reads `state.status()` (self-check, etc.)
        │         — backend consumers always get a fresh call, never stale.
        │
        └── WebSocket "status" channel — broadcast by MarketService's
            `_status_loop` every 20s (RC1.15), plus on connect/disconnect/
            symbol-switch. This is the ONLY hop where staleness could occur
            (a frontend copy between ticks) — bounded to ≤20s by design.
                │
                ▼
        Frontend consumers (all read the SAME `status` object from
        lib/store.tsx, none recompute independently):
        MarketStatusBanner · StatusBar/Header · FeedDiagnostics ·
        DailyReview · Scanner gating · Opportunity board gating ·
        Kill Switch card (market_closed-aware, RC1.14) · AI Self-Check
```

No component computes market-open state independently — every consumer above
is a reader of the one chain shown, per Rule 10.

**Time source — one clock, no independent timezone objects (RC1.16):**

```
app/core/clock.py — the only place a zoneinfo.ZoneInfo is constructed
  IST = Asia/Kolkata           NY = America/New_York (US-session clock only)
  now() / today_str() / midnight_today_ts()
        │
        ├── Market Countdown / Session Clock → core/state.py, engines/market_context.py
        ├── US Open Timer / Europe Session   → services/global_feed.py `_clock()`
        ├── Greeks Expiry Clock (Black-Scholes T) → engines/index_analytics.py,
        │                                            engines/strike_selector.py
        ├── Daily Reset ("Today" scope)       → services/analytics.py `_midnight_today()`,
        │                                        services/missed_winner.py `summary()`
        ├── Weekly Reset ("This week" scope)  → rolling 7 days, both of the above —
        │                                        consistent with each other by convention
        ├── Global Context Capture            → services/global_feed.py (same `_clock`)
        └── Kill Switch Timer / Validation Window → services/kill_switch.py,
             services/verdicts.py — duration-only (`time.time()` deltas), never a
             wall-clock day boundary, so timezone-agnostic by construction; no fix needed.
```

Before RC1.16, 12 files each independently built `zoneinfo.ZoneInfo("Asia/
Kolkata")`; two of them (`index_analytics.py`, `strike_selector.py`) actually
used a naive, timezone-less `datetime.now()` for Greeks time-to-expiry —
silently wrong on any host not OS-configured to IST. All 12 now import from
`core/clock.py`. Separately, `missed_winner.summary()`'s "today" was a
rolling-24h window while its own UI label said "Today" (calendar day) —
fixed to share `analytics.py`'s calendar-day definition via
`midnight_today_ts()`.

## Backlog — deferred to RC2 / Production (owner-ordered, not to be built in RC1)

- **Event-driven state broadcast**: replace the 20s `_status_loop` poll
  (RC1.15) with a push-on-change model once Production Optimization begins.
  The current polling interval is sufficient for RC1; do not implement this
  early.
- **Exchange Calendar (RC1.16 follow-up, owner-raised)**: `is_market_open()`
  today only knows the daily IST time window (weekday check + hours) — it
  has no concept of NSE/BSE trading holidays, Muhurat trading, or ad-hoc
  special/half-day sessions. Needs a holiday-calendar data source (static
  yearly list at minimum) before this can be built; not started, since no
  such dataset exists in the codebase yet. Proposed hierarchy for Production:
  `Trading Clock → Exchange Calendar → Market Open`.

### Resolved by RC1.16 follow-up (same day)
- **Expiry Time Audit (owner-raised)**: `_years_to_expiry`/`_years` were two
  independently-duplicated Black-Scholes T functions (Expiry Date + 15:30
  IST close + current time → years remaining). Centralized into
  `core.clock.years_to_expiry()` — `index_analytics._years_to_expiry` and
  `strike_selector._years` are now the literal same function object, not two
  copies that happen to agree.
