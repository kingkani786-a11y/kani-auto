"""Signal Quality Engine — A/B/C grading. Below 60% = NO TRADE (enforced
upstream by the confluence threshold; grade D is a safety net)."""
from __future__ import annotations

from typing import Any


def grade(signal: dict[str, Any], historical_accuracy: float | None) -> dict[str, Any]:
    if signal.get("signal") == "NO TRADE":
        return {"grade": "NO TRADE", "grade_score": 0, "grade_notes": []}

    conf = float(signal.get("confidence") or 0)
    confirms = int(signal.get("confirmations_count") or 0)
    score = conf
    notes: list[str] = []

    # confluence breadth bonus/penalty
    score += (confirms - 5) * 2
    if historical_accuracy is not None:
        score += (historical_accuracy - 55) * 0.2
        notes.append(f"Historical accuracy of recent signals: {historical_accuracy:.0f}%")

    score = max(0.0, min(100.0, score))
    if score >= 85:
        g = "A"
        notes.insert(0, "A-grade: exceptional confluence — full planned size appropriate")
    elif score >= 70:
        g = "B"
        notes.insert(0, "B-grade: solid setup — standard size")
    elif score >= 60:
        g = "C"
        notes.insert(0, "C-grade: acceptable but marginal — reduced size or skip")
    else:
        g = "NO TRADE"
        notes.insert(0, "Quality below 60 — do not trade this")

    return {"grade": g, "grade_score": round(score, 1), "grade_notes": notes}
