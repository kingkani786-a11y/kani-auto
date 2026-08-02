"""RVE-001 — Conditional Outcome Validation Experiment (2026-08-02).

RESEARCH ARTIFACT. Not a production module. Not imported by anything.
Read-only over the existing black box. Run manually:

    python3 research/RVE_001_analysis.py            # human-readable report
    python3 research/RVE_001_analysis.py --csv      # also write results CSV

QUESTION
    The Opportunity Ladder shows point-reach probabilities (5pt 72%, 10pt 51%,
    20pt 27% ...). Those come from opportunity_metrics.outcome_stats(), which
    pools the ENTIRE black box — one global base rate, identical for every
    symbol, every regime, every setup.

    Do CONDITIONAL patterns (this setup, right now) have materially different
    reach-rates than that base rate? If yes, a Live Similarity Engine (V9
    Stage 2B) has something real to show. If no, no amount of UI creates edge
    that isn't in the data.

METRIC (deliberately identical to outcome_stats(), so results are
apples-to-apples with the ladder's own numbers):
    population : episodes with t_ignite  (alerted only)
    reach @ N  : potential >= N          (potential = peak - base)

FOUR TESTS, in order of increasing rigour:
    T1  naive across-day pattern separation
    T2  controlled — same conditions, one variable differs + day-concentration
    T3  within-day — does the condition still separate once DAY is held fixed?
    T4  does REGIME explain the day effect? (is 'day' a repeatable market state?)

See RVE_001_conditional_outcome_experiment.md for findings and caveats.
"""
from __future__ import annotations

import glob
import json
import statistics
import sys
from collections import defaultdict

LOG_GLOB = "/Users/macbookair/cloud-ai-trader/data/opportunity_log/*.jsonl"
PTS = [5, 10, 20, 30, 40, 50, 80, 100]
KEY_PTS = [5, 10, 20, 30, 50]
MIN_N = 30

# Declared cut-points for the binary condition tags. UNVALIDATED — the right
# split may well be elsewhere; that is itself an open question (see the .md).
OI_BUILD_MIN = 60
TREND_STRONG_MIN = 60


def load():
    rows = []
    for f in sorted(glob.glob(LOG_GLOB)):
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def reach(rows, p=20):
    if not rows:
        return None
    return round(100 * sum(1 for r in rows if (r.get("potential") or 0) >= p) / len(rows), 1)


def reach_table(rows):
    return len(rows), {p: reach(rows, p) for p in PTS}


def core_tags(r):
    """CORE conditions only — regime/session deliberately EXCLUDED, because
    they are largely day-level properties and would confound any
    'does the setup matter' question (this is the whole point of T3)."""
    e = r.get("engine") or {}
    L = e.get("layers") or {}
    t = []
    if e.get("vwap") and e.get("underlying"):
        t.append("VWAP_ABOVE" if e["underlying"] > e["vwap"] else "VWAP_BELOW")
    if L.get("OI") is not None:
        t.append("OI_BUILD" if L["OI"] >= OI_BUILD_MIN else "OI_WEAK")
    if L.get("Trend") is not None:
        t.append("TREND_STRONG" if L["Trend"] >= TREND_STRONG_MIN else "TREND_WEAK")
    return sorted(t)


def full_tags(r):
    t = core_tags(r)
    if r.get("regime"):
        t.append(f"REGIME_{r['regime']}")
    if r.get("session_type"):
        t.append(f"SESSION_{r['session_type']}")
    return sorted(t)


def main(write_csv=False):
    records = load()
    alerted = [r for r in records if r.get("t_ignite")]
    taggable = [r for r in alerted
                if (r.get("engine") or {}).get("layers")
                and (r.get("engine") or {}).get("vwap") and r.get("day")]

    print(f"total records                    : {len(records)}")
    print(f"alerted (ladder's own population): {len(alerted)}")
    print(f"alerted WITH condition data      : {len(taggable)}"
          f"   <- pre-2026-07-22 rows lack layers (known join bug)")

    base_n, base = reach_table(alerted)
    print(f"\n=== GLOBAL BASE RATE (what the Opportunity Ladder shows today) ===")
    for p in PTS:
        print(f"  {p:3d}pt : {base[p]:5.1f}%")

    # ---------------- T1: naive across-day separation --------------------
    print(f"\n=== T1  NAIVE across-day pattern separation (n>={MIN_N}) ===")
    groups = defaultdict(list)
    for r in taggable:
        groups["|".join(full_tags(r))].append(r)
    sized = {k: v for k, v in groups.items() if len(v) >= MIN_N}
    print(f"  distinct patterns: {len(groups)}   with n>={MIN_N}: {len(sized)}")
    t1 = []
    for sig, rows in sorted(sized.items(), key=lambda kv: -len(kv[1])):
        n, tbl = reach_table(rows)
        days = len({r["day"] for r in rows})
        top = max(sum(1 for r in rows if r["day"] == d) for d in {r["day"] for r in rows})
        t1.append((sig, n, days, round(100 * top / n, 1), tbl))
    for sig, n, days, conc, tbl in t1:
        print(f"\n  n={n:4d} days={days} biggest-day={conc:5.1f}%  {sig}")
        print("        " + "  ".join(f"{p}pt {tbl[p]:5.1f}%" for p in KEY_PTS))
    print("\n  --- spread vs base ---")
    for p in KEY_PTS:
        vals = [tbl[p] for *_, tbl in t1 if tbl[p] is not None]
        if len(vals) >= 2:
            print(f"  {p:3d}pt  base {base[p]:5.1f}%  range {min(vals):5.1f}..{max(vals):5.1f}%"
                  f"  spread {round(max(vals)-min(vals),1):5.1f}pp  stdev {round(statistics.pstdev(vals),1)}")

    # ---------------- T2: controlled, one variable differs ---------------
    print(f"\n=== T2  CONTROLLED — identical conditions, only OI differs ===")
    print("    (REGIME_TRENDING + SESSION_NORMAL + TREND_STRONG + VWAP_ABOVE)")
    for oi in ("OI_BUILD", "OI_WEAK"):
        want = sorted([oi, "REGIME_TRENDING", "SESSION_NORMAL", "TREND_STRONG", "VWAP_ABOVE"])
        rows = [r for r in taggable if full_tags(r) == want]
        if not rows:
            continue
        n, tbl = reach_table(rows)
        days = {r["day"] for r in rows}
        top = max(sum(1 for r in rows if r["day"] == d) for d in days)
        print(f"\n  {oi:9s} n={n:4d} days={len(days)} biggest-day-share={round(100*top/n,1)}%")
        print("        " + "  ".join(f"{p}pt {tbl[p]:5.1f}%" for p in KEY_PTS))

    # ---------------- T3: within-day (the decisive one) ------------------
    print(f"\n=== T3  WITHIN-DAY — day held fixed, do CORE conditions separate? ===")
    by_day = defaultdict(lambda: defaultdict(list))
    for r in taggable:
        by_day[r["day"]]["|".join(core_tags(r))].append(r)
    spreads = []
    for day in sorted(by_day):
        cells = {k: v for k, v in by_day[day].items() if len(v) >= 15}
        if len(cells) < 2:
            continue
        day_rows = [r for v in by_day[day].values() for r in v]
        print(f"\n  {day}  (day base {reach(day_rows):5.1f}%)")
        vals = []
        for sig, rows in sorted(cells.items(), key=lambda kv: -(reach(kv[1]) or 0)):
            vals.append(reach(rows))
            print(f"      {reach(rows):5.1f}%  n={len(rows):4d}  {sig}")
        sp = round(max(vals) - min(vals), 1)
        spreads.append((day, sp))
        print(f"      --> within-day spread {sp}pp")
    if spreads:
        print(f"\n  average within-day spread: "
              f"{round(sum(s for _, s in spreads)/len(spreads),1)}pp")

    print(f"\n  --- direction consistency: does OI_BUILD beat OI_WEAK within a day? ---")
    for day in sorted(by_day):
        b = [r for k, v in by_day[day].items() if "OI_BUILD" in k for r in v]
        w = [r for k, v in by_day[day].items() if "OI_WEAK" in k for r in v]
        if len(b) >= 15 and len(w) >= 15:
            rb, rw = reach(b), reach(w)
            print(f"    {day}: BUILD {rb:5.1f}%(n={len(b):3d})  WEAK {rw:5.1f}%(n={len(w):3d})"
                  f"  -> {'BUILD' if rb > rw else 'WEAK'} wins")

    # ---------------- T4: is 'day' a repeatable market state? ------------
    print(f"\n=== T4  Does REGIME explain the day effect? ===")
    print("    (if a regime is a repeatable state, the SAME regime should give")
    print("     similar reach on DIFFERENT days)\n")
    cells = defaultdict(list)
    for r in alerted:
        if r.get("regime") and r.get("day"):
            cells[(r["day"], r["regime"])].append(r)
    by_reg = defaultdict(list)
    for (day, reg), rows in cells.items():
        if len(rows) >= 20:
            by_reg[reg].append((day, len(rows), reach(rows)))
    for reg, entries in sorted(by_reg.items()):
        if len(entries) < 2:
            print(f"  {reg:18s} only {len(entries)} day(s) — cannot test")
            continue
        vals = [v for _, _, v in entries]
        print(f"  {reg:18s} across-day spread {round(max(vals)-min(vals),1):5.1f}pp"
              f"   [{', '.join(f'{d}:{v}%' for d, _, v in sorted(entries))}]")

    print("\n  --- pooled by regime (all days together) ---")
    pooled = defaultdict(list)
    for r in alerted:
        if r.get("regime"):
            pooled[r["regime"]].append(r)
    for reg, rows in sorted(pooled.items(), key=lambda kv: -(reach(kv[1]) or 0)):
        print(f"    {reg:18s} n={len(rows):5d} days={len({r['day'] for r in rows})}"
              f"  20pt {reach(rows):5.1f}%  50pt {reach(rows,50):5.1f}%")

    if write_csv:
        import csv
        out = "research/RVE_001_results.csv"
        with open(out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["test", "group", "n", "days", "biggest_day_share_pct"]
                       + [f"reach_{p}pt_pct" for p in KEY_PTS])
            w.writerow(["BASE", "ALL_ALERTED", base_n, "", ""]
                       + [base[p] for p in KEY_PTS])
            for sig, n, days, conc, tbl in t1:
                w.writerow(["T1_PATTERN", sig, n, days, conc] + [tbl[p] for p in KEY_PTS])
            for reg, rows in pooled.items():
                w.writerow(["T4_REGIME_POOLED", reg, len(rows),
                            len({r['day'] for r in rows}), ""]
                           + [reach(rows, p) for p in KEY_PTS])
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main(write_csv="--csv" in sys.argv)
