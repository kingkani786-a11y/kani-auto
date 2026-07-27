# Cloud AI Trader V8 — Evidence-Driven Autonomous Evolution System (EDAES)

Locked by owner, 2026-07-27. Governs all work on the `v8-dev` branch. The
name is deliberate: AI researches, proves, and recommends autonomously —
production decisions stay with the owner, always.

## The two modes

### Mode A — Autonomous Research Mode (100% autonomous)

No approval needed to operate here. Repository scan, architecture review,
bug detection, pattern discovery, new trading ideas, strategy evolution,
backtesting, walk-forward testing, shadow trading, statistical analysis,
performance optimization, documentation updates — all free to run without
asking first, as long as they stay inside `v8-dev` and never touch `main`
or the live processes.

### Mode B — Production Governance Mode (human-approved, always)

Nothing in this mode ever executes without the owner's explicit,
per-action authorization. No exceptions, regardless of how much evidence
was gathered or how many validation gates passed.

## The 10 states (as amended)

States 1-8 (Observe, Diagnose, Learn, Generate Improvements, Simulation,
Evidence Validation, Promotion Rules, Shadow Mode) run exactly as
originally specified, entirely inside Mode A.

**State 9 — Autonomous Recommendation** (replaces "Autonomous Decision"):

> If every validation gate passes, generate: Evidence Report, Performance
> Report, Risk Report, Comparison Report, Rollback Plan, Deployment Plan,
> Final Recommendation. Status: **READY FOR APPROVAL**. Wait for owner
> authorization. Never deploy automatically. Never merge automatically.
> Never modify production automatically.

**State 10 — Emergency Recovery Plan** (replaces "Automatic Rollback"):

> If production degrades: immediately detect, collect evidence, generate
> the rollback command, prepare the rollback package, notify the owner,
> wait for approval. Execute only after authorization.

## Why this resolves the earlier conflict

The original "Autonomous Decision" state let passing evidence gates
*replace* owner approval. The owner's own prior "V8 Development
Authorization" required evidence gates to *precede* approval, never
replace it. States 9 and 10 as amended make that explicit and permanent:
passing every metric is grounds to *recommend*, never grounds to *execute*.
This is the same shape as the standing production rule that has governed
every push and restart this entire project: approval is per-action, fresh
every time, never a standing yes — regardless of how much evidence backs
the request.

## What never changes, regardless of mode

- Entry Logic, Exit Logic, Risk Logic, Position Sizing, Confidence Formula,
  Support/Resistance Logic, Institutional Logic, Decision Engine — none of
  these are auto-modified in production, ever, under any circumstance,
  even after Evidence + Simulation + Backtest + Shadow Mode + Validation +
  Promotion Rules all succeed. Passing all of that produces a
  recommendation, not an authorization.
- No standing daemon — this system does not run as an unattended
  background process making decisions between conversations. Continuous
  monitoring in the STATE 1 sense means "run this analysis whenever asked,
  thoroughly," not "operate autonomously 24/7 without the owner present."
  Genuine always-on monitoring/alerting is a separate, explicit
  infrastructure decision if ever wanted — not implied by this charter.
- Capital protection > any performance/innovation gain, exactly as V7's
  Trading Doctrine already establishes.
