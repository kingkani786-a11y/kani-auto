"""V8 feature flags — owner authorization, 2026-07-27 (V8 Development branch).

Every V8 capability ships DISABLED by default. Nothing here is wired into
any live decision, gate, or size — enabling a flag only makes a NEW,
additive read-only surface available (a report, a panel, a comparison
metric); it never replaces or silently changes what V7's existing engines
decide. Promoting anything from "flag on in dev" to "feeds a real gate in
production" is a separate, later Trading-Doctrine proposal, not something
flipping a flag here ever does on its own.

This module lives only on the v8-dev branch/worktree — it is not present
on main, so there's nothing to accidentally merge and no gate to keep an
eye on if a V7 hotfix is ever cherry-picked away from this branch.
"""
from __future__ import annotations

import os


def _flag(name: str) -> bool:
    return os.environ.get(f"CAT_V8_{name}", "").strip().lower() in ("1", "true", "yes")


class V8Flags:
    # Item 1 — Walk-Forward Validation framework (in development)
    walk_forward_validation: bool = _flag("WALK_FORWARD_VALIDATION")

    # Item 2 — ML Calibration Model (not started)
    ml_calibration_model: bool = _flag("ML_CALIBRATION_MODEL")

    # Item 3 — GEX (dealer gamma exposure) approximation (not started)
    gex_approximation: bool = _flag("GEX_APPROXIMATION")

    # Research Dashboard — the one exception to the 2026-07-30 v8-dev code
    # freeze (docs/V8_STATUS.md): read-only aggregation of already-built
    # Phase 1-3C/Evidence/Walk-Forward/Promotion-Gate outputs. No new
    # evidence math, no gate, no broker connection needed.
    research_dashboard: bool = _flag("RESEARCH_DASHBOARD")


v8_flags = V8Flags()
