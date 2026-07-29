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
| 2026-07-27 | During the owner's first live session, a broker rate-limit cooldown (a pre-existing, working, correctly-triggered protection mechanism) displayed as the vague "🟠 Broker issue — retrying automatically" instead of the intended "⏳ Rate limited by broker — pausing briefly, will resume". Same root cause independently affected the Settings page's Save & Connect error message if attempted during a cooldown. | Two classifiers (`market_service.py`'s `_friendly_error()` and `frontend/lib/status.ts`'s `friendlyMessage()`) checked for the phrase `"rate limit"` (space) but the actual cooldown exception says `"Broker rate-limit cooldown..."` (hyphen) — a pure string-match miss, present since before this session. `ProChart.tsx`'s own classifier already had a `"cooldown"` fallback and was unaffected. | Broadened both classifiers to also match `"rate-limit"` and `"cooldown"`. Verified: both known cooldown message variants (`dhan.py`'s hyphenated cooldown message and its space-separated 429 message) now correctly classify as `RATE_LIMIT`. Frontend `tsc` clean. **Code fixed and verified; deploy held for the same upcoming restart as the 1H fix above (frontend-only change, no restart urgency beyond that).** |

## Rule for this phase

No new features, no new engines, no new panels — bug fixes and the checks
above only. V8.0 planning (candidate list in `docs/RELEASE_NOTES_v7.0.0.md`)
does not begin until this checklist is complete and the owner says so.
