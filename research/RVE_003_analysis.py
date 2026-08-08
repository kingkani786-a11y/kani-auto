"""RVE-003 — Opening-Range runner predictability. Reproducible analysis.

Run:  cd backend && python3 ../research/RVE_003_analysis.py

Requires the ORFE candle cache to exist (data/orfe_research/_candles_*.json.gz),
populated by one live run per symbol:
    POST /api/orfe-research/run?symbol=<SYM>&months=6

Reads only. Writes RVE_003_results.csv next to this file. Touches no live
module, no threshold, no gate.
"""
from __future__ import annotations

import collections
import csv
import json
import os
import pathlib
import statistics as stt
import sys

os.environ.setdefault("CAT_RESEARCH_MODE", "1")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from app.services import orfe_research as o  # noqa: E402

SYMBOLS = ("NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY")

# Pre-declared feature set. Fixed BEFORE looking at outcomes, and reported in
# full below whatever the result — the point is to avoid reporting only
# whichever feature happened to look elevated (the RVE-001 failure mode).
FEATURES = ("or_width_pct", "gap_pct", "or_vol_share", "adx", "rsi", "atr")

# One consistent entry rule across every setup, so the comparison isolates
# "what preceded a big move", not "which entry was used".
REFERENCE_LEVEL = 0.618
RUNNER_PERCENTILE = 0.90


def collect() -> list[dict]:
    out: list[dict] = []
    for sym in SYMBOLS:
        cached = o._load_cached_candles(sym)
        if not cached:
            print(f"  [skip] {sym}: no candle cache")
            continue
        candles, _ = cached
        days = o._group_by_day(candles)
        prev_close = None
        for day in sorted(days):
            dcs = sorted(days[day], key=lambda x: x["time"])
            rows = o._process_day(day, dcs)
            setup = next((r for r in rows if r.get("kind") == "setup"), None)
            first = dcs[0]
            gap_pct = ((first["open"] - prev_close) / prev_close * 100) if prev_close else None
            prev_close = dcs[-1]["close"]
            if not setup:
                continue
            or_vol = sum(x.get("volume", 0) for x in dcs
                         if o.OR_START <= o._hm(x["time"]) < o.OR_END)
            day_vol = sum(x.get("volume", 0) for x in dcs)
            trade = next((r for r in rows if r.get("kind") == "touch"
                          and r["fib_level"] == REFERENCE_LEVEL
                          and r["outcome"] != "OPEN"), None)
            if not trade:
                continue
            risk = abs(trade["entry_px"] - trade["stop_px"])
            if risk <= 0:
                continue
            if trade["outcome"] == "LOSS":
                r_mult = -1.0
            elif trade["outcome"] == "WIN_T1":
                r_mult = abs(trade["target1_px"] - trade["entry_px"]) / risk
            else:
                r_mult = abs(trade["target2_px"] - trade["entry_px"]) / risk
            out.append({
                "sym": sym, "day": day, "R": r_mult,
                "or_width_pct": setup["or_range"] / first["open"] * 100,
                "gap_pct": gap_pct,
                "or_vol_share": (or_vol / day_vol * 100) if day_vol else None,
                "adx": setup.get("adx_930"), "rsi": setup.get("rsi_930"),
                "atr": setup.get("atr_930"),
                "regime": setup.get("regime"), "bias": setup.get("bias"),
            })
    return out


def main() -> None:
    rec = collect()
    if not rec:
        print("no records — populate the candle cache first")
        return
    rs = sorted(r["R"] for r in rec)
    thr = rs[int(RUNNER_PERCENTILE * len(rs))]
    top = [r for r in rec if r["R"] >= thr]
    rest = [r for r in rec if r["R"] < thr]

    print(f"trades: {len(rec)}   runner threshold R>={thr:.2f}   "
          f"runners={len(top)} rest={len(rest)}")
    total, top_r = sum(rs), sum(x for x in rs if x >= thr)
    print(f"CONCENTRATION: top decile = {100*top_r/total:.0f}% of total R "
          f"({top_r:.1f} of {total:.1f})")
    print(f"R: min {rs[0]:.2f} p25 {rs[len(rs)//4]:.2f} median {rs[len(rs)//2]:.2f} "
          f"p75 {rs[3*len(rs)//4]:.2f} max {rs[-1]:.2f}")
    print()
    print(f"{'FEATURE':<16}{'RUNNERS':<12}{'REST':<12}{'ratio':<8}")
    rows_out = []
    for k in FEATURES:
        a = [r[k] for r in top if r.get(k) is not None]
        b = [r[k] for r in rest if r.get(k) is not None]
        if not a or not b:
            continue
        ma, mb = stt.median(a), stt.median(b)
        ratio = (ma / mb) if abs(mb) > 1e-9 else float("nan")
        print(f"{k:<16}{ma:<12.3f}{mb:<12.3f}{ratio:<8.2f}")
        rows_out.append({"feature": k, "runners_median": round(ma, 4),
                         "rest_median": round(mb, 4), "ratio": round(ratio, 3),
                         "n_runners": len(a), "n_rest": len(b)})
    for k in ("regime", "bias", "sym"):
        print(f"{k}: runners={dict(collections.Counter(r[k] for r in top))} "
              f"rest={dict(collections.Counter(r[k] for r in rest))}")

    with (pathlib.Path(__file__).parent / "RVE_003_results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["feature", "runners_median", "rest_median",
                                          "ratio", "n_runners", "n_rest"])
        w.writeheader()
        w.writerows(rows_out)
    print("\nwrote RVE_003_results.csv")


if __name__ == "__main__":
    main()
