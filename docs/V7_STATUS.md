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
| 2026-07-27 | Hero's Multi-Timeframe row never showed "1H" (5m/15m/4H/Daily only), confirmed on the owner's first live market-open session | `mtf_confluence.py` resampled 1H bars from `state.candles`, hard-capped at 600 one-minute bars (10h) in `market_service.py`. A 1H timeframe needs 30 complete bars (1800 min / 30h) to satisfy `_MIN_BARS` — 3x more than the cap can ever hold. 1H was structurally unable to ever reach "ready", on any day. | New `mtf_1h_cache.py` (real 60-bar 1H fetch, 10 min TTL) mirroring the existing 4H cache pattern, wired into the same scanner loop. `mtf_confluence.py` now takes 1H from this direct fetch instead of resampling. Verified: synthetic test confirms 1H reaches `ready: True` independent of the 1m buffer's cap; old resample path reproduced showing only 10 bars (the bug). **Code fixed and verified; deploy (backend restart) held for market close per standing rule.** |
| 2026-07-27 | During the owner's first live session, a broker rate-limit cooldown (a pre-existing, working, correctly-triggered protection mechanism) displayed as the vague "🟠 Broker issue — retrying automatically" instead of the intended "⏳ Rate limited by broker — pausing briefly, will resume". Same root cause independently affected the Settings page's Save & Connect error message if attempted during a cooldown. | Two classifiers (`market_service.py`'s `_friendly_error()` and `frontend/lib/status.ts`'s `friendlyMessage()`) checked for the phrase `"rate limit"` (space) but the actual cooldown exception says `"Broker rate-limit cooldown..."` (hyphen) — a pure string-match miss, present since before this session. `ProChart.tsx`'s own classifier already had a `"cooldown"` fallback and was unaffected. | Broadened both classifiers to also match `"rate-limit"` and `"cooldown"`. Verified: both known cooldown message variants (`dhan.py`'s hyphenated cooldown message and its space-separated 429 message) now correctly classify as `RATE_LIMIT`. Frontend `tsc` clean. **Code fixed and verified; deploy held for the same upcoming restart as the 1H fix above (frontend-only change, no restart urgency beyond that).** |

## Rule for this phase

No new features, no new engines, no new panels — bug fixes and the checks
above only. V8.0 planning (candidate list in `docs/RELEASE_NOTES_v7.0.0.md`)
does not begin until this checklist is complete and the owner says so.
