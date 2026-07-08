"""Black-Scholes Greeks + implied volatility (no scipy needed)."""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


@dataclass
class Greeks:
    delta: float
    gamma: float
    theta: float   # per calendar day
    vega: float    # per 1 vol point
    iv: float      # decimal, e.g. 0.14

    def dict(self) -> dict:
        return asdict(self)


def bs_price(S: float, K: float, t: float, r: float, sigma: float, is_call: bool) -> float:
    if t <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return max(0.0, (S - K) if is_call else (K - S))
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    if is_call:
        return S * _norm_cdf(d1) - K * math.exp(-r * t) * _norm_cdf(d2)
    return K * math.exp(-r * t) * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def implied_vol(price: float, S: float, K: float, t: float, r: float, is_call: bool) -> float:
    """Bisection — robust against the flat-vega wings."""
    if price <= 0 or t <= 0:
        return 0.0
    lo, hi = 0.01, 3.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if bs_price(S, K, t, r, mid, is_call) > price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def compute_greeks(
    S: float, K: float, t_years: float, r: float, option_price: float, is_call: bool,
    iv_hint: float = 0.0,
) -> Greeks:
    sigma = iv_hint if iv_hint > 0 else implied_vol(option_price, S, K, t_years, r, is_call)
    if t_years <= 0 or sigma <= 0:
        return Greeks(0.0, 0.0, 0.0, 0.0, sigma)
    sq_t = math.sqrt(t_years)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * t_years) / (sigma * sq_t)
    d2 = d1 - sigma * sq_t
    delta = _norm_cdf(d1) if is_call else _norm_cdf(d1) - 1.0
    gamma = _norm_pdf(d1) / (S * sigma * sq_t)
    vega = S * _norm_pdf(d1) * sq_t / 100.0
    theta_core = -(S * _norm_pdf(d1) * sigma) / (2 * sq_t)
    if is_call:
        theta = (theta_core - r * K * math.exp(-r * t_years) * _norm_cdf(d2)) / 365.0
    else:
        theta = (theta_core + r * K * math.exp(-r * t_years) * _norm_cdf(-d2)) / 365.0
    return Greeks(round(delta, 4), round(gamma, 6), round(theta, 2), round(vega, 2), round(sigma, 4))
