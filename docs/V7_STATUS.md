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

## Rule for this phase

No new features, no new engines, no new panels — bug fixes and the checks
above only. V8.0 planning (candidate list in `docs/RELEASE_NOTES_v7.0.0.md`)
does not begin until this checklist is complete and the owner says so.
