"""V8 Phase 3A — Pattern Extractor (v8-dev, 2026-07-30; refined 2026-07-30).

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

Owner refinement (2026-07-30) added three things on top of the original tag
extraction:
  - pattern_id()/pattern_signature() — a stable identity for a tag
    combination, so Phase 3B can GROUP BY it and Phase 4 can reference it.
  - tag_source()/describe_tags() — which engine/module each tag's underlying
    value actually came from, for debugging.
  - THRESHOLD_REGISTRY — every declared cutoff in one place, with its
    validation status, instead of scattered module constants. Phase 4's
    proposal engine will eventually read/write against this same registry
    ("current vs observed-best vs proposed"); for now it's read-only.
"""
from __future__ import annotations

import hashlib
from typing import Any

from .risk_approval import VIX_LOW, VIX_HIGH  # reused, not redeclared

# ── Threshold Registry — single source of truth for every declared cutoff
# used below. "status" tells you whether a number is borrowed from code that
# already exists elsewhere (reused — trustworthy) or invented here for lack
# of any existing definition (unvalidated — a working guess, not evidence).
# Phase 3B's occurrence/win-rate stats are what will actually test the
# unvalidated ones; nothing here claims otherwise. Same declared-not-fitted
# convention as opportunity_metrics.py's own STIR_PCT/RUNNER_PCT.
THRESHOLD_REGISTRY: dict[str, dict[str, Any]] = {
    "cpr_narrow_pct": {
        "value": 0.15, "unit": "% of pivot (tc-bc width)",
        "status": "unvalidated", "reused_from": None,
        "note": "below this = CPR_NARROW, else CPR_WIDE",
    },
    "gamma_wall_near_pct": {
        "value": 0.15, "unit": "% distance from underlying spot",
        "status": "mirrors an existing formula, not independently chosen",
        "reused_from": "engines/gamma_shield.py (inline 0.0015 fraction — "
                        "that file exports no named constant, so this value "
                        "must be kept in sync by hand if it ever changes there)",
        "note": "below this = GAMMA_WALL_NEAR, else GAMMA_WALL_FAR",
    },
    "oi_build_min": {
        "value": 60, "unit": "OI layer score (0-100)",
        "status": "unvalidated", "reused_from": None,
        "note": "at/above this = OI_BUILD, else OI_WEAK",
    },
    "trend_strong_min": {
        "value": 60, "unit": "Trend layer score (0-100)",
        "status": "unvalidated", "reused_from": None,
        "note": "at/above this = TREND_STRONG, else TREND_WEAK",
    },
    "vix_low": {
        "value": VIX_LOW, "unit": "India VIX points",
        "status": "reused", "reused_from": "services/risk_approval.py (VIX_LOW)",
        "note": "below this = VIX_LOW tag",
    },
    "vix_high": {
        "value": VIX_HIGH, "unit": "India VIX points",
        "status": "reused", "reused_from": "services/risk_approval.py (VIX_HIGH)",
        "note": "above this = VIX_HIGH tag; between vix_low and vix_high = VIX_NORMAL",
    },
}


def _t(name: str) -> Any:
    return THRESHOLD_REGISTRY[name]["value"]


# ── Tag source metadata — which engine/module a tag FAMILY's underlying
# value actually comes from, for debugging ("why does this episode carry
# VWAP_ABOVE?" → look here, then at that file).
TAG_SOURCES: dict[str, str] = {
    "CPR": "engines/support_resistance.py daily_cpr() — pivot/tc/bc",
    "GAMMA_WALL": "state.intelligence.layers.expiry.gamma_wall "
                  "(engines/expiry.py, read the way engines/gamma_shield.py does)",
    "VWAP": "state.signal.tech.vwap (technical indicators, market_service.py)",
    "BOS_CHOCH": "engines/structure.py analyze() — bos_choch",
    "OI": "state.intelligence layers.intelligence.decision_matrix 'OI' row",
    "DELTA": "state.intelligence.strike (engines/strike_selector.py + "
             "engines/greeks.py) — only present when the episode's own "
             "strike matches the currently strike-engine-selected one",
    "VIX": "state.intelligence.layers.vix_correlation (engines/global_context.py)",
    "TREND": "state.intelligence layers.intelligence.decision_matrix 'Trend' row",
    "REGIME": "opportunity_metrics._behavioural_regime() — tape axis",
    "SESSION": "opportunity_metrics._session_type() — calendar axis",
}

_TAG_FAMILY_FIXED = {"BOS": "BOS_CHOCH", "CHOCH": "BOS_CHOCH"}
_TAG_FAMILY_PREFIXES = [
    ("CPR_", "CPR"), ("GAMMA_WALL_", "GAMMA_WALL"), ("VWAP_", "VWAP"),
    ("OI_", "OI"), ("DELTA_", "DELTA"), ("VIX_", "VIX"), ("TREND_", "TREND"),
    ("REGIME_", "REGIME"), ("SESSION_", "SESSION"),
]


def tag_family(tag: str) -> str | None:
    if tag in _TAG_FAMILY_FIXED:
        return _TAG_FAMILY_FIXED[tag]
    for prefix, fam in _TAG_FAMILY_PREFIXES:
        if tag.startswith(prefix):
            return fam
    return None


def tag_source(tag: str) -> str | None:
    fam = tag_family(tag)
    return TAG_SOURCES.get(fam) if fam else None


def describe_tags(tags: list[str]) -> list[dict[str, str | None]]:
    """Annotate a tag list with each tag's source module, for debugging."""
    return [{"tag": t, "source": tag_source(t)} for t in tags]


def _cpr_tag(cpr: float | None, tc: float | None, bc: float | None) -> str | None:
    if not (cpr and tc is not None and bc is not None):
        return None
    width_pct = abs(tc - bc) / cpr * 100 if cpr else None
    if width_pct is None:
        return None
    return "CPR_NARROW" if width_pct < _t("cpr_narrow_pct") else "CPR_WIDE"


def _gamma_wall_tag(wall: float | None, underlying: float | None) -> str | None:
    if not (wall and underlying):
        return None
    distance_pct = abs(underlying - wall) / underlying * 100
    return "GAMMA_WALL_NEAR" if distance_pct < _t("gamma_wall_near_pct") else "GAMMA_WALL_FAR"


def _vwap_tag(vwap: float | None, underlying: float | None) -> str | None:
    if not (vwap and underlying):
        return None
    return "VWAP_ABOVE" if underlying > vwap else "VWAP_BELOW"


def _oi_tag(oi_score: float | None) -> str | None:
    if oi_score is None:
        return None
    return "OI_BUILD" if oi_score >= _t("oi_build_min") else "OI_WEAK"


def _delta_tag(delta: float | None) -> str | None:
    if delta is None:
        return None
    return "DELTA_POSITIVE" if delta > 0 else ("DELTA_NEGATIVE" if delta < 0 else None)


def _vix_tag(vix: float | None) -> str | None:
    if vix is None:
        return None
    if vix < _t("vix_low"):
        return "VIX_LOW"
    if vix > _t("vix_high"):
        return "VIX_HIGH"
    return "VIX_NORMAL"


def _trend_tag(trend_score: float | None) -> str | None:
    if trend_score is None:
        return None
    return "TREND_STRONG" if trend_score >= _t("trend_strong_min") else "TREND_WEAK"


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


def pattern_id(bb: dict[str, Any]) -> str:
    """A short, stable, content-derived ID for a tag combination — e.g.
    'PATTERN_A3F9C21B'. Deterministic: the SAME tag combination always
    produces the SAME id, with no persistent counter/registry file needed
    (unlike a sequential 'PATTERN_000431' style ID, which would require
    assigning and storing IDs somewhere as new combinations are first seen).

    This is a content hash (8 hex chars ≈ 4.3 billion buckets), not a
    sequence number — collision is practically impossible at any pattern
    count this project will ever reach, but it is not mathematically zero.
    `pattern_signature()` remains the true, exact identity; if two IDs were
    ever suspected to collide, compare signatures directly rather than IDs.
    """
    sig = pattern_signature(bb)
    digest = hashlib.sha256(sig.encode()).hexdigest()[:8]
    return f"PATTERN_{digest.upper()}"


def group_records(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group already-closed black-box records by pattern_id. Shared by Phase
    3B (pattern_stats.py) and the Evidence Validator — pattern identity is
    this module's concern, not something each downstream consumer should
    re-derive its own copy of."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        groups.setdefault(pattern_id(r), []).append(r)
    return groups


# ── Core signature (owner, 2026-07-30) ──────────────────────────────────────
# pattern_id/pattern_signature bake REGIME_*/SESSION_* into a pattern's own
# identity — a real, useful design for "how does this exact condition set
# perform in EXPIRY sessions specifically", but it means a fixed pattern_id
# can NEVER mix regimes/sessions, so "does this pattern generalize across
# Bull/Bear/Sideways" is unanswerable at that level BY CONSTRUCTION, not
# because the evidence happens to be concentrated (flagged in
# evidence_validator.py when this was first noticed).
#
# core_signature/core_pattern_id below are the SAME tags with REGIME_*/
# SESSION_* excluded — a second, complementary grouping. A "core pattern"
# (e.g. CPR_NARROW|OI_BUILD|TREND_STRONG|VWAP_ABOVE) can appear under
# multiple regimes/sessions, which is exactly what lets the Evidence
# Validator check whether it holds up across them. This does not replace
# pattern_id/pattern_signature — both groupings are kept, for different
# questions.
_CORE_EXCLUDED_PREFIXES = ("REGIME_", "SESSION_")


def core_tags(bb: dict[str, Any]) -> list[str]:
    return [t for t in extract_tags(bb) if not t.startswith(_CORE_EXCLUDED_PREFIXES)]


def core_signature(bb: dict[str, Any]) -> str:
    return "|".join(core_tags(bb))


def core_pattern_id(bb: dict[str, Any]) -> str:
    """Same content-hash approach as pattern_id(), prefixed CORE_ so the two
    id spaces are never visually confused with each other."""
    sig = core_signature(bb)
    digest = hashlib.sha256(sig.encode()).hexdigest()[:8]
    return f"CORE_{digest.upper()}"


def group_by_core(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        groups.setdefault(core_pattern_id(r), []).append(r)
    return groups
