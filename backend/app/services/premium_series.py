"""Premium tick persistence — prerequisite for Premium S/R (owner, 2026-07-23).

premium_radar._tracks keeps only a 200-tick rolling window (~_LOOKBACK
seconds) — not enough history for an honest "N touches, X% bounce" claim on
the premium series itself (support_resistance.premium_levels_available() has
said so since Phase 2 kickoff). This persists every scanned tick to a durable
per-day log so a real intraday premium history can be read back and fed
through the SAME touch/bounce/break math already proven for spot levels
(support_resistance.compute_levels) — no second algorithm invented.

Same RESEARCH_MODE / CAT_DATA_DIR convention as opportunity_metrics.py:
verification runs must never pollute the production log (2026-07-21 lesson —
a verification run once wrote the production path because that path was the
silent default).

Scoped to TODAY only, deliberately: a strike's premium behaves very
differently across days (DTE decay, IV regime), so cross-day premium-level
comparison for the "same" nominal strike would compare unrelated populations.
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
from typing import Any

from ..core.clock import IST

RESEARCH_MODE = os.getenv("CAT_RESEARCH_MODE", "").strip() in ("1", "true", "yes")
_LOG_DIR = (pathlib.Path(os.environ["CAT_DATA_DIR"]) if os.getenv("CAT_DATA_DIR")
            else pathlib.Path(__file__).resolve().parents[3] / "data" / "premium_log")


def _today() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d")


def record(symbol: str, strike: int, typ: str, premium: float, now: float) -> None:
    """One line per (symbol, strike, type) per scan tick. Never crashes the
    radar scan — same never-affect-the-radar contract as opportunity_metrics."""
    if RESEARCH_MODE or premium <= 0:
        return
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"ts": round(now, 1), "symbol": symbol, "strike": int(strike),
                            "type": typ, "premium": round(premium, 2)}, ensure_ascii=False)
        with (_LOG_DIR / f"{_today()}.jsonl").open("a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def read_today(symbol: str, strike: int, typ: str) -> list[dict[str, Any]]:
    """Every persisted tick today for one strike, oldest first."""
    p = _LOG_DIR / f"{_today()}.jsonl"
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        for ln in p.read_text().splitlines():
            if not ln.strip():
                continue
            row = json.loads(ln)
            if (row.get("symbol") == symbol and row.get("strike") == int(strike)
                    and row.get("type") == typ):
                out.append(row)
    except Exception:
        pass
    return out


def to_bars(ticks: list[dict[str, Any]], bucket_s: int = 60) -> list[dict[str, Any]]:
    """Bucket raw (ts, premium) ticks into synthetic OHLC bars — the shape
    support_resistance.compute_levels() already expects. bucket_s=60 (1-min):
    fine enough to resolve intraday premium swings, coarse enough that 11
    bars (compute_levels' minimum) means ~11 minutes of real trading, not a
    handful of noisy sub-second ticks masquerading as a trend."""
    if not ticks:
        return []
    buckets: dict[int, list[float]] = {}
    for t in ticks:
        b = int(t["ts"]) // bucket_s
        buckets.setdefault(b, []).append(t["premium"])
    bars = []
    for b in sorted(buckets):
        prices = buckets[b]
        bars.append({"time": b * bucket_s, "open": prices[0], "high": max(prices),
                      "low": min(prices), "close": prices[-1], "volume": len(prices)})
    return bars
