# AI Operating System Vision — Cloud AI Trader Explorer v2 → v10

**Status: RECORDED (owner architecture, 2026-07-11). Not yet approved for build.**
**Blocked on: Anthropic API key (owner must create at platform.claude.com) +
current validation queue (RC1.17 → MODE → premium-accuracy → Voice → IPMME).**

Owner's framing: not a Trading Dashboard — an **AI Operating System for
Financial Markets**. Pipeline evolves from
`Data → Rules → Calculation → Decision` to
`Data → AI Thinking → Research → Reasoning → Self Learning → Decision → Voice → Memory → Improvement`.

## Locked laws (owner, verbatim in spirit)

1. **AI never auto-changes trading rules.** It may discover patterns,
   backtest, measure win rates, and *recommend* — production changes only
   after owner approval (this is exactly the existing Phase-22 pipeline).
2. Trading decisions stay **explainable and auditable**.
3. Existing doctrine unchanged: system never places orders; kill-switch /
   safe-mode vetoes untouchable; Voice is consumer-only; Two-Layer law.

## Honest inventory — 10 engines vs what exists today

| # | Engine (owner) | Today (deterministic) | Gap = the LLM language layer |
|---|---|---|---|
| 1 | Live Data Brain | ✅ market_service, chain, Greeks, OI, PCR, VWAP, global feed | news feed not connected |
| 2 | AI Reasoning | ✅ entry_checklist + gate + blocker_research produce exactly the "Trend strong BUT volume absent SO not ready" chain — as structured data | natural-language narration of that chain |
| 3 | AI Research | 🟡 verdict ledger (572 settled), module_stats, premium-accuracy regimes | 4-year pattern history **does not exist** — needs historical data acquisition first; honest: cannot be conjured |
| 4 | Memory Brain | ✅ persistence + ledgers ("Liquidity saved 78 trades" is literally module_stats today) | conversational recall of it |
| 5 | AI Learning | ✅ daily_review, nightly evolution, report card | AI-*written* prose report (LLM, 1 call/day) |
| 6 | Strategy Lab | ✅ backtest, simulator, replay | brainstorm conversation on top |
| 7 | AI Analyst / Radio | ✅ Voice v0.x + briefing() (consumer-only) | richer language; cadence stays engine-driven |
| 8 | AI Planner | 🟡 expiry/gamma awareness exists | economic-event calendar (CPI etc.) not connected |
| 9 | AI Developer | ❌ new — the Design Studio proposal (#013 in PROPOSALS.md) | fully LLM |
| 10 | AI Commander | ✅ market_service orchestration + execution gate is the Chief today | LLM never becomes the Chief for trade decisions |

**Key honest point:** the "Agents" (Market/Options/Greeks/Liquidity/Risk/…)
already exist — they are the scoring modules; the execution gate is the Chief
AI. They report numbers, not language. The genuinely new build is a **language
layer on top**, powered by the Claude API — not a replacement of the engine.

## Cost-safe 3-tier architecture (design law for the build)

| Tier | Cadence | Runs on | LLM? |
|---|---|---|---|
| 1. Decision engine | per tick (seconds) | existing deterministic modules | **NEVER** — cost, latency, auditability, offline-safety |
| 2. On-demand | when owner asks | Q&A, Strategy Lab chat, Developer assistant, "explain this verdict" | Claude API per request (≈ ₹5–15/call) |
| 3. Scheduled | 2–4 calls/day | morning plan (Engine 8), EOD learning report (Engine 5), radio-script polish | Claude API |

Per-tick multi-agent LLM calls are rejected: ~780 ticks/day × N agents would
cost lakhs/month and put an internet dependency inside the trading loop.
The radio keeps speaking every 30s from the deterministic engine (as today);
the LLM upgrades the *language*, never the *decision*.

## Build phases (after API key + queue clears)

- **Phase A** — `ai_layer.py` foundation: Anthropic SDK, `claude-opus-4-8`,
  system prompt = doctrine + QUALITY.md, daily cost cap, kill-switch for the
  AI layer itself (engine unaffected if disabled). One consumer: EOD report.
- **Phase B** — Conversational brain: `brain.answer()` falls back to LLM with
  published-state-only context (Voice law preserved: dashboard thinks, LLM
  phrases). Tanglish.
- **Phase C** — Developer assistant (Engine 9 / Design Studio) + Strategy Lab
  chat + morning Planner.
- **Phase D** — Research Engine depth: only after historical data exists.
