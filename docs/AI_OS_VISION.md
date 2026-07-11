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

---

## vNext refinement (owner, 2026-07-11) — FAIOS + AI Council

**Target name: Cloud AI Trader Explorer → Financial AI Operating System (FAIOS).**

Owner's architecture correction, now LOCKED as the #013 core law:

> Explorer must NOT "become ChatGPT". It becomes an **AI Operating System
> that USES an LLM**. Trading decisions (BUY/WAIT/NO TRADE, Entry/Exit/SL)
> come only from the deterministic Decision Brain. The LLM only:
> Explain · Research · Compare · Teach · Review · Summarize · Q&A · Reports.

### 10-Layer map (owner) → implementation

| Layer | Owner name | Maps to |
|---|---|---|
| 1 | Market Intelligence | existing data layer (news feed pending) |
| 2 | Decision Brain | existing engines + gate — **LLM-free forever (Tier 1)** |
| 3 | LLM Intelligence | Phase A/B `ai_layer.py` (Claude API) |
| 4 | AI Radio | existing Voice; cadence engine-driven, LLM polishes language only |
| 5 | AI Research Lab | Tier 2 Q&A; historical-depth questions ("2023-ல் எப்படி?") need historical data first (Phase D) |
| 6 | AI Developer | Phase C (Design Studio / Engine 9) |
| 7 | AI Teacher | **new module** — Training-mode Q&A ("ஏன் WAIT? Gamma எப்படி?"); natural fit on top of existing professor endpoint; Tier 2 |
| 8 | AI Memory | existing ledgers/module_stats + conversational recall (Tier 2) |
| 9 | AI Planner | Tier 3 scheduled: Morning Brief, EOD Review, Weekly Improvement, Monthly AI Performance Audit |
| 10 | AI Operating System | orchestration: Live Data → Decision Engine → Memory → LLM → Radio → Dashboard |

### AI Council (new module, owner)

Market/Options/Liquidity/Risk/News/Strategy/Developer/Voice AIs each report;
**Chief AI reads all and gives a Final SUMMARY — never a Final Decision.**
Rulings:
- Council members = existing deterministic modules' outputs, narrated by the
  LLM per domain. The numbers come from the engine; the LLM writes the words.
- Chief AI output is Tier 2/3 (on-demand "council meeting" button + the
  scheduled Planner reports) — never per-tick, never in the decision path.
- If Council summary and execution gate ever disagree, the gate wins and the
  disagreement is displayed honestly (same MODE Two-Layer law).

### Planner cadence (Layer 9, locked)
Morning Brief (pre-open) · EOD Review (post-close) · Weekly Improvement
Report · Monthly AI Performance Audit — 2 LLM calls/day + 1/week + 1/month.

---

## AI Cortex refinement (owner, 2026-07-11 — 3rd iteration)

### Three-way separation (LOCKED)
- **Dhan API** → brings market data (eyes)
- **Decision Engine** → computes the market, alone decides BUY/WAIT/NO TRADE (spine)
- **LLM** → thinks, explains, researches, reviews, plans (cortex — never the spine)

### LLM provider (owner named Gemini)
Owner's message names the **Gemini API** for the cortex slot. Design ruling:
`ai_layer.py` is built **provider-agnostic** behind one interface
(`cortex.ask(role, structured_context, question)`), so the slot can hold
Gemini or Claude — whichever API key the owner creates decides Phase A's
provider; switching later is a config change, not a rebuild. Cost/quality
comparison presented at build time. The unlock remains the same: **owner
must create the API key** (Google AI Studio for Gemini / platform.claude.com
for Claude); assistant cannot create accounts.

### Structured AI Context law (LOCKED)
The LLM never receives raw market data. It receives only the engine's
published, structured snapshot (trend/score, liquidity/score, OI build-up,
PCR, VWAP side, Decision + blocking reasons, module_stats, verdict-ledger
numbers). This is the existing Voice/Rule-10 published-state law extended to
the cortex: **one state → one source → one truth → LLM is a consumer.**

### Master Prompt (owner, recorded — basis of ai_layer system prompt)
> You are the AI Cortex of Cloud AI Trader Explorer. You are not the trading
> engine. You never generate BUY or SELL decisions independently. You only
> use verified outputs from the Decision Engine. Responsibilities: explain
> the market; research better ideas; review completed sessions; teach the
> user; generate voice commentary; suggest software improvements; create new
> research proposals; learn from validated history. Never fabricate market
> data. Never override the execution gate. Every recommendation must include
> reasoning and confidence. Any strategy change requires human approval
> before production.

### New modules (this iteration)
| Module | Scope | Honest cadence ruling |
|---|---|---|
| **AI Architect** | Full software audit: architecture, code quality, performance, memory, security, API usage, AI quality, trading quality | Daily full-repo audit is token-expensive; scoped to **weekly + on-demand**, fed a repo summary + metrics (not the whole codebase per call). Findings → PROPOSALS.md, never auto-applied. |
| **AI Research Center** | Autonomous research: SMC, Wyckoff, order flow, gamma/dealer positioning, market profile, auction theory, liquidity concepts, academic papers → produces test/reject/adopt proposals | Needs web-search capability in the cortex call. Output = proposals only; enters the Improvement flow below. |
| **AI Improvement Engine** | Observe → Research → Idea → Simulation → Backtest → Proposal → **Human Approval** → Production | This IS the existing Phase-22 pipeline with LLM-generated candidates upstream. AI never touches production directly (owner-locked, re-affirmed). |

---

## #014 AI Cortex Integration (owner, 2026-07-11)

Owner ruling: one LLM API used as an OS — many role-scoped agents behind an
Orchestrator, not one chatbot doing everything.

### 10 role-agents (each = a role prompt + the structured snapshot, one API)
1. **Orchestrator (Chief)** — only agent that talks to the user; routes to the others
2. **Market Analyst** — summary/trend/structure/liquidity/momentum/price-action narration
3. **Decision Explainer** — turns the gate's WAIT/BUY/NO-TRADE into plain language
4. **Research** — SMC/Wyckoff/ICT/gamma/auction/papers — research only, no decision
5. **Learning** — daily/weekly/monthly review prose
6. **Developer** — dashboard/perf/duplicate/slow-API/UI review
7. **Architect** — whole-software audit (weekly + on-demand)
8. **Voice** — radio; knows no decision, speaks only what Orchestrator hands it
9. **Teacher** — concept Q&A (BOS, liquidity sweep, Greeks…)
10. **Planner** — morning brief / close report / weekly plan
+ **Improvement** — Observe→Research→Idea→Sim→Backtest→Proposal→**Approval**→Production

### 10 infra modules (the actual code in ai_layer)
| Module | Job |
|---|---|
| AI Orchestrator | route user/schedule requests to the right role-agent |
| Agent Manager | registry of role prompts + their allowed context slices |
| Context Builder | assemble the published structured snapshot (Rule-10) — **raw candles never sent** |
| Prompt Manager | versioned system+role prompts (Master Prompt is the base) |
| Memory Manager | conversational recall over existing ledgers/module_stats |
| Voice Manager | hand engine-published lines to TTS (consumer-only) |
| Research Manager | web-research calls + proposal capture |
| **Cost Controller** | per-agent + daily call/token caps; a Council/Planner run ≈ 10 calls — **not optional** |
| **Safety Layer** | hard-blocks BUY/SELL/SL/strike/override at the code boundary, not via prompt trust |
| **Human Approval Layer** | = existing Phase-22; Improvement AI feeds it, never writes production |

### Snapshot contract (owner-provided JSON shape, locked as the Context Builder output)
```json
{ "market": {"trend","trendScore","liquidity","liquidityScore","structure","decision"},
  "blockers": [...], "confidence": N, "reason": [...] }
```

### Hard NOs (Safety Layer, code-enforced)
No BUY · no SELL · no Stop Loss · no Option-Strike selection · no gate override.
### Allowed
Explain · Review · Research · Compare · Teach · Reports · Voice commentary ·
Developer suggestions · Proposal generation.
