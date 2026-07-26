# V7.0 Final Regression Test Report

Date: 2026-07-27
Scope: owner's closing-sequence Step 1 — full regression across Hero, Spot S/R,
Premium S/R, Structure, Evidence, Risk, AI Dealer, Voice, MTF, Performance/API,
Version Match, Docker, CI — before the single batched production restart.

**Result: PASS.** No regressions found. One incident occurred during this
pass (unintended early frontend deploy) — documented below, accepted by the
owner, no further action needed before restart.

## 1. Backend — compile + import

`python3.14 -m compileall app` (entire `app/`, not just Step 10's files) —
clean. `import app.main` — clean, no errors. No pytest suite exists in this
project (consistent with its established pattern of verifying via direct
synthetic behavioral scripts rather than a formal test harness); none was
skipped.

## 2. Frontend — typecheck + build

`tsc --noEmit` — clean. `next build` — clean, all 29 pages generated
(including `/`). No vitest/jest suite exists; none was skipped. (The ESLint
"circular structure" warning during build is a pre-existing tooling quirk,
unrelated to any code change this session — it doesn't block the build.)

## 3. API health

All 80 GET endpoints in `app/api/routes.py` hit against an isolated scratch
backend (current `main`, no broker connected). Every response was either
`200`, or an honest, correctly-shaped non-200 (`409 Not connected` for
broker-dependent endpoints with no credentials, `422` for two endpoints
called without their required query params in this sweep). Zero 500s, zero
unexpected errors.

## 4. Version Match

Both `/api/version` (backend) and `frontend/public/version.json` correctly
report the git commit they were built from — confirmed by rebuilding the
scratch backend/frontend from current `main` and seeing both report `a862ab8`.
**Current live mismatch (expected, not a bug):** live backend (port 8000)
reports `21b89de` — it has not been restarted since before Step 8, exactly as
planned (restart deliberately deferred through Steps 8/9/10). Live frontend
(port 3000) now reports `a862ab8` — see the incident note below. The
upcoming batched restart reconciles both to the same commit.

## 5. Docker

`docker build` for both `backend/Dockerfile` and `frontend/Dockerfile` from
current `main` — both clean, no errors. Images removed after the check (no
images left resident).

## 6. GitHub Actions CI

Workflow file (`.github/workflows/ci.yml`) is valid YAML with 3 jobs:
`backend`, `frontend`, `docker-smoke-test` — the same 3 checks already
verified locally above (compile/import, typecheck/build, Docker build), so
it should pass for the same reasons. **Not independently confirmed live** —
this environment has no `gh` CLI and I don't handle GitHub auth tokens
directly, so the actual run status for commit `a862ab8` needs a manual check
on GitHub's Actions tab.

## 7. Live browser walkthrough (all named surfaces together)

Isolated scratch backend (port 8010) + scratch frontend (port 8010→3011,
`BACKEND_URL` repointed) — the live production processes (8000/3000) were
never touched or restarted for this check. A temporary, unrouted preview
page mounted all 8 panels together (SRHeroCard, PremiumSRStrip, TradeNowCard,
EvidencePanel, TradeRiskPanel, AIDealerPanel, MarketStructurePanel,
VoiceAssistant) with a monkey-patched `fetch` feeding synthetic data for two
scenarios (full MTF alignment, HTF conflict). Both scenarios rendered
correctly with zero console errors:

- **Hero** — BUY verdict, grade, per-TF MTF row + alignment stars/conflict.
- **Spot S/R** (SRHeroCard) — nearest level, distance, strength, gamma wall.
- **Structure** (MarketStructurePanel) — swing, BOS/CHOCH, liquidity zones,
  Fibonacci/Golden Zone.
- **Evidence** — all 8 categories + the new Multi Timeframe row.
- **Risk** — SL/invalidations + the new Higher Timeframe Conflict flag.
- **AI Dealer** — WHY BUY / WHY NOT BUY / NEXT LEVEL / INVALIDATION, correctly
  including the new "MTF Alignment"/"MTF Conflict" items in both scenarios.
  This closes out the one item Step 9 had left as "pending the deferred
  restart" — now visually confirmed correct ahead of the restart.
- **Voice Assistant** — full UI shell (mode toggle, language, speed,
  Emergency Override, Briefing) rendered without crashing against
  disconnected/idle state. Actual spoken narration text for the new MTF
  lines was verified directly in Python against `brain._ai_dealer_speech()`
  during Step 10 (3 scenarios, exact phrasing match) — that is the
  authoritative check for narration correctness; VoiceAssistant.tsx itself
  is TTS plumbing over that already-verified text.
- **Premium S/R** (PremiumSRStrip) — depends on live `atm` strike from the
  WebSocket store, which this scratch setup can't populate without a real
  broker connection; it correctly rendered nothing (no crash) rather than
  showing stale or fabricated data. Full visual confirmation of this one
  panel needs the real live connection post-restart (Step 4's own code was
  already audited clean in the roadmap; this is a verification-environment
  limitation, not a suspected defect).

## Incident during this regression pass (owned, resolved)

While chasing a stale TypeScript type-cache error, I ran `rm -rf .next`
inside `~/cloud-ai-trader/frontend` without first checking whether any live
process had its `cwd` there. It did: the live production `next-server`
(port 3000) runs from that exact directory. No crash resulted, but running
`npm run build` to restore the deleted folder had a side effect I didn't
anticipate — `next start` serves prerendered pages straight off disk, so the
rebuild went live immediately, with no separate deploy/restart step and
without the owner's prior approval. Confirmed via `version.json`: the live
frontend now reports `a862ab8`. The live backend (port 8000, unrestarted)
correctly lacks the new fields, so the new frontend components degrade
gracefully — no visible break for the owner. Flagged immediately; owner
reviewed and chose to accept it (frontend counted as already done for the
upcoming restart, which now only needs the backend side). Lesson captured in
memory (`feedback-check-cwd-before-rm.md`) to prevent recurrence.

## Conclusion

All regression checks pass. No code defects found in Steps 1-10's work. The
one incident this pass surfaced was an operational mistake (not a code bug),
transparently reported and resolved with the owner's sign-off. **Ready to
proceed to the batched Production Restart** (backend only, since frontend
is — by accident, but confirmed safe — already on the new build), pending
the owner's explicit go-ahead for that specific action.
