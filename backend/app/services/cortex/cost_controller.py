"""Cost Controller — mandatory budget guard for every Cortex call.

Owner-locked (#014): NOT optional. Each agent call = 1 API call; a Council /
Planner fan-out can be ~10 calls. Without caps a single button could cost
₹100+. This module enforces:

  • a per-IST-day call cap  (settings.ai_daily_call_cap)
  • a per-IST-day ₹ cap     (settings.ai_daily_cost_cap_inr)

It keeps an in-memory ledger that resets at IST midnight (single Time Service).
`check()` is called BEFORE a request; `record()` AFTER, with token usage. When
a cap is hit, `check()` returns allowed=False and the provider refuses with an
honest message — never a silent overspend.

Cost estimate uses a per-model $/1M-token table × USD→INR. Numbers are
estimates for display/guarding; the provider records real token counts when the
SDK returns them.
"""
from __future__ import annotations

from typing import Any

from ...config import settings
from ...core.clock import today_str

# $ per 1M tokens (input, output). Estimates for the Cost Controller guard.
_PRICING: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    # Gemini (public list prices; override via table if they drift)
    "gemini-2.5-pro": (1.25, 10.0),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-flash-latest": (0.30, 2.50),
}
_DEFAULT_PRICE = (3.0, 15.0)


class _Ledger:
    def __init__(self) -> None:
        self.day = today_str()
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost_inr = 0.0
        self.entries: list[dict[str, Any]] = []

    def _roll(self) -> None:
        d = today_str()
        if d != self.day:
            self.day = d
            self.calls = 0
            self.input_tokens = 0
            self.output_tokens = 0
            self.cost_inr = 0.0
            self.entries = []


_ledger = _Ledger()


def price_inr(model: str, in_tok: int, out_tok: int) -> float:
    pin, pout = _PRICING.get(model, _DEFAULT_PRICE)
    usd = (in_tok / 1_000_000) * pin + (out_tok / 1_000_000) * pout
    return round(usd * settings.usd_inr, 4)


def check() -> dict[str, Any]:
    """Gate a request BEFORE it is made."""
    _ledger._roll()
    if _ledger.calls >= settings.ai_daily_call_cap:
        return {"allowed": False,
                "reason": f"Daily call cap reached ({settings.ai_daily_call_cap}). "
                          "Resets at IST midnight."}
    if _ledger.cost_inr >= settings.ai_daily_cost_cap_inr:
        return {"allowed": False,
                "reason": f"Daily ₹ cap reached (₹{settings.ai_daily_cost_cap_inr:.0f}). "
                          "Resets at IST midnight."}
    return {"allowed": True, "reason": ""}


def record(role: str, model: str, in_tok: int, out_tok: int) -> float:
    _ledger._roll()
    cost = price_inr(model, in_tok, out_tok)
    _ledger.calls += 1
    _ledger.input_tokens += in_tok
    _ledger.output_tokens += out_tok
    _ledger.cost_inr = round(_ledger.cost_inr + cost, 4)
    _ledger.entries.append(
        {"role": role, "model": model, "in": in_tok, "out": out_tok, "inr": cost})
    if len(_ledger.entries) > 200:
        _ledger.entries = _ledger.entries[-200:]
    return cost


def report() -> dict[str, Any]:
    """Live budget view for the Cost Monitor (Governance #015 reuses this)."""
    _ledger._roll()
    return {
        "day": _ledger.day,
        "calls": _ledger.calls,
        "call_cap": settings.ai_daily_call_cap,
        "input_tokens": _ledger.input_tokens,
        "output_tokens": _ledger.output_tokens,
        "cost_inr_today": round(_ledger.cost_inr, 2),
        "cost_cap_inr": settings.ai_daily_cost_cap_inr,
        "budget_left_inr": round(
            max(0.0, settings.ai_daily_cost_cap_inr - _ledger.cost_inr), 2),
        "recent": _ledger.entries[-10:],
    }
