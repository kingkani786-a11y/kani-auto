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

## Rule for this phase

No new features, no new engines, no new panels — bug fixes and the checks
above only. V8.0 planning (candidate list in `docs/RELEASE_NOTES_v7.0.0.md`)
does not begin until this checklist is complete and the owner says so.
