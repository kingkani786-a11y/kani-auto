"""Technical indicators over OHLCV candles: EMA, VWAP, ATR, ADX, momentum."""
from __future__ import annotations


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def vwap(candles: list[dict]) -> float:
    pv = vol = 0.0
    for c in candles:
        tp = (c["high"] + c["low"] + c["close"]) / 3.0
        v = max(float(c.get("volume", 0)), 0.0)
        pv += tp * v
        vol += v
    if vol == 0:  # indices report no volume — fall back to typical-price mean
        return sum((c["high"] + c["low"] + c["close"]) / 3.0 for c in candles) / max(len(candles), 1)
    return pv / vol


def atr(candles: list[dict], period: int = 14) -> float:
    if len(candles) < 2:
        return 0.0
    trs = []
    for prev, cur in zip(candles, candles[1:]):
        trs.append(max(
            cur["high"] - cur["low"],
            abs(cur["high"] - prev["close"]),
            abs(cur["low"] - prev["close"]),
        ))
    period = min(period, len(trs))
    a = sum(trs[:period]) / period
    for tr in trs[period:]:
        a = (a * (period - 1) + tr) / period
    return a


def adx(candles: list[dict], period: int = 14) -> float:
    if len(candles) < period + 2:
        return 0.0
    plus_dm, minus_dm, trs = [], [], []
    for prev, cur in zip(candles, candles[1:]):
        up = cur["high"] - prev["high"]
        dn = prev["low"] - cur["low"]
        plus_dm.append(up if (up > dn and up > 0) else 0.0)
        minus_dm.append(dn if (dn > up and dn > 0) else 0.0)
        trs.append(max(
            cur["high"] - cur["low"],
            abs(cur["high"] - prev["close"]),
            abs(cur["low"] - prev["close"]),
        ))

    def smooth(xs: list[float]) -> list[float]:
        out = [sum(xs[:period])]
        for x in xs[period:]:
            out.append(out[-1] - out[-1] / period + x)
        return out

    str_, spd, smd = smooth(trs), smooth(plus_dm), smooth(minus_dm)
    dxs = []
    for tr_v, pd_v, md_v in zip(str_, spd, smd):
        if tr_v == 0:
            continue
        pdi, mdi = 100 * pd_v / tr_v, 100 * md_v / tr_v
        if pdi + mdi:
            dxs.append(100 * abs(pdi - mdi) / (pdi + mdi))
    if len(dxs) < period:
        return dxs[-1] if dxs else 0.0
    a = sum(dxs[:period]) / period
    for d in dxs[period:]:
        a = (a * (period - 1) + d) / period
    return a


def momentum(closes: list[float], period: int = 10) -> float:
    """Rate of change, percent."""
    if len(closes) <= period or closes[-period - 1] == 0:
        return 0.0
    return (closes[-1] / closes[-period - 1] - 1.0) * 100.0


def trend_state(closes: list[float]) -> dict:
    """EMA(9/21) regime classification."""
    if len(closes) < 21:
        return {"trend": "NEUTRAL", "ema9": 0.0, "ema21": 0.0}
    e9, e21 = ema(closes, 9)[-1], ema(closes, 21)[-1]
    last = closes[-1]
    if e9 > e21 and last > e9:
        t = "BULLISH"
    elif e9 < e21 and last < e9:
        t = "BEARISH"
    else:
        t = "NEUTRAL"
    return {"trend": t, "ema9": round(e9, 2), "ema21": round(e21, 2)}


def trend_engine(candles: list[dict], session_vwap: float) -> dict:
    """Layer 1 — institutional trend stack: EMA 20/50/200 + VWAP + ADX."""
    closes = [c["close"] for c in candles]
    if len(closes) < 30:
        return {"direction": "NEUTRAL", "score_bull": 50, "score_bear": 50,
                "trend": "NEUTRAL", "notes": []}

    e20 = ema(closes, 20)[-1]
    e50 = ema(closes, min(50, len(closes)))[-1]
    e200 = ema(closes, min(200, len(closes)))[-1]
    adx_v = adx(candles)
    last = closes[-1]
    notes: list[str] = []
    bull = bear = 50.0

    stack_bull = e20 > e50 > e200
    stack_bear = e20 < e50 < e200
    if stack_bull and last > e20:
        bull += 22; bear -= 15
        notes.append("EMA stack 20>50>200 with price above — established uptrend")
    elif stack_bear and last < e20:
        bear += 22; bull -= 15
        notes.append("EMA stack 20<50<200 with price below — established downtrend")
    elif e20 > e50:
        bull += 8
    elif e20 < e50:
        bear += 8

    if session_vwap > 0:
        if last > session_vwap:
            bull += 8
            notes.append("Price above VWAP — buyers paying up")
        else:
            bear += 8
            notes.append("Price below VWAP — sellers in control")

    strength = max(0.0, min(1.0, (adx_v - 15) / 25))
    if bull > bear:
        bull += strength * 10
    elif bear > bull:
        bear += strength * 10
    if adx_v >= 25:
        notes.append(f"ADX {adx_v:.0f} confirms trend strength")

    bull, bear = max(0, min(100, bull)), max(0, min(100, bear))
    direction = "BULL" if bull - bear >= 10 else "BEAR" if bear - bull >= 10 else "NEUTRAL"
    return {
        "direction": direction,
        "score_bull": round(bull, 1),
        "score_bear": round(bear, 1),
        "trend": "BULLISH" if direction == "BULL" else "BEARISH" if direction == "BEAR" else "NEUTRAL",
        "ema20": round(e20, 2), "ema50": round(e50, 2), "ema200": round(e200, 2),
        "vwap": round(session_vwap, 2), "adx": round(adx_v, 1),
        "notes": notes,
    }
