"""RVE-002 — Day State Descriptor Research (2026-08-02).

RESEARCH ARTIFACT. Not production. Imported by nothing. Read-only.
    python3 research/RVE_002_analysis.py

CONTEXT
    RVE-001 found that apparent "pattern edge" was a stack of confounds:
    day-concentration -> regime -> SYMBOL -> the metric itself. Its own
    conclusion ("the day dominates") was then partly superseded when the
    symbol audit showed much of that day-swing was premium-scale.

    The open question it left: what actually defines a trading day, in a way
    that REPEATS? The 5-label regime taxonomy demonstrably does not
    (within-regime across-day spread 52-66pp vs 25pp between regimes).

METRIC FIX (the precondition RVE-001 established)
    RVE-001 used `potential >= N` — ABSOLUTE premium points. That is not
    comparable across symbols: 20pt on a Rs441 GOLD premium is a 4.5% move,
    on a Rs59 NIFTY premium it is 34%. This experiment uses `peak_rise >= X%`
    — the premium's own percentage move — which IS symbol-independent.

    NOT USED, and why: the owner proposed an ATR-multiple metric (move / ATR),
    which is the professionally correct normalisation. It is NOT computable
    from recorded data: `engine.atr` is the UNDERLYING's ATR (index points,
    ~0.1% of underlying), while `potential`/`peak_rise` describe the PREMIUM.
    Dividing one by the other mixes units. Computing a true ATR-multiple would
    require recording the premium's own ATR (or the underlying move per
    episode) — logged as a future recording requirement, not done here.

CONTROLS APPLIED (each one RVE-001 lacked)
    - SYMBOL   : analysed per-symbol, never pooled across premium scales
    - DTE      : days-to-expiry, added on the owner's instruction (theta / IV /
                 gamma behave differently 0 vs 4 days out)
    - DAY      : day-level features tested against day-level outcome

FEATURES TESTED (only what is actually recorded; continuous, not labels)
    ADX, ATR% (atr/underlying), Trend score, Liquidity score, MTF score,
    time-of-day block, dte.
"""
from __future__ import annotations

import glob
import json
import statistics
from collections import defaultdict

LOG_GLOB = "/Users/macbookair/cloud-ai-trader/data/opportunity_log/*.jsonl"
RISE_PCT = 30          # symbol-independent: premium rose >= 30%
MIN_CELL = 20


def load():
    out = []
    for f in sorted(glob.glob(LOG_GLOB)):
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def rise(rows, pct=RISE_PCT):
    """Symbol-independent reach: premium rose >= pct%."""
    if not rows:
        return None
    return round(100 * sum(1 for r in rows if (r.get("peak_rise") or 0) >= pct) / len(rows), 1)


def pearson(xs, ys):
    if len(xs) < 3:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    return round(num / den, 3) if den else None


def time_block(hhmmss):
    if not hhmmss:
        return None
    try:
        h = int(hhmmss.split(":")[0]) + int(hhmmss.split(":")[1]) / 60
    except Exception:
        return None
    if h < 10:
        return "OPEN"
    if h < 12:
        return "MORNING"
    if h < 14:
        return "MIDDAY"
    return "CLOSE"


def main():
    records = load()
    alerted = [r for r in records if r.get("t_ignite") and r.get("day") and r.get("symbol")]
    print(f"alerted with symbol+day: {len(alerted)}")
    print(f"metric: peak_rise >= {RISE_PCT}%  (symbol-independent)\n")

    # ---- 1. within-symbol day variation, on the FIXED metric --------------
    print("=== 1. WITHIN-SYMBOL day variation (metric now symbol-independent) ===")
    by_sym = defaultdict(lambda: defaultdict(list))
    for r in alerted:
        by_sym[r["symbol"]][r["day"]].append(r)
    sym_spreads = {}
    for sym in sorted(by_sym, key=lambda s: -sum(len(v) for v in by_sym[s].values())):
        days = {d: v for d, v in by_sym[sym].items() if len(v) >= MIN_CELL}
        if len(days) < 2:
            continue
        vals = {d: rise(v) for d, v in sorted(days.items())}
        sp = round(max(vals.values()) - min(vals.values()), 1)
        sym_spreads[sym] = sp
        print(f"  {sym}  (n={sum(len(v) for v in days.values())}, {len(days)} days)"
              f"  spread {sp}pp")
        for d, v in vals.items():
            print(f"      {d}  {v:5.1f}%   n={len(days[d])}")
    print()

    # ---- 2. does DTE explain it? (owner's addition) ----------------------
    print("=== 2. DTE (days-to-expiry) effect, per symbol ===")
    for sym in ("NIFTY", "SENSEX"):
        rows = [r for r in alerted if r["symbol"] == sym and r.get("dte") is not None]
        if len(rows) < MIN_CELL:
            continue
        buckets = defaultdict(list)
        for r in rows:
            buckets[r["dte"]].append(r)
        cells = {k: v for k, v in buckets.items() if len(v) >= MIN_CELL}
        if not cells:
            continue
        print(f"  {sym} (n={len(rows)} with dte)")
        for d in sorted(cells):
            print(f"      dte={d}  {rise(cells[d]):5.1f}%   n={len(cells[d])}")
        vals = [rise(v) for v in cells.values()]
        if len(vals) > 1:
            print(f"      --> dte spread {round(max(vals)-min(vals),1)}pp")
    print()

    # ---- 3. continuous day-state features vs day outcome -----------------
    print("=== 3. Do CONTINUOUS day-state features explain the day variation? ===")
    print("    (per symbol; each row = one day; correlation with that day's rise-rate)\n")
    for sym in ("NIFTY", "SENSEX"):
        days = {d: v for d, v in by_sym[sym].items() if len(v) >= MIN_CELL}
        if len(days) < 3:
            print(f"  {sym}: only {len(days)} usable days — cannot correlate\n")
            continue
        feats = defaultdict(list)
        y = []
        print(f"  --- {sym} ---")
        print(f"    {'day':12s} {'rise%':>7s} {'ADX':>7s} {'ATR%':>8s} {'Trend':>7s} {'Liq':>6s} {'MTF':>6s}")
        for d in sorted(days):
            rows = days[d]
            e = [r.get("engine") or {} for r in rows]
            adx = [x["adx"] for x in e if x.get("adx") is not None]
            atrp = [x["atr"] / x["underlying"] * 100 for x in e
                    if x.get("atr") and x.get("underlying")]
            L = [x.get("layers") or {} for x in e]
            tr = [l["Trend"] for l in L if l.get("Trend") is not None]
            lq = [l["Liquidity"] for l in L if l.get("Liquidity") is not None]
            mt = [l["MTF"] for l in L if l.get("MTF") is not None]
            if not adx:
                continue
            row_y = rise(rows)
            y.append(row_y)
            feats["ADX"].append(statistics.fmean(adx))
            feats["ATR%"].append(statistics.fmean(atrp) if atrp else 0)
            feats["Trend"].append(statistics.fmean(tr) if tr else None)
            feats["Liquidity"].append(statistics.fmean(lq) if lq else None)
            feats["MTF"].append(statistics.fmean(mt) if mt else None)
            print(f"    {d:12s} {row_y:6.1f}% {statistics.fmean(adx):7.1f}"
                  f" {(statistics.fmean(atrp) if atrp else 0):7.3f}%"
                  f" {(statistics.fmean(tr) if tr else float('nan')):7.1f}"
                  f" {(statistics.fmean(lq) if lq else float('nan')):6.1f}"
                  f" {(statistics.fmean(mt) if mt else float('nan')):6.1f}")
        print(f"\n    correlation with day rise-rate (n={len(y)} days):")
        for k, xs in feats.items():
            pairs = [(a, b) for a, b in zip(xs, y) if a is not None]
            if len(pairs) >= 3:
                r = pearson([a for a, _ in pairs], [b for _, b in pairs])
                print(f"      {k:10s} r = {r if r is not None else 'n/a'}   (n={len(pairs)})")
        print()

    # ---- 4. time-of-day block --------------------------------------------
    print("=== 4. Time-of-day block (is 'when in the session' a descriptor?) ===")
    for sym in ("NIFTY", "SENSEX"):
        rows = [r for r in alerted if r["symbol"] == sym]
        blocks = defaultdict(list)
        for r in rows:
            b = time_block(r.get("t_ignite"))
            if b:
                blocks[b].append(r)
        cells = {k: v for k, v in blocks.items() if len(v) >= MIN_CELL}
        if not cells:
            continue
        print(f"  {sym}")
        for b in ("OPEN", "MORNING", "MIDDAY", "CLOSE"):
            if b in cells:
                print(f"      {b:8s} {rise(cells[b]):5.1f}%   n={len(cells[b])}")
        vals = [rise(v) for v in cells.values()]
        if len(vals) > 1:
            print(f"      --> time-block spread {round(max(vals)-min(vals),1)}pp")
    print()

    print("=== SUMMARY ===")
    print(f"  within-symbol day spread (normalised): "
          f"{ {k: f'{v}pp' for k, v in sym_spreads.items()} }")
    print("  See RVE_002_day_state_descriptor.md for interpretation and caveats.")


if __name__ == "__main__":
    main()
