# Cloud AI Trader V7.0 — Status

```
Cloud AI Trader V7.0
STATUS : FEATURE COMPLETE

Mode:
✔ Bug Fixes
✔ Stability
✔ Optimization

No New Features
```

Declared by owner, 2026-07-27, commit `4e8d6b3`. All 10 roadmap steps
shipped (see `docs/RELEASE_NOTES_v7.0.0.md`). Git tag `v7.0.0-final` held
back by owner choice — not yet created.

## Pre-V8.0 checklist (must complete before any V8.0 work starts)

Live observation phase, owner decision 2026-07-27. Nothing in this list is
scoped as "done" until the owner has actually run it against a live,
broker-connected session — most items need real market data or real audio
output, neither of which existed in this session's off-hours verification.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | 2-3 days live-market observation | ⏳ Not started | Needs market open + owner watching |
| 2 | Full trading in Broker Connected mode | ⏳ Not started | Owner enters credentials via Settings |
| 3 | Bug fixes only (no scope creep) | Standing rule | Applies for the whole observation phase |
| 4 | Performance profiling | ⏳ Not started | Can be assisted once live logs exist |
| 5 | False-signal check | ⏳ Not started | Needs live signal history to audit |
| 6 | Voice narration verification (live, audible) | ⏳ Not started | Off-hours session verified the *text* (`brain._ai_dealer_speech()`, 3 synthetic scenarios) and that the UI shell renders — actual spoken audio in a real browser session with sound enabled is unverified |
| 7 | Memory-leak / API-latency check | ⏳ Not started | Needs sustained live runtime to observe |

## Bugs found & fixed during this phase

| Date | Bug | Root cause | Fix |
|------|-----|-----------|-----|
| 2026-07-27 | Live site rendered as unstyled plain HTML, "WS OFFLINE" badge, everything stuck on "Loading…" | A `next dev` scratch instance (for a regression-test browser check) was run from the live frontend's own directory, silently overwriting the production `.next` build with dev-mode artifacts. The already-running server kept serving HTML referencing the old (now-deleted) hashed asset filenames — every CSS/JS request 400'd for real visitors. | Proper `npm run build` (confirmed `BUILD_ID` present + correctly hashed chunks) + frontend-only restart (`launchctl kickstart`, owner-approved). Verified: all assets 200, dark theme renders, WS badge green. |
| 2026-07-27 | Hero's Multi-Timeframe row never showed "1H" (5m/15m/4H/Daily only), confirmed on the owner's first live market-open session | `mtf_confluence.py` resampled 1H bars from `state.candles`, hard-capped at 600 one-minute bars (10h) in `market_service.py`. A 1H timeframe needs 30 complete bars (1800 min / 30h) to satisfy `_MIN_BARS` — 3x more than the cap can ever hold. 1H was structurally unable to ever reach "ready", on any day. | New `mtf_1h_cache.py` (real 60-bar 1H fetch, 10 min TTL) mirroring the existing 4H cache pattern, wired into the same scanner loop. `mtf_confluence.py` now takes 1H from this direct fetch instead of resampling. Verified: synthetic test confirms 1H reaches `ready: True` independent of the 1m buffer's cap; old resample path reproduced showing only 10 bars (the bug). **Deployed via a backend restart the owner performed independently mid-session (~15:01 IST) — confirmed live: `mtf.timeframes` now includes 1H, all 7 timeframes present.** |
| 2026-07-27 | AI Dealer's "WHY BUY" list showed a false "✓ MTF Alignment" checkmark even when the Hero had no directional bias at all (confirmed live: `alignment_pct` was `None` at the exact moment the checkmark showed) | `decision_contract.py`'s `_ai_dealer()` gated this item on `mtf_ready` alone (enough candle bars exist), not on whether the Hero actually had a BULL/BEAR bias to check timeframes against. `mtf_confluence.py`'s `higher_tf_conflict` short-circuits to `False` when there's no hero bias ("nothing to conflict with"), which this code read as "aligned" instead of "unmeasurable" — violating this project's own "○ means not-yet-measurable, never fabricate ✓/✗" doctrine. | Changed the gate to `mtf.get("alignment_pct") is not None` (only set when a real hero bias existed to compute against). Verified 3 scenarios: no-bias → `ok: None` (was wrongly `True`); genuine alignment → still `True`; genuine conflict → still `False`. Scoped only to this one AI Dealer item — Hero card and Evidence Panel already independently required a resolved bias before rendering anything, so they were never affected. **Deployed via the owner's backend restart later the same day — confirmed live.** |
| 2026-07-28 | `FeedDiagnostics.tsx`'s "FEED" badge inconsistently showed a calm "🟡 PAUSED — not a data problem" message or an alarming "🔴 0%" itemized red view for the exact same closed-market condition, depending only on restart timing | The component's own stated intent ("a closed market must never read as a red data-quality alarm") only exempted `MISSING` status, not `DELAYED`. Backend checks (`_check_quotes`, `_check_signals`, etc.) report `MISSING` when a value was never received this run, but `DELAYED` once a real value was received and then ages past its own threshold — exactly what happens to last-known quotes/signals once the market closes and a prior session's values just sit there aging. Right after a restart (empty state) → MISSING → exempted → calm message. Any time after that during the same closed period → DELAYED → not exempted → alarming view. Confirmed the actual gate-relevant `data_quality` (Kill Switch/Safe Mode/Risk Approval) already has correct closed-market awareness and was unaffected — purely a secondary diagnostics-panel display bug. | One-line fix: exempt `DELAYED` the same way `MISSING` already is, when `market_open === false`. Verified via `tsc` (clean) and 4 isolated logic scenarios: closed+mixed-MISSING/DELAYED → no false alarm (was the bug); open+same statuses → still correctly flags real issues (no regression); closed+all-OK → still calm; open+`CORRUPT` → still always flagged (never exempted, since that's genuinely bad data, not an absent feed). **Code fixed and verified; not yet deployed (awaiting the next restart).** |
| 2026-07-29 | AI Analysis card's NEXT field cut off mid-sentence ("Market close a") and WATCH/CHANGE showed bare "—" placeholders, confirmed live and stayed that way for 26+ minutes (`cached 1567s`) | A rare truncated/incomplete Gemini reply (confirmed NOT a chronic token-budget issue — a fresh forced call and the last 10 real calls all completed fully using only 40-130 of the 700-token budget) got cached under `analysis.py`'s decision-state `key` the same as a good reply would. That cache has no TTL of its own — it's only re-checked when the decision state changes or the 180s throttle passes — so one rare bad generation could replay for as long as the decision stayed the same. Root cause was "bad response cached forever," not "Gemini can't generate enough text." | Added `_is_complete()`: validates all 4 expected keys (`why`/`next`/`watch`/`change`) are present AND each value is non-empty, not a `—`/`-` placeholder, and at least 10 chars (a truncated fragment or placeholder won't clear this; a real sentence always will). Only a complete reply gets cached; an incomplete one is still returned once (best available right now) but not persisted, so the next request gets a fresh retry. Verified: 4 isolated `_is_complete()` scenarios (complete → cache; missing keys → don't; empty/dash placeholders → don't; tiny truncated fragment → don't) plus a full mocked `analyze()` run confirming the 3-call sequence (incomplete → not cached → retried fresh → complete → cached → served from cache on the next call). **Follow-up same day (owner suggestion):** also check the provider's own finish/stop reason (`resp.candidates[0].finish_reason` for Gemini, `msg.stop_reason` for Anthropic — confirmed both fields exist in the installed SDKs) — `MAX_TOKENS`/`SAFETY`/etc now block caching even when the parsed blocks happen to superficially look complete (all 4 keys present, decent length), which pure block-completeness checking alone would miss. Verified: 7 finish/stop-reason classifications (Gemini STOP/MAX_TOKENS/SAFETY, Anthropic end_turn/max_tokens/stop_sequence, and unknown/None defaulting safely to not-truncated); a synthetic "sneaky truncated" case (blocks look complete, `finish_reason=MAX_TOKENS`) correctly still blocks caching; a real live Gemini call with a deliberately tiny `max_tokens=15` reproduced genuine truncation end-to-end (`finish_reason: MAX_TOKENS`, visibly cut-off text); a normal real live call confirmed `finish_reason: STOP` / not truncated. **Code fixed and verified; not yet deployed (awaiting the next restart).** |
| 2026-07-27 | During the owner's first live session, a broker rate-limit cooldown (a pre-existing, working, correctly-triggered protection mechanism) displayed as the vague "🟠 Broker issue — retrying automatically" instead of the intended "⏳ Rate limited by broker — pausing briefly, will resume". Same root cause independently affected the Settings page's Save & Connect error message if attempted during a cooldown. | Two classifiers (`market_service.py`'s `_friendly_error()` and `frontend/lib/status.ts`'s `friendlyMessage()`) checked for the phrase `"rate limit"` (space) but the actual cooldown exception says `"Broker rate-limit cooldown..."` (hyphen) — a pure string-match miss, present since before this session. `ProChart.tsx`'s own classifier already had a `"cooldown"` fallback and was unaffected. | Broadened both classifiers to also match `"rate-limit"` and `"cooldown"`. Verified: both known cooldown message variants (`dhan.py`'s hyphenated cooldown message and its space-separated 429 message) now correctly classify as `RATE_LIMIT`. Frontend `tsc` clean. **Code fixed and verified; deploy held for the same upcoming restart as the 1H fix above (frontend-only change, no restart urgency beyond that).** |
| 2026-07-31 | System Verify's headline health score reads "75% Degraded" every single pre-market/closed-market morning, even though nothing is actually wrong — confirmed live on a Friday pre-open screenshot (08:30 IST, market opens 09:15) | `system_verify.py`'s score is computed only from 4 subsystems marked `core=True` (Backend/Decision Engine/Memory/AI Cortex): `ok_core = sum(1 for s in core_subs if s["status"] == "ok")`. Decision Engine's status correctly becomes `"paused"` (not `"ok"`) when the market is closed — but the score formula treated `paused` exactly like a failure, not like the module's own stated design ("paused/off on a closed market... is expected, not a fault", the note shown directly under the misleading score). Math confirmed the bug exactly: 3 of 4 core subsystems `ok` (Decision Engine `paused`) → 100×3/4 = 75 → `score >= 60` bucket → "Degraded". | Broadened the score check to `status in ("ok", "paused")` — deliberately NOT including `"building"` (Decision Engine still warming up while the market IS open), which stays a real signal that should still count against the score. Verified two scenarios: market-closed (Decision Engine `paused`) → 100%/Stable (was 75%/Degraded); market-open-but-warming-up (Decision Engine `building`) → still correctly 75%/Degraded, unchanged. No trading impact — pure observability score, doesn't touch any gate/decision/size. **Code fixed and verified; not yet deployed (awaiting the next restart).** |
| 2026-07-31 | Signal Maturity panel showed a big "NOT READY" badge with "Ready · threshold 61" on the very next line for the SAME setup (maturity 82/100), confirmed live during a real NIFTY session (09:23 IST, decision WAIT) | `signal_maturity.py` has two independent state machines that happen to share vocabulary. `entry_trigger.status` (the badge) correctly returns "NOT READY" whenever there's no active directional BUY/SELL call (`is_dir` false when the engine's decision is WAIT/NO TRADE), regardless of maturity. `stage` (the line underneath) is `_stage(maturity)` — a PURE numeric-score band with zero awareness of `is_dir`, using the words Immature/Developing/Preparing/Armed/Ready. At maturity 82 (≥81), `_stage()` returns "Ready" — same word family as the badge, opposite verdict, both describing the same number. "Preparing" and "Armed" collide the same way at other maturity levels (`status` also uses those exact words). The underlying gating logic was always correct; only the two labels' overlapping vocabulary was the problem. | Renamed `_stage()`'s band words to a vocabulary that cannot collide with `status`'s words: Immature → Developing → Building → Strong → Peak (was Preparing/Armed/Ready). Verified `_stage()` is display-only (single consumer, `SignalMaturity.tsx` line 41; no other code depends on the exact string) before renaming — confirmed no logic path reads these words. Verified new bands render correctly across the full maturity range (15→Immature, 30→Developing, 50→Building, 70→Strong, 82→Peak, 95→Peak). No trading impact — pure display wording, the actual NOT READY/READY/ARMED gate status is untouched. **Code fixed and verified; not yet deployed (awaiting the next restart).** |
| 2026-07-31 | AI Timeline's empty-state message read "Quiet on a closed market" while the market badge read "MARKET OPEN · ACTIVE MARKET" and NIFTY was visibly ticking live (24,345.75, +28.6) — confirmed on the same live screenshot, 09:50 IST, 35 min into the session | `AITimelineCard.tsx`'s zero-events message was a single hardcoded string, unconditional on actual market state — it always claimed "Quiet on a closed market" whenever `events.length === 0`, regardless of whether the market was open or closed. Zero timeline events during an open-but-quiet morning (Decision Engine had stayed WAIT the whole session, no trend/structure/liquidity transition yet) is not itself a bug — but asserting the market was closed when it plainly wasn't is a factual display error. | Added the same `status.market_open` check `FeedDiagnostics.tsx` already uses (`useMarket()` from the shared store) and made the closing sentence conditional: "Quiet on a closed market." only when `market_open === false`, "Quiet so far today." when the market is open with genuinely zero events yet. Verified via `tsc` (clean) and isolated logic check of both branches. No trading impact — pure display copy, doesn't touch what triggers a timeline event. **Code fixed and verified; not yet deployed (awaiting the next restart).** |
| 2026-07-31 | AI Analysis (Gemini) said "trend data null" and "key levels null" in its WHY/WATCH text at 12:35 IST, while the same dashboard showed live Trend ✓ BULLISH (83), Structure ✓ BREAKOUT, and full CPR/VWAP levels via the AI Decision Matrix — confirmed the Gemini output was being honest about broken input, not hallucinating | `context_builder.py`'s `_layer_tag()`/`_layer_score()` (the ONLY bridge from the engine to the LLM, per the file's own Rule 10 docstring) looked up top-level keys `"Trend"`/`"MTF Trend"`/`"Liquidity"`/`"Order Flow"`/`"Structure"`/`"Market Structure"` directly under `state.intelligence.layers`, and inside them, fields named `label`/`state`/`status`/`verdict`/`score`/`value`/`pct`/`strength`. NONE of these key names or field names have ever existed there — the raw per-engine dicts are keyed lowercase (`trend`, `structure`, `order_flow`) with entirely different fields (`score_bull`/`score_bear`, `direction`, `score`). The names `"Trend"`/`"Structure"`/`"Liquidity"` only exist as `layer` entries inside `layers.intelligence.decision_matrix.rows` — the same nested path `opportunity_metrics.py`, `decision_contract.py`, and `risk_approval.py` already correctly walk elsewhere in this codebase. Net effect: `market.trend`/`trendScore`/`liquidity`/`liquidityScore`/`structure` have been `null` in every single Gemini call this feature has ever made, since the file was written — `decision`/`blockers`/`confidence`/`reason` were unaffected (they read from different, correctly-wired state paths). | Rewrote `_layer_tag()`/`_layer_score()` to read from `layers.intelligence.decision_matrix.rows` by `layer` name (matching the same rows structure already correct elsewhere), pulling each row's own `reason` text (tag) and `score` (numeric) — the exact same values already shown on the AI Decision Matrix panel, not a new derivation. Verified against a mocked state mirroring the live screenshot exactly (Trend/83/BULLISH, Structure/79/BREAKOUT, Liquidity/60/buy-side) — all 5 fields now populate correctly with the dashboard's own numbers; also verified a fully-empty state still gracefully returns `null` for all 5 (never fabricates) rather than crashing. No trading impact and no doctrine change — Gemini still only explains an already-published decision, per Rule 10; this only fixes what real data it gets to explain with. **Code fixed and verified; not yet deployed (awaiting the next restart).** |
| 2026-07-31 | AI Decision Matrix showed "Futures – Neutral On" as a standalone row label, confirmed live at 15:14 IST — reads like a truncated sentence fragment | `futures.py:74` sets `relation = "NEUTRAL ON"` by design, but ONLY as a mid-sentence fragment for its own `notes.append(f"Futures {relation.lower()} the bullish signal")` construction — "Futures neutral on the bullish signal" is a complete, grammatical sentence there. `intelligence.py`'s `_decision_matrix()` separately reuses the same raw `relation` string standalone (`.title()`'d alone) for the Futures row's reason text. `CONFIRMS`/`CONTRADICTS` happen to also read fine as standalone single words, which is exactly what masked this until the `NEUTRAL ON` case was hit — it has no missing preposition problem in the sentence context, but reads as an incomplete fragment on its own. | Special-cased `NEUTRAL ON` → `"Neutral"` at the one place it's used standalone (`_decision_matrix()`'s Futures row); `futures.py`'s own relation value and sentence-building are completely untouched, so the "Futures neutral on the bullish/bearish signal" note text is unaffected. Verified all 5 possible relation values (`CONFIRMS`/`CONTRADICTS`/`NEUTRAL ON`/`NO ACTIVE SIGNAL`/`None`) render correctly through `_decision_matrix()` directly — only the one broken case changed, the other four are byte-identical to before. No trading impact — the Futures row's numeric `score` (which does feed the gate) is completely unchanged; only the reason text shown to a human changed. **Code fixed and verified; not yet deployed (awaiting the next restart).** |

### Today's bug family (owner's own classification, 2026-07-31)

Of the 5 bugs above, 4 are the same species: **correct logic → wrong
presentation** ("Display Honesty" / "Display Semantics" — System Verify,
Signal Maturity, AI Timeline, Futures label). Only one (AI Analysis
Context) is a genuine data-plumbing bug. **No bug was found in the core
trading engine, risk gate, or Hero decision today** — everything found
sharpens how a correct decision is *explained*, not the decision itself.
That lines up exactly with the observation phase's own purpose.

**Deferred design candidate — a presentation-mapping layer** (owner's
suggestion; NOT built now, this is new architecture, not a bug fix): the
Futures label bug happened because one internal enum value (`"NEUTRAL
ON"`, `futures.py`) was reused directly as a UI label in a different file,
after being designed only for one specific sentence template. A small
internal→display mapping layer (e.g. `CONFIRMS→"Confirms"`,
`CONTRADICTS→"Contradicts"`, `NEUTRAL_ON→"Neutral"`) at each such boundary
would make this whole bug *class* structurally harder to reintroduce —
internal values could then evolve independently of what's shown to a
trader. Worth considering as a small hardening pass sometime after the
pre-V8 checklist, not urgent enough to justify new code during the
bug-fixes-only phase now.

### New process rule — Fresh Session Verification (owner, 2026-07-31)

Before any suspected display bug is declared "confirmed" and fixed, verify
in a genuinely fresh session first — same tab + hard refresh isn't always
enough to bust a Service-Worker-controlled cache (this app registers one,
`cat-shell-*`, for PWA/offline support). Escalate in this order until the
behavior either reproduces or clears:

1. Same tab, hard refresh (Cmd/Ctrl+Shift+R).
2. Brand new tab.
3. Incognito/private window (guarantees no inherited SW/cache state).
4. Only then — code inspection.

**Why this matters, in the owner's own framing:** a suspicious behavior
can come from two completely different places that must be diagnosed
separately —
```
Application  → Correct
Verification → Incomplete
```
vs.
```
Application  → Incorrect
Verification → Correct
```
Both look identical from the outside ("the bug is still there"), but only
one of them is fixed by changing code. Confusing the two costs a wasted
fix or an unfixed real bug — telling them apart *before* touching code is
what non-fabricated debugging discipline (Evidence → Reproduce → Verify →
Root Cause → Fix) is actually for.

**Observation Log entry format for a closed-no-fix case** (owner's own
template — use this whenever a suspected bug turns out to be verification-
side, so a later audit can tell "fixed" apart from "false alarm" at a
glance):
```
Observation #X
Suspected: <what looked wrong>
Evidence: <what confirmed vs contradicted it>
Root Cause: <application bug | stale client state | other>
Fix: <what changed, or None>
Status: Closed - No Code Change   (or: Fixed, Verified)
```

**Case closed under this rule, 2026-07-31 — AI Timeline "closed market" report:**
```
Observation: AI Timeline showed "Quiet on a closed market" during live
             market-open hours (MCX:GOLD, 21:09 IST)
Evidence:    ✓ /api/status returned market_open: true (confirmed via curl
               and via a live fetch() from inside a fresh browser session)
             ✓ A brand-new, never-before-loaded browser tab against the
               same running frontend showed "Quiet so far today" — the
               CORRECT post-fix text — on the very same build (7ae15ab)
Root Cause:  Stale client session in the tab being screenshotted from —
             likely pre-dating the backend/frontend restart, with a
             Service-Worker-controlled cache outliving an ordinary hard
             refresh. NOT an application defect.
Fix:         None
Status:      Closed — Verified, No Code Change Required
```

## Open observations — evidence collecting, deliberately NOT fixed yet

Owner decision 2026-07-30: these are real, code-confirmed findings, but the
trigger/impact isn't proven enough yet to justify a change. Collect more
sessions of evidence first, then decide. Recording them here so they're
tracked rather than re-derived from scratch each session.

### OBS-1 — Stale-episode reaper has no independent timer (HIGH priority)

**Confirmed in code:** `opportunity_metrics._sweep_stale()` is reachable from
exactly two places — inside `record()` (per radar tick, 60s-throttled) and
`_restore_open()` (restart only). There is no standalone timer. So whenever
the premium radar stops calling `record()`, stale episodes accumulate with
nothing able to clear them, and the Measurement Health card sticks on
DEGRADED indefinitely.

**Observed 2026-07-29 (~17:0x IST):** `open_episodes: 10, open_stale: 10,
status: DEGRADED`, byte-identical when re-read 75s later — a 60s sweep
should have fired at least once in that window. Self-cleared later (now
HEALTHY / 0 stale), and the backend restart reset the counters.

**Hypothesis, NOT proven:** broker rate-limit cooldown (429s were recurring
every 3-10 min that day, cooldowns escalating toward the 300s cap) starves
the option-chain fetch → radar stops ticking → reaper starves. The dashboard
keeps showing the last-known frozen track list, which makes the radar *look*
like it's still running. Ruled out along the way: `_close_episode()` cannot
throw and strand an episode (it swallows its own persistence errors).

**Evidence still needed before fixing:** does it recur? how often? does each
occurrence line up with a broker cooldown window? Only on repeat occurrence
does adding an independent reaper timer become the right call — fixing it
now would be treating a hypothesis as a diagnosis.

**Impact if it recurs:** measurement/display only. It does not touch any
gate, decision, or sizing — Measurement Health is an observability card.

**Session log:** 2026-07-30 (expiry) — **did NOT recur.** Measurement
Health stayed HEALTHY all session (22 open / 0 stale at 15:27 IST). One
clean session against it; still need more before concluding either way.

### OBS-2 — Execution Lock / Calibration gate is near coin-flip (HIGH priority)

**Measured, from the gate's own tracker (2026-07-30):** `1106 blocks ·
saved 58% / missed 42% · solo-missed 51%`. On 2026-07-30 the radar caught
several large moves early that this gate blocked — 77900 CE +292%, 77800 CE
+244.8%, 77700 CE +191.9%, 77600 CE +151.2% — with the day tallying
`MISSED 6 · PROFIT LOST +160 pts · TOP BLOCKER: Execution Lock`. The
underlying cause is Calibration sitting at 54 against a ≥55 threshold, and
calibration scoring has been FROZEN since 2026-07-23 (owner), so it cannot
self-recover.

**Deliberately NOT changed.** Threshold changes are Trading Doctrine and
require the full Observation→Evidence→Proposal→Approval pipeline. Owner
decision: collect 2-3 more trading sessions, then compare Win Rate, Profit
Factor, Drawdown, False Entry rate and Missed Winner rate before any
proposal is even drafted. No auto-tuning, ever.

**Session log — the numbers are volatile intraday, which itself argues for
patience:**

| When | Blocks | Saved | Missed | Solo-missed | Day tally |
|---|---|---|---|---|---|
| 2026-07-30 ~11:12 | 1106 | 58% | 42% | 51% | 6 missed, +160 pts |
| 2026-07-30 ~15:27 | 1581 | **67%** | **33%** | 51% | 13 missed, +340 pts |

Within a single session the saved/missed split moved from 58/42 to 67/33
(+475 blocks). Reading a verdict off any single snapshot would have been
wrong in both directions — exactly why the 2-3 session rule is right.
A second, separate gate is also now accumulating data worth watching:
`Premium: AVOID — saved 76% / missed 24% · 598 blocks`.

### OBS-3 — Frontend/backend version gap (LOW priority, intentional)

Backend is on `6e7c411`; frontend is still on `4cd3884`, so the
FeedDiagnostics closed-market fix (`60ccdfe`) isn't live yet and the
Build Version badge correctly reads ⚠ mismatch. Deployment-only, zero
trading-logic impact — deliberately deferred to one batched frontend
rebuild + restart at the end of the observation phase.

### OBS-4 — Live false-signal + performance tracking (owner-added 2026-07-30)

Two tracking asks, no code change:
- **False signals:** Hero BUY → SL hit · Hero BUY → TP hit · WAIT → large
  move missed · BUY → no follow-through. Note: with Execution Lock blocking
  every entry (OBS-2), the only live category currently producing data is
  "WAIT → move missed" — the other three need the gate to actually open.
- **Performance:** memory leak, CPU, API latency, WebSocket stability,
  response time. Partly overlaps the pre-V8 checklist items 4 and 7 above.

### OBS-5 — AI Learning Dataset (owner-added 2026-07-30) — MOSTLY ALREADY BUILT

Owner asked to record every opportunity's full context so V8 can mine
patterns from 500-1000 samples. **Audited before adding anything: this is
~80% already built and running.** `opportunity_metrics._black_box()` writes
one JSON line per opportunity episode to `data/opportunity_log/*.jsonl`,
with an `engine` snapshot joining live Decision Engine state.

**Verified against real data, 2026-07-30:**

| Owner's field | Status in the black box |
|---|---|
| Hero Decision | ✅ `engine.decision`, `engine.grade`, `engine.confidence` |
| Evidence | ✅ `engine.layers` — all 11 layer scores + `root_cause` verdict |
| Market Structure | ✅ score via `layers.Structure` (label itself not stored) |
| MTF | ✅ `layers.MTF` |
| Greeks | ⚠️ composite `layers.Greeks` score only — no raw δ/γ/θ/vega/IV |
| Gamma | ⚠️ partial — no gamma-wall level stored |
| OI | ✅ `layers.OI` + `engine.pcr` |
| CPR | ❌ hardcoded `None` — IEIE Phase 1, never built |
| VWAP | ✅ `engine.vwap` (+ `adx`, `atr`, `underlying`) |
| Entry | ✅ `base`, `alert_prem`, `ideal_prem`, `entry_edge`, `ideal_wait_s` |
| Exit | ✅ `peak`, `t_exhaust`, `close_reason` |
| SL / Target | ❌ not joined into the episode record |
| P&L | ✅ `potential` / `captured` / `lost` (premium points) |
| Result | ✅ `outcome`, `capture`, `traj`, `reason`, `stability` |

Also captured beyond the ask: `dte`, `expiry_day`, `session_type`
(NORMAL/EXPIRY/BUDGET), `regime` (TRENDING/VOLATILE), `ignite_path`,
`delay_s`, `validation_bucket`, and six lifecycle timestamps
(coil/move_start/ignite/runner/peak/exhaust).

**Volume — the important correction.** 3,829 total records exist, but only
**1,414 (37%) are usable for pattern-learning.** Everything before
2026-07-22 has an empty `engine.layers` — the join path was silently broken
(logged in-code: "0 of 2363 black-box lines carry layer context") until the
2026-07-21 fix. Only post-fix records carry decision context. At ~170-310
usable records/session, 500-1000 more samples is roughly **3-6 more
sessions**, not months.

**Second correction — these are OPPORTUNITIES, not executed trades.** The
system never places orders, and Execution Lock has blocked every entry, so
realized-P&L trade count is zero. The dataset measures what the radar saw
and what the engine decided, including the counterfactuals (blocked moves
that then ran) — arguably better for pattern-learning than a trade-only
log, but it should not be described as a trade dataset.

**Genuine gaps to close in V8** (all new code ⇒ deferred, V7 is frozen):
CPR / RSI / EFI (the deferred IEIE Phase 1 fields, currently hardcoded
`None`), raw Greeks values, gamma-wall level, and joining planned SL/Target
into the episode record.

### OBS-6 — Minimum-tick (₹0.05) options distort percentage statistics (MEDIUM)

**Found 2026-07-30 (SENSEX expiry day, "Expiry Power Hour").** Percentage
moves are computed off whatever the episode's base premium was, with no
minimum-premium floor — `record()` only rejects `premium <= 0`. On an
option sitting at the ₹0.05 minimum tick, this produces figures that are
arithmetically correct but practically meaningless.

**Verified live:**
- Radar API: `77900 PE — from_low: 0.05, rise_pct: 100.0`. A **five-paise**
  move (₹0.05 → ₹0.10) was classified `🔴 EXPLODING`, scored `Runner 55`,
  and promoted into the PREPARE ZONE, drawing ~7% of AI Attention.
- "BIG MOVERS TODAY" rendered `77900 PE ₹0.05 → ₹397.15 (+7943.0×)` and
  five more in the 1441×-6209× range, all tagged "✗ missed" — headline
  "missed opportunities" that were never realistically capturable at a
  minimum-tick entry.

**Scope is smaller than the display suggests.** In the closed-episode log
only 4 of 484 records today have a base ≤ ₹0.10 (2% of the 162 classed as
runners), and all 4 resolved `outcome: FADE`. So the OBS-5 learning dataset
is only lightly polluted — but the live panels (Big Movers, Premium Radar
zones, AI Attention, runner count) are visibly distorted, worst on expiry
day when many strikes park at the minimum tick.

**No trading impact:** these are radar observations, not gates. Execution
Lock blocked every entry regardless (OBS-2), and nothing here feeds a
decision, threshold, or position size.

**Candidate V8 fix (new code ⇒ deferred under the freeze):** a
minimum-premium floor for percentage classification — e.g. exclude bases
below ~₹1.00 from runner/EXPLODING scoring and from the Big Movers list,
or switch those to absolute-points framing. Needs a declared threshold, so
it belongs in the evidence pipeline, not a quick patch.

## Deferred enhancement — split System Verify into 3 (later 4) indices

Owner proposal, 2026-07-31, explicitly logged rather than built now (new
feature, not a bug fix — held per the rule below). One score currently
conflates two different questions: "is the software healthy" and "can a
trade actually happen right now." Proposed split:

```
System Health      — Backend/Memory/AI Cortex up (the 75%-bug fix's fix)
Trading Readiness  — READY / CLOSED / BLOCKED (market+broker+risk gates)
Research Health    — Weekend AI / black-box logging / calibration state
```

Worked examples from the owner: market closed → System 100%, Trading
CLOSED, Research 100%. Market open, everything fine → System 100%,
Trading READY, Research 100%. Broker disconnected → System 82%, Trading
BLOCKED, Research 94% — i.e. "system is healthy, only trading can't
proceed" becomes visible at a glance instead of one blended number hiding
which part is actually the problem.

Owner also separately noted a 4th index — **AI Readiness** — as a V9-only
extension of this same idea (see `cat-v9-recommendation-ai-vision.md`
memory), not part of this 3-way split.

**Status: logged, not built.** This is new UI/data-shape work, not a fix
to existing logic — out of scope for the current bug-fixes-only
observation phase. Build after the 7-item checklist below is complete (or
if the owner explicitly authorizes it as a scoped exception, the same way
the V8 Research Dashboard was authorized as one during the v8-dev freeze).

### OBS-7 — Opportunity Ladder blends all symbols into one base rate (MEDIUM)

**Found 2026-08-02** during research experiment RVE-001/002 (`v8-dev`,
`research/`). Not a trading-logic bug and not a rendering bug — an
**evidence-integrity** issue, the same family as the AI Timeline / System
Verify / Feed Diagnostics fixes already made this phase.

`opportunity_metrics.outcome_stats()` globs **every** `*.jsonl` in the black
box and pools them into one global reach-rate. `observed_reach_pct()` serves
that to `execution_card._opportunity_ladder()`. There is no symbol filter.
So the ladder shows the *same* percentages regardless of which symbol the
dashboard is currently displaying — confirmed live: every dashboard dump
across a full session read `72/53/29/12/5`, unchanged across NIFTY, SENSEX
and GOLD.

**Why that misleads:** `potential` is measured in *absolute premium points*,
and premium scale differs enormously by symbol. 20 points is a **4.5%** move
on a ₹441 GOLD premium but a **34%** move on a ₹59 NIFTY premium. Measured
reach-rate ordered almost exactly by premium size:

| symbol | median premium | 20pt reach | 50pt reach |
|---|---|---|---|
| NIFTY | ₹59.40 | **13.9%** | 2.1% |
| SENSEX | ₹106.03 | 43.1% | 16.5% |
| GOLD | ₹441.00 | 67.3% | 41.8% |
| CRUDEOIL | ₹505.20 | 60.0% | 26.7% |
| *blended (what the ladder shows)* | — | *27.4%* | *8.7%* |

A trader watching **NIFTY** sees `20pt ≈ 27.4%` when NIFTY's own measured
rate is **13.9%** — roughly double, inflated by SENSEX/GOLD/CRUDEOIL data
mixed in. The 50pt row is worse: 8.7% shown vs 2.1% actual for NIFTY.

**No trading impact:** the ladder is display-only. It feeds no gate, no
decision, no sizing — `_opportunity_ladder()` output is presentational, and
the Execution Lock / Kill Switch / Risk Approval paths never read it.

**Deliberately NOT fixed** (owner decision, 2026-08-02) — log only, same
discipline as OBS-1/2/6. A fix has real design choices that shouldn't be
rushed: filter by current symbol (loses sample size — NIFTY alone has 1,413
alerted vs 3,619 pooled), switch the ladder to percentage-move bands instead
of absolute points (changes what the panel *means*), or show per-symbol and
blended side by side. That's a Trading-Doctrine-adjacent display decision,
not a one-line correction.

### OBS-8 — AI Analysis transient-classification gap (NOT REPRODUCED) (LOW)

**Observed 2026-08-03** on a live dashboard (MCX:CRUDEOIL, Safe Mode active,
broker in rate-limit cooldown). The AI Analysis card read
`AI unavailable — HTTP 500`.

**Confirmed by evidence:**
- Backend returned **no HTTP 500 today**, on any endpoint. Every
  `/api/cortex/analyze` call in the log is `200 OK`, and a live check during
  the investigation also returned 200.
- Gemini itself returned 3 × `400 Bad Request` today — but those are caught
  in `provider.py` and returned to the client as **200 with `ok:false`**,
  never as a 500.
- Also confirmed *working* on the same screenshot: the AI Timeline fix
  (reads "Quiet so far today") and the truncated-reply cache fix (log shows
  `cortex explainer reply truncated (finish_reason=MAX_TOKENS), not caching`).
- `MAX_TOKENS` truncation is **not** a regression from the 2026-07-31
  context_builder fix — it first appears 2026-07-30, before that fix was
  deployed, when the context fields were still all null.

**Real gap found in code (verified, but NOT proven to be the cause):**
`provider.py:103` classifies transient upstream failures
(`503`/`UNAVAILABLE`/`429`/`overloaded`/`high demand`/`RESOURCE_EXHAUSTED`)
and returns `transient: true`, so the card shows a calm
"⏳ AI temporarily busy — retrying automatically". That only applies when the
HTTP call *succeeds*. When the fetch itself fails:

```
api.ts:30            msg = `HTTP ${r.status}`          -> "HTTP 500"
AIAnalysisCard:25    catch -> {ok:false, error:msg}    -> no `transient` flag
render (:47)         transient ? "⏳ " : "AI unavailable — "
```

…the backend's transient classification is bypassed entirely, so even a
genuinely temporary 503 would render as the alarming "AI unavailable —"
rather than "retrying". Same family as the rate-limit hyphen classifier bug
fixed earlier this phase.

**Why this is NOT being fixed yet:** the gap is real in code, but it has not
been shown to be what produced this screenshot. The card polls every 60s
(`AIAnalysisCard.tsx:26`), so a single transient failure would clear on the
next poll — the screenshot may simply have caught that window. Root cause is
unconfirmed between: a real backend 500 that went unlogged, a browser-side
fetch failure, a proxy, or stale render state. **One screenshot is not enough
evidence to change a classifier** — the same discipline that correctly closed
the AI Timeline case as "Verified, No Code Change Required".

**Status:** Observation · Priority Low · Reproduced: **No** · Production
impact: unknown · Trading impact: none (display only; AI Analysis feeds no
gate or decision).

**Trigger for action — on a second occurrence, capture in this order:**
screenshot → backend log at that exact timestamp → browser Network tab
(status + response body) → console. Only then reproduce and fix.

## Rule for this phase

No new features, no new engines, no new panels — bug fixes and the checks
above only. V8.0 planning (candidate list in `docs/RELEASE_NOTES_v7.0.0.md`)
does not begin until this checklist is complete and the owner says so.
