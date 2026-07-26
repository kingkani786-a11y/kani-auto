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

## Rule for this phase

No new features, no new engines, no new panels — bug fixes and the checks
above only. V8.0 planning (candidate list in `docs/RELEASE_NOTES_v7.0.0.md`)
does not begin until this checklist is complete and the owner says so.
