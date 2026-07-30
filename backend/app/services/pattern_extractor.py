"""V8 Phase 3A — Pattern Extractor (v8-dev, 2026-07-30).

Owner's own sub-phase split for V8 Phase 3 (Pattern Mining):
    3A Pattern Extractor  — tag each episode with the conditions present.
    3B Pattern Statistics — occurrences / win% / avg MFE-MAE / avg timing.
    3C Pattern Ranking    — confidence / reliability / sample size / regime.

THIS FILE IS 3A ONLY. It reads one already-written black-box record (from
data/opportunity_log/*.jsonl, produced by opportunity_metrics.py) and returns
the condition tags present on it — nothing else. No occurrence counts, no
win/loss rates, no ranking, no confidence score, no recommendation text.
"Occurrences" is explicitly the FIRST item on the owner's own Phase 3B list —
even a raw count belongs there, not here. This module never says a pattern is
good; it doesn't say anything about a pattern's outcome at all, only what was
present. Purely read-only over historical logs; never touches live state,
never mutates anything, never runs during market hours as part of any gate.

Every tag below reuses a threshold or classification the codebase ALREADY
has, where one exists (VIX_LOW/VIX_HIGH from risk_approval.py; BOS/CHOCH
straight from structure.py's own labeling). Where no existing cutoff exists
(CPR width, OI/Trend score bands), a NEW threshold is declared below —
explicitly marked as unvalidated. Same declared-not-fitted convention as
opportunity_metrics.py's own STIR_PCT/RUNNER_PCT. Phase 3B's occurrence/
win-rate stats are what will tell us whether these cutoffs actually separate
outcomes; until then they are working guesses, not evidence.
"""
from __future__ import annotations

from typing import Any

from .risk_approval import VIX_LOW, VIX_HIGH  # reused, not redeclared

# ── declared thresholds (NEW, unvalidated — Phase 3B checks these) ─────────
CPR_NARROW_PCT = 0.15      # tc-bc as % of pivot; below this = "narrow" CPR
GAMMA_WALL_NEAR_PCT = 0.15  # mirrors gamma_shield.py's own inline 0.15% (0.0015)
                            # formula — that file has no named constant to
                            # import, so this must be kept in sync by hand if
                            # gamma_shield.py's threshold ever changes.
OI_BUILD_MIN = 60          # layers["OI"] score ≥ this = "OI Build"
TREND_STRONG_MIN = 60      # layers["Trend"] score ≥ this = "Trend Strong"


def _cpr_tag(cpr: float | None, tc: float | None, bc: float | None) -> str | None:
    if not (cpr and tc is not None and bc is not None):
        return None
    width_pct = abs(tc - bc) / cpr * 100 if cpr else None
    if width_pct is None:
        return None
    return "CPR_NARROW" if width_pct < CPR_NARROW_PCT else "CPR_WIDE"


def _gamma_wall_tag(wall: float | None, underlying: float | None) -> str | None:
    if not (wall and underlying):
        return None
    distance_pct = abs(underlying - wall) / underlying * 100
    return "GAMMA_WALL_NEAR" if distance_pct < GAMMA_WALL_NEAR_PCT else "GAMMA_WALL_FAR"


def _vwap_tag(vwap: float | None, underlying: float | None) -> str | None:
    if not (vwap and underlying):
        return None
    return "VWAP_ABOVE" if underlying > vwap else "VWAP_BELOW"


def _oi_tag(oi_score: float | None) -> str | None:
    if oi_score is None:
        return None
    return "OI_BUILD" if oi_score >= OI_BUILD_MIN else "OI_WEAK"


def _delta_tag(delta: float | None) -> str | None:
    if delta is None:
        return None
    return "DELTA_POSITIVE" if delta > 0 else ("DELTA_NEGATIVE" if delta < 0 else None)


def _vix_tag(vix: float | None) -> str | None:
    if vix is None:
        return None
    if vix < VIX_LOW:
        return "VIX_LOW"
    if vix > VIX_HIGH:
        return "VIX_HIGH"
    return "VIX_NORMAL"


def _trend_tag(trend_score: float | None) -> str | None:
    if trend_score is None:
        return None
    return "TREND_STRONG" if trend_score >= TREND_STRONG_MIN else "TREND_WEAK"


def extract_tags(bb: dict[str, Any]) -> list[str]:
    """Return the sorted, deduplicated condition tags present on ONE black-box
    record. Missing/unavailable inputs simply produce no tag for that
    condition — never a fabricated guess (same doctrine as the rest of the
    black box: an unmeasurable field stays absent, not defaulted)."""
    engine = bb.get("engine") or {}
    layers = engine.get("layers") or {}
    greeks = engine.get("greeks") or {}

    tags = [
        _cpr_tag(engine.get("cpr"), engine.get("cpr_tc"), engine.get("cpr_bc")),
        _gamma_wall_tag(engine.get("gamma_wall"), engine.get("underlying")),
        _vwap_tag(engine.get("vwap"), engine.get("underlying")),
        engine.get("bos_choch"),                    # "BOS" | "CHOCH" | None, direct passthrough
        _oi_tag(layers.get("OI")),
        _delta_tag(greeks.get("delta")),
        _vix_tag(engine.get("vix")),
        _trend_tag(layers.get("Trend")),
    ]
    # calendar/tape axis tags — already-logged categorical fields, passed
    # through as-is rather than re-derived.
    if bb.get("regime"):
        tags.append(f"REGIME_{bb['regime']}")
    if bb.get("session_type"):
        tags.append(f"SESSION_{bb['session_type']}")

    return sorted({t for t in tags if t})


def pattern_signature(bb: dict[str, Any]) -> str:
    """A canonical grouping key for one episode's tag combination — e.g.
    'CPR_NARROW|GAMMA_WALL_NEAR|TREND_STRONG|VWAP_ABOVE'. Just an identifier
    for Phase 3B to group by; computing a signature is not the same as
    computing that signature's statistics, which stays out of this file."""
    return "|".join(extract_tags(bb))
