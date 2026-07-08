"""Layer 9 — Probability Engine.

Converts the confluence edge into probability of success/failure and an
IV- (or ATR-) based expected move and range. POS is a calibrated logistic
of the score edge, damped by regime quality — it is an estimate of edge,
not a guarantee.
"""
from __future__ import annotations

import datetime
import math
from typing import Any


def analyze(
    win_score: float,
    lose_score: float,
    regime_score: float,
    spot: float,
    iv: float,                 # decimal ATM IV, 0 if unknown
    expiry: str | None,
    atr_v: float,
) -> dict[str, Any]:
    edge = win_score - lose_score
    # logistic centered at edge=0; regime damps toward 50 in bad tape
    raw = 1.0 / (1.0 + math.exp(-edge / 12.0))
    damp = 0.5 + 0.5 * min(regime_score, 100) / 100.0
    pos = 50 + (raw * 100 - 50) * damp
    pos = max(5.0, min(92.0, pos))

    # Expected move — INTRADAY horizon (max 1 trading day of sigma), because
    # every consumer (point capture, ladder, entry details, projection) reads
    # this as "today's realistic move". Using time-to-expiry here inflated the
    # number ~5x on monthly-expiry contracts (NG: 31 pts shown vs ~6.5 real).
    # The full to-expiry sigma is still returned separately for reference.
    em_expiry = None
    if iv > 0 and expiry and spot > 0:
        try:
            days = max((datetime.date.fromisoformat(expiry) - datetime.date.today()).days, 0) + 0.5
            em_expiry = spot * iv * math.sqrt(days / 365.0)
            em = spot * iv * math.sqrt(min(days, 1.0) / 365.0)
        except ValueError:
            em = 2.0 * atr_v
    else:
        em = 2.0 * atr_v

    return {
        "prob_success": round(pos, 1),
        "prob_failure": round(100 - pos, 1),
        "expected_move": round(em, 2),
        "expected_move_expiry": round(em_expiry, 2) if em_expiry else None,
        "expected_range": [round(spot - em, 2), round(spot + em, 2)],
    }
