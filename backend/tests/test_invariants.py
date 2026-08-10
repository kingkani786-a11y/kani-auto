"""Regression tests for the invariants this system must never silently break.

Run:   cd backend && python3 -m unittest discover -s tests -v

WHY STDLIB unittest AND NOT pytest: pytest is not installed in this venv, and
adding it would change requirements/CI/Docker for a repo whose whole discipline
is small, provable, isolated changes. unittest ships with Python, so these run
anywhere the app runs, with no new dependency.

WHY THIS FILE EXISTS: every regression proven during development (2026-08-07/08)
was throwaway inline Python — real verification that evaporated the moment the
shell exited. Nothing was re-runnable, so a later edit could quietly undo a
proven property and nobody would find out. These are the properties that were
actually verified by hand; they are now permanent.

Every test here is OFFLINE — no broker connection, no live state, no writes to
any production data directory (each test redirects module data dirs to a temp
path). CAT_RESEARCH_MODE is set before app imports so no module can checkpoint
into production state.
"""
from __future__ import annotations

import ast
import datetime
import json
import os
import pathlib
import tempfile
import unittest

os.environ.setdefault("CAT_RESEARCH_MODE", "1")   # must precede app imports

from app.core.clock import IST                                    # noqa: E402
from app.engines import confluence                                # noqa: E402
from app.engines.technicals import rsi                            # noqa: E402
from app.services import audit                                    # noqa: E402
from app.services import decision_contract                        # noqa: E402
from app.services import orfe_research as orfe                    # noqa: E402
from app.services import shadow_calibration as sc                 # noqa: E402
from app.services.analytics import _calibration, _confidence_buckets  # noqa: E402

_BACKEND = pathlib.Path(__file__).resolve().parents[1]


def _audit_rec(conf: float, win: int, ts: float, with_new_fields: bool = True) -> dict:
    """A settled audit record, shaped exactly as audit._settle() writes one."""
    r = {
        "action": "WAIT", "hypothetical": True, "reached": 1 if win else 0,
        "sl_hit": not win, "win": win, "runner_prob": 50.0, "expected_move": 20.0,
        "actual_expansion": 10.0, "atr": 10.0, "animal": "WOLF", "clarity": "CLEAR",
        "data_confidence": "HIGH", "regime": "TRENDING", "session": "MID", "ts": ts,
    }
    if with_new_fields:
        r["signal_confidence"] = float(conf)
        r["direction"] = "BULL"
    return r


class ShadowCalibrationTests(unittest.TestCase):
    """The module built to break the calibration deadlock. Its whole value
    depends on being (a) numerically comparable to the real score and
    (b) structurally unable to influence trading."""

    def setUp(self):
        sc._DATA_DIR = pathlib.Path(tempfile.mkdtemp())
        sc._seen_ts.clear()
        audit._history.clear()

    def test_formula_is_identical_to_the_real_calibration(self):
        """The point of Shadow Calibration is comparability with the REAL
        score. If this drifts, the two numbers stop meaning the same thing
        and the whole module becomes misleading rather than useful."""
        recs = [(65, 1), (65, 1), (65, 1), (65, 1), (65, 0),
                (75, 1), (75, 1), (75, 1), (75, 0), (75, 0), (75, 0),
                (85, 1), (85, 1), (85, 1), (85, 1), (85, 1)]
        for i, (c, w) in enumerate(recs):
            audit._history.append(_audit_rec(c, w, 1786100000.0 + i))
        sc.harvest()
        shadow = sc.report()

        outcomes = [{"confidence": c, "win": w} for c, w in recs]
        real = _calibration(_confidence_buckets(outcomes)["buckets"], outcomes)

        self.assertEqual(shadow["shadow_calibration_score"], real["calibration_score"])
        self.assertEqual(shadow["error"], real["error"])

    def test_imports_nothing_that_can_gate_a_trade(self):
        """Structural isolation, asserted against the AST rather than trusted
        from a docstring. If someone later imports kill_switch or confluence
        here, a research module silently gains the ability to affect trading."""
        tree = ast.parse((_BACKEND / "app/services/shadow_calibration.py").read_text())
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imported.append((getattr(node, "module", "") or "")
                                + " " + ",".join(a.name for a in node.names))
        forbidden = ("kill_switch", "confluence", "execution_gate",
                     "decision", "weight_approval")
        for imp in imported:
            for f in forbidden:
                self.assertNotIn(f, imp, f"shadow_calibration must not import {f}")

    def test_thin_sample_returns_none_not_a_fabricated_score(self):
        """A bucket under MIN_PER_BUCKET must yield None + BUILDING. Inventing
        a score off 1-2 samples is exactly the fabrication this repo forbids."""
        for i, (c, w) in enumerate([(65, 1), (75, 0)]):
            audit._history.append(_audit_rec(c, w, 1786200000.0 + i))
        sc.harvest()
        r = sc.report()
        self.assertIsNone(r["shadow_calibration_score"])
        self.assertEqual(r["status"], "BUILDING")

    def test_building_progress_survives_the_outer_note_merge(self):
        """Regression for a real bug: _score()'s BUILDING message was keyed
        "note" and got silently overwritten by report()'s own "note", hiding
        the only field that says how far the sample is from usable."""
        for i, (c, w) in enumerate([(65, 1), (75, 0)]):
            audit._history.append(_audit_rec(c, w, 1786300000.0 + i))
        sc.harvest()
        r = sc.report()
        self.assertIn("60-70:1", r.get("progress", ""))
        self.assertTrue(r.get("note"))          # disclaimer still present too

    def test_harvest_is_idempotent(self):
        """harvest() runs every AI cycle over the same in-memory deque. If it
        were not deduped, every cycle would re-append and inflate the sample."""
        audit._history.append(_audit_rec(65, 1, 1786400000.0))
        self.assertEqual(sc.harvest(), 1)
        self.assertEqual(sc.harvest(), 0)

    def test_records_without_confidence_are_skipped_never_backfilled(self):
        """Pre-deploy audit records carry no signal_confidence. Guessing one
        would manufacture calibration evidence out of nothing."""
        audit._history.append({"hypothetical": True, "win": 1,
                               "ts": 1786500000.0, "action": "WAIT"})
        self.assertEqual(sc.harvest(), 0)


class AuditRegressionTests(unittest.TestCase):
    """audit.py is live infrastructure. The Shadow Calibration work added two
    fields to its records; those must not perturb anything already reading it."""

    def setUp(self):
        audit._history.clear()

    def test_new_fields_do_not_change_report_output(self):
        """Byte-identical apart from report()'s own wall-clock ts."""
        def snapshot(with_new: bool) -> str:
            audit._history.clear()
            for i, (c, w) in enumerate([(65, 1), (75, 0), (85, 1)]):
                audit._history.append(_audit_rec(c, w, 1786100000.0 + i, with_new))
            d = dict(audit.report())
            d.pop("ts", None)                   # wall-clock, differs every call
            return json.dumps(d, sort_keys=True, default=str)

        self.assertEqual(snapshot(False), snapshot(True))


class OrfeResearchTests(unittest.TestCase):
    """ORFE is research-only, but a measurement bug here produces false
    conclusions about a strategy — which is how a bad rule reaches production."""

    @staticmethod
    def _c(day: int, h: int, m: int, op, hi, lo, cl):
        t = datetime.datetime(2026, 6, day, h, m, tzinfo=IST).timestamp()
        return {"time": t, "open": op, "high": hi, "low": lo, "close": cl, "volume": 1000}

    def _base_day(self, day: int):
        """Rising opening range -> CALL bias, breakout to ~118, then a
        retracement deep enough to touch the 0.786 level."""
        cs = []
        for i in range(15):
            p = 100 + i * 0.7
            cs.append(self._c(day, 9, 15 + i, p, p + 0.3, p - 0.3, p + 0.2))
        cs.append(self._c(day, 9, 30, 110.5, 118.0, 110.4, 117.5))
        for i, p in enumerate([115, 112, 109, 107.5]):
            cs.append(self._c(day, 9, 31 + i, p + 1, p + 1.2, p - 0.2, p))
        return cs

    def test_target2_is_reachable_on_a_later_candle(self):
        """THE BUG (fixed 2026-08-08): the loop broke the instant T1 was hit,
        with the T2 check nested in that same branch — so WIN_T2 required one
        1-minute candle to span from below T1 to beyond T2. It reported
        t2_rate=0.0 across all 288 rows and every regime, which was read as
        'the T2 rule is too far' when in fact T2 was never given a chance."""
        cs = self._base_day(1)
        for i, p in enumerate([112, 116, 118.5, 121, 124, 127, 129]):
            cs.append(self._c(1, 9, 35 + i, p - 1, p + 0.5, p - 1.5, p))
        for i in range(40):
            cs.append(self._c(1, 10, i % 60, 129, 129.5, 128.5, 129))

        # _process_day emits a leading kind="setup" denominator row (2026-08-08)
        # alongside the per-level touch rows; outcomes live on the touch rows.
        rows = [r for r in orfe._process_day("2026-06-01", cs)
                if r.get("kind", "touch") == "touch"]
        self.assertTrue(any(r["outcome"] == "WIN_T2" for r in rows),
                        "T2 unreachable when hit on a candle after T1")
        won = next(r for r in rows if r["outcome"] == "WIN_T2")
        self.assertIsNotNone(won["mins_to_t2"])
        self.assertGreater(won["mins_to_t2"], won["mins_to_t1"])

    def test_stop_after_target1_stays_a_win(self):
        """Once T1 is banked, a later stop ends the run at WIN_T1. Scoring it
        LOSS would understate the strategy by erasing a realised target."""
        cs = self._base_day(2)
        for i, p in enumerate([113, 118.5, 115, 110, 105, 99, 95]):
            cs.append(self._c(2, 9, 35 + i, p + 1, p + 0.6, p - 1.0, p))
        for i in range(40):
            cs.append(self._c(2, 10, i % 60, 95, 95.5, 94.5, 95))

        rows = {r["fib_level"]: r for r in orfe._process_day("2026-06-02", cs)
                if r.get("kind", "touch") == "touch"}
        deep = rows[0.786]           # the level touched on the genuine retracement
        self.assertEqual(deep["outcome"], "WIN_T1")
        self.assertIsNotNone(deep["t1_time"])

    def test_untouched_level_produces_no_row(self):
        """A level price never reached is a non-event. Emitting it as a loss
        would invent losing trades that were never taken."""
        cs = self._base_day(3)
        for i in range(40):
            cs.append(self._c(3, 10, i % 60, 117, 117.5, 116.5, 117))
        rows = orfe._process_day("2026-06-03", cs)
        self.assertLess(len(rows), len(orfe.FIB_LEVELS))


class FibDepthEvidenceTests(unittest.TestCase):
    """Retracement-depth layer (owner, 2026-08-08). Its whole purpose is the
    DENOMINATOR: before this, an untouched level emitted no row at all, so
    'how often does a setup retrace to 0.618?' could not be computed —
    the numerator was stored and the denominator discarded."""

    def setUp(self):
        orfe._DATA_DIR = pathlib.Path(tempfile.mkdtemp())

    def _seed(self, depths):
        rows = []
        for i, depth in enumerate(depths):
            rows.append({"kind": "setup", "day": f"2026-06-{i+1:02d}", "bias": "CALL",
                         "regime": "TRENDING", "deepest_frac": depth, "or_range": 10.0})
            for f in orfe.FIB_LEVELS:
                if depth <= f:
                    rows.append({"kind": "touch", "day": f"2026-06-{i+1:02d}",
                                 "bias": "CALL", "regime": "TRENDING", "fib_level": f,
                                 "outcome": "WIN_T1", "mfe_pts": 10.0, "mae_pts": 5.0,
                                 "rejection": f <= 0.618, "deepest_frac": depth})
        orfe._write_rows("TEST", rows)
        return orfe.level_stats("TEST")

    def test_reach_probability_uses_the_setup_denominator(self):
        st = self._seed([0.90, 0.70, 0.55, 0.30])
        by = {l["fib_level"]: l for l in st["levels"]}
        # depths <= f count as having reached level f (smaller frac = deeper)
        self.assertEqual(by[1.0]["reach_pct"], 100.0)     # all four
        self.assertEqual(by[0.786]["reach_pct"], 75.0)    # 0.70/0.55/0.30
        self.assertEqual(by[0.618]["reach_pct"], 50.0)    # 0.55/0.30
        self.assertEqual(by[0.236]["reach_pct"], 0.0)     # none that deep
        self.assertEqual(by[0.786]["of_setups"], 4)

    def test_reach_is_none_not_zero_without_setup_rows(self):
        """Legacy logs have only touch rows. 'not measured' must not render
        as 'never happened' — that would read as a real 0% probability."""
        orfe._write_rows("TEST", [
            {"kind": "touch", "day": "2026-06-01", "bias": "CALL", "regime": "TRENDING",
             "fib_level": 0.618, "outcome": "WIN_T1", "mfe_pts": 9.0, "mae_pts": 3.0}])
        st = orfe.level_stats("TEST")
        by = {l["fib_level"]: l for l in st["levels"]}
        self.assertIsNone(by[0.618]["reach_pct"])
        self.assertEqual(st["setup_rows"], 0)

    def test_legacy_rows_without_kind_still_counted_as_touches(self):
        orfe._write_rows("TEST", [
            {"day": "2026-06-01", "bias": "CALL", "regime": "TRENDING",
             "fib_level": 0.618, "outcome": "WIN_T1", "mfe_pts": 9.0, "mae_pts": 3.0}])
        st = orfe.level_stats("TEST")
        self.assertEqual(st["total_rows"], 1)

    def test_mae_percentiles_reported_beside_the_mean(self):
        """MAE is skewed; an average hides the tail that actually stops you out."""
        st = self._seed([0.30, 0.55, 0.70])
        lvl = next(l for l in st["levels"] if l["fib_level"] == 1.0)
        self.assertIsNotNone(lvl["median_mae_pts"])
        self.assertIsNotNone(lvl["p90_mae_pts"])

    def test_rejection_split_is_reported_separately(self):
        """'Fib touched' vs 'Fib gave a quality entry' must stay distinguishable."""
        st = self._seed([0.30, 0.55])
        deep = next(l for l in st["levels"] if l["fib_level"] == 0.618)
        self.assertGreater(deep["n_with_rejection"], 0)
        shallow = next(l for l in st["levels"] if l["fib_level"] == 1.0)
        self.assertGreater(shallow["n_bare_touch"], 0)

    def test_shallow_and_full_giveback_levels_exist(self):
        self.assertIn(0.236, orfe.FIB_LEVELS)
        self.assertIn(1.0, orfe.FIB_LEVELS)


class BacktestGateTests(unittest.TestCase):
    """The dynamic-zone backtest is BACKTEST_ONLY and must stay unreachable
    as a trading input until the owner's sample bar is met. The reason is
    measured, not theoretical: on this dataset the identical fixed rule
    earned 0.627 mean R on train and 1.178 on test purely because the market
    changed. At n~30 that swamps any strategy difference, so an ungated
    number would let regime noise be read as edge."""

    def test_unlock_bar_is_the_owners_standard(self):
        self.assertEqual(orfe.UNLOCK_MIN_DAYS, 100)
        self.assertEqual(orfe.UNLOCK_MIN_SIGNALS, 500)
        self.assertTrue(orfe.BACKTEST_ONLY,
                        "BACKTEST_ONLY must not be flipped without a human decision")

    def test_backtest_is_not_reachable_from_any_live_decision_module(self):
        """orfe_research must not be imported by confluence/decision/gate code."""
        for mod in ("app/engines/confluence.py", "app/services/decision_contract.py",
                    "app/engines/execution_gate.py", "app/services/kill_switch.py",
                    "app/engines/decision.py"):
            p = _BACKEND / mod
            if p.exists():
                self.assertNotIn("orfe_research", p.read_text(),
                                 f"{mod} must not import the research backtest")

    def test_gate_blocks_and_explains_on_a_thin_sample(self):
        """Requires the candle cache; skipped where it is absent (e.g. CI)."""
        try:
            r = orfe.dynamic_zone_backtest("NIFTY")
        except ValueError:
            self.skipTest("no cached candles in this environment")
        if r.get("error"):
            self.skipTest(r["error"])
        self.assertEqual(r["mode"], "BACKTEST_ONLY")
        # mandatory fields, duplicated at top level so a caller cannot miss them
        self.assertIn("sample_size", r)
        self.assertIn("regime_warning", r)
        g = r["gate"]
        self.assertIn("unlocked_for_decisions", g)
        self.assertIn("regime_warning", g)
        # at the current sample the gate must be shut
        if g["sample_size"]["test_setups"] < orfe.UNLOCK_MIN_SIGNALS and \
           g["sample_size"]["test_days"] < orfe.UNLOCK_MIN_DAYS:
            self.assertFalse(g["unlocked_for_decisions"])
            self.assertEqual(g["status"], "DIRECTIONAL_ONLY")
            self.assertIsNotNone(g["shortfall"])

    def test_fib_level_selector_is_also_gated(self):
        """The Level Selector cross-tabs by level/bias/regime — smaller cells
        than the zone backtest, not larger — so it must be at least as gated."""
        r = orfe.fib_level_selector("TEST_EMPTY_SYMBOL_NO_CACHE")
        self.assertEqual(r["mode"], "BACKTEST_ONLY")
        self.assertFalse(r["gate"]["unlocked_for_decisions"])
        self.assertIn("sample_size", r)
        self.assertIn("regime_warning", r)

    def test_fib_level_selector_reach_matches_level_stats(self):
        """Two different aggregations (level_stats vs fib_level_selector) over
        the SAME persisted rows must agree on reach probability — divergence
        here would mean one of them has a bug, not a market finding."""
        try:
            ls = orfe.level_stats("NIFTY")
            sel = orfe.fib_level_selector("NIFTY")
        except Exception:
            self.skipTest("no persisted NIFTY research rows in this environment")
        if not ls.get("levels") or not sel["overall"]["by_level"]:
            self.skipTest("no rows")
        a = {L["fib_level"]: L["reach_pct"] for L in ls["levels"]}
        b = {L["fib_level"]: L["reach_pct"] for L in sel["overall"]["by_level"]}
        self.assertEqual(a, b)

    def test_fib_level_selector_confirmation_split_never_fabricates_a_cell(self):
        """A confirmation split with zero samples must report n=0 and a None
        mean_R, never a manufactured number."""
        rows = [{"kind": "setup", "day": "2026-06-01", "bias": "CALL",
                "regime": "TRENDING", "deepest_frac": 0.5}]
        orfe._write_rows("TEST_SEL", rows)
        r = orfe.fib_level_selector("TEST_SEL")
        for L in r["overall"]["by_level"]:
            for side in L["by_confirmation"].values():
                if side["n"] == 0:
                    self.assertIsNone(side["mean_R"])

    def test_train_test_split_is_chronological_not_random(self):
        """A random split leaks future regime into training and flatters the
        result — the one methodological error that would invalidate all of it."""
        try:
            r = orfe.dynamic_zone_backtest("NIFTY")
        except ValueError:
            self.skipTest("no cached candles in this environment")
        if r.get("error"):
            self.skipTest(r["error"])
        self.assertIn("chronological", r["split"]["method"])
        self.assertGreater(r["split"]["train_days"], r["split"]["test_days"])


class WilsonIntervalTests(unittest.TestCase):
    """A proportion without its n and interval is a misleading number —
    63.5% on n=9 is not the same claim as 63.5% on n=500."""

    def test_known_values(self):
        w = orfe._wilson(50, 100)
        self.assertEqual(w["pct"], 50.0)
        self.assertAlmostEqual(w["lo"], 40.4, delta=0.5)
        self.assertAlmostEqual(w["hi"], 59.6, delta=0.5)

    def test_interval_narrows_as_n_grows(self):
        """Same point estimate, more data -> tighter interval. If this ever
        stopped holding, the interval would be decorative rather than real."""
        small = orfe._wilson(6, 10)
        large = orfe._wilson(600, 1000)
        self.assertEqual(small["pct"], large["pct"])
        self.assertGreater(small["width"], large["width"] * 5)

    def test_stays_inside_zero_one_at_extremes(self):
        """Why Wilson and not the normal approximation: at p=0 or p=1 the
        normal interval escapes [0,1] and reports impossible probabilities."""
        for w in (orfe._wilson(0, 5), orfe._wilson(5, 5)):
            self.assertGreaterEqual(w["lo"], 0.0)
            self.assertLessEqual(w["hi"], 100.0)

    def test_zero_sample_returns_none_not_zero(self):
        w = orfe._wilson(0, 0)
        self.assertIsNone(w["pct"])
        self.assertEqual(w["n"], 0)


class OverfittingDetectorTests(unittest.TestCase):
    """This exists because TWO false findings in this project were caught only
    by a human re-reading code. A detector that cannot catch those exact
    signatures is decorative."""

    def setUp(self):
        orfe._DATA_DIR = pathlib.Path(tempfile.mkdtemp())

    @staticmethod
    def _rows(spec):
        """spec: list of (day, fib, outcome, R, rejection)"""
        out = [{"kind": "setup", "day": d, "bias": "CALL", "regime": "TRENDING",
                "deepest_frac": 0.3, "day_of_week": "Mon"}
               for d in sorted({s[0] for s in spec})]
        for day, fib, outcome, R, rej in spec:
            out.append({"kind": "touch", "day": day, "fib_level": fib,
                        "outcome": outcome, "r_multiple": R, "rejection": rej,
                        "mae_pts": 10.0, "mfe_pts": 10.0, "bias": "CALL",
                        "regime": "TRENDING"})
        return out

    def test_catches_the_actual_t2_bug_signature(self):
        """MUTATION CHECK against a real historical bug (fixed in 9076e13):
        the T2 loop broke on T1 touch, so t2_rate was 0.0 at EVERY level while
        T1 ranged 15.9%-80.2%. Reproduces that exact shape — T1 spread wide,
        T2 frozen at zero — and asserts the detector catches it."""
        spec = []
        for i in range(1, 21):
            d = f"2026-06-{i:02d}"
            # T1 rate deliberately varies steeply by level, T2 never occurs
            for fib, wr in ((0.236, 0.15), (0.5, 0.45), (1.0, 0.80)):
                win = (i / 20.0) <= wr
                spec.append((d, fib, "WIN_T1" if win else "LOSS",
                             1.0 if win else -1.0, False))
        orfe._write_rows("TEST_W", self._rows(spec))
        codes = [w["code"] for w in orfe.research_warnings("TEST_W")["warnings"]]
        self.assertIn("IDENTICAL_ACROSS_ALL_STRATA", codes)

    def test_uniform_t2_alone_is_not_flagged(self):
        """The refinement that fixed a false positive: if T1 is ALSO flat, a
        uniform T2 is just a sample with no T2 hits — honest, not an artifact.
        Without this the detector would fire on every T2-less dataset."""
        spec = [(f"2026-06-{i:02d}", fib, "WIN_T1", 1.0, False)
                for i in range(1, 16) for fib in (0.382, 0.5, 0.618)]
        orfe._write_rows("TEST_W", self._rows(spec))
        codes = [w["code"] for w in orfe.research_warnings("TEST_W")["warnings"]]
        self.assertNotIn("IDENTICAL_ACROSS_ALL_STRATA", codes)

    def test_catches_rejection_sign_flip(self):
        """The 2026-08-08 finding: rejection helped at some levels and hurt at
        adjacent ones on thin cells. Found by hand then; must be automatic now."""
        spec = []
        for i in range(1, 9):
            d = f"2026-06-{i:02d}"
            spec += [(d, 0.5, "WIN_T1", 2.0, True), (d, 0.5, "LOSS", -1.0, False)]
            spec += [(d, 0.618, "LOSS", -1.0, True), (d, 0.618, "WIN_T1", 2.0, False)]
        orfe._write_rows("TEST_W", self._rows(spec))
        codes = [w["code"] for w in orfe.research_warnings("TEST_W")["warnings"]]
        self.assertIn("REJECTION_DIRECTION_INCONSISTENT", codes)

    def test_catches_single_trade_dominance(self):
        spec = [(f"2026-06-{i:02d}", 0.5, "LOSS", -1.0, False) for i in range(1, 10)]
        spec.append(("2026-06-20", 0.5, "WIN_T2", 60.0, False))
        orfe._write_rows("TEST_W", self._rows(spec))
        codes = [w["code"] for w in orfe.research_warnings("TEST_W")["warnings"]]
        self.assertIn("SINGLE_TRADE_DOMINATES", codes)

    def test_catches_thin_cells_and_the_owner_bar(self):
        spec = [("2026-06-01", 0.5, "WIN_T1", 1.0, False)]
        orfe._write_rows("TEST_W", self._rows(spec))
        codes = [w["code"] for w in orfe.research_warnings("TEST_W")["warnings"]]
        self.assertIn("SAMPLE_CRITICALLY_THIN", codes)
        self.assertIn("BELOW_OWNER_EVIDENCE_BAR", codes)

    def test_clean_data_produces_no_false_alarm(self):
        """A detector that fires on everything is as useless as one that fires
        on nothing. Well-behaved, adequately-sampled, level-varying data must
        not trigger the artifact checks."""
        import random
        random.seed(7)
        spec = []
        for i in range(1, 41):
            d = f"2026-06-{i:02d}"
            for fib, wr in ((0.5, 0.55), (0.618, 0.45), (0.786, 0.35)):
                win = random.random() < wr
                spec.append((d, fib, "WIN_T1" if win else "LOSS",
                             1.0 if win else -1.0, random.random() < 0.5))
        orfe._write_rows("TEST_W", self._rows(spec))
        codes = [w["code"] for w in orfe.research_warnings("TEST_W")["warnings"]]
        for artifact in ("IDENTICAL_ACROSS_ALL_STRATA", "SINGLE_TRADE_DOMINATES",
                         "EXPECTANCY_SIGN_FLIP_OUT_OF_SAMPLE"):
            self.assertNotIn(artifact, codes)


class TransitionMatrixTests(unittest.TestCase):
    def setUp(self):
        orfe._DATA_DIR = pathlib.Path(tempfile.mkdtemp())

    def test_conditional_probability_matches_hand_computation(self):
        """4 setups at known depths: 0.9, 0.7, 0.55, 0.3.
        Reached 0.786 -> those with deepest<=0.786 = 0.7/0.55/0.3 = 3.
        Of those, reached 0.618 -> 0.55/0.3 = 2. So P = 2/3 = 66.7%."""
        rows = [{"kind": "setup", "day": f"2026-06-0{i+1}", "bias": "CALL",
                 "regime": "TRENDING", "deepest_frac": d}
                for i, d in enumerate((0.9, 0.7, 0.55, 0.3))]
        orfe._write_rows("TEST_TM", rows)
        tm = orfe.transition_matrix("TEST_TM")
        step = next(s for s in tm["transitions"] if s["from"] == 0.786)
        self.assertEqual(step["to"], 0.618)
        self.assertEqual(step["p_deeper_given_reached"]["n"], 3)
        self.assertAlmostEqual(step["p_deeper_given_reached"]["pct"], 66.7, delta=0.1)

    def test_every_probability_carries_n_and_interval(self):
        rows = [{"kind": "setup", "day": "2026-06-01", "bias": "CALL",
                 "regime": "TRENDING", "deepest_frac": 0.4}]
        orfe._write_rows("TEST_TM", rows)
        tm = orfe.transition_matrix("TEST_TM")
        for s in tm["transitions"]:
            for key in ("pct", "n", "lo", "hi"):
                self.assertIn(key, s["p_deeper_given_reached"])


class NoLookaheadTests(unittest.TestCase):
    """The single most dangerous class of bug in backtest research: using a
    candle that had not printed yet."""

    def test_touch_indicators_ignore_all_future_candles(self):
        """Same day, but with extra candles appended AFTER the touch. Every
        touch-time field must be byte-identical — if any of them changed, an
        indicator was reading the future."""
        def C(h, m, op, hi, lo, cl):
            t = datetime.datetime(2026, 6, 1, h, m, tzinfo=IST).timestamp()
            return {"time": t, "open": op, "high": hi, "low": lo,
                    "close": cl, "volume": 1000}
        base = []
        for i in range(15):
            p = 100 + i * 0.7
            base.append(C(9, 15 + i, p, p + 0.3, p - 0.3, p + 0.2))
        base.append(C(9, 30, 110.5, 118.0, 110.4, 117.5))
        for i, p in enumerate([115, 112, 109, 107.5]):
            base.append(C(9, 31 + i, p + 1, p + 1.2, p - 0.2, p))
        for i, p in enumerate([112, 116, 118.5, 121, 124, 127, 129]):
            base.append(C(9, 35 + i, p - 1, p + 0.5, p - 1.5, p))
        short = base + [C(10, i % 60, 129, 129.5, 128.5, 129) for i in range(40)]
        # a wildly different future that must not influence touch-time context
        wild = base + [C(10, i % 60, 300, 400.0, 250.0, 350) for i in range(40)]

        def touch_ctx(cs):
            return [{k: r.get(k) for k in ("fib_level", "rsi_touch", "atr_touch",
                                           "supertrend_direction", "vwap_side",
                                           "candle_bias", "entry_time")}
                    for r in orfe._process_day("2026-06-01", cs)
                    if r.get("kind") == "touch"]

        self.assertEqual(touch_ctx(short), touch_ctx(wild))


class EventLoopBlockingTests(unittest.TestCase):
    """THE 2026-08-10 INCIDENT. google-genai's generate_content() is a
    BLOCKING network call with no default deadline. It was being invoked
    directly inside `async def` FastAPI handlers, so a stalled Gemini froze
    the ENTIRE backend — every tick loop, the WebSocket, and /health itself.
    The watchdog read that as "backend unresponsive" and restarted: 20 times
    between 2026-08-03 and 2026-08-10. The live log signature was the SDK
    call starting, then 88-107s of total silence at ~0% CPU.

    Two defences, both asserted here: a hard timeout bounds the stall, and
    to_thread keeps it off the event loop entirely."""

    _ROUTES = _BACKEND / "app/api/routes.py"
    _PROVIDER = _BACKEND / "app/services/cortex/provider.py"
    _MAIN = _BACKEND / "app/main.py"

    def test_gemini_call_has_a_hard_timeout(self):
        src = self._PROVIDER.read_text()
        self.assertIn("GEMINI_TIMEOUT_MS", src)
        self.assertIn("http_options", src,
                      "the generate_content call must pass an http_options timeout")
        import re
        m = re.search(r"GEMINI_TIMEOUT_MS\s*=\s*([0-9_]+)", src)
        self.assertIsNotNone(m)
        self.assertLessEqual(int(m.group(1).replace("_", "")), 120_000,
                             "a timeout longer than ~2min defeats its own purpose")

    def test_the_timeout_api_exists_in_the_installed_sdk(self):
        """Guards against an SDK upgrade silently dropping the kwarg — the
        timeout would then be ignored and the freeze would return."""
        try:
            from google.genai import types
        except ImportError:
            self.skipTest("google-genai not installed in this environment")
        cfg = types.GenerateContentConfig(
            max_output_tokens=64, http_options=types.HttpOptions(timeout=45_000))
        self.assertEqual(cfg.http_options.timeout, 45_000)

    # Blocking AI entry points, in ANY file with an async def that can reach
    # them. "run_cycle" is here specifically because weekend_ai.run_cycle()
    # was the SECOND instance of this bug, found only after the fix to
    # routes.py alone didn't stop the restart loop — it was reached from a
    # background asyncio task in main.py, not an HTTP handler, so scanning
    # only routes.py missed it entirely. Never scope this scan to one file
    # again for that reason.
    _BLOCKING_AI_CALLS = ("analyze", "eod_report", "run_cycle", "ask")

    # THIRD INSTANCE, same incident window: evolution.run_nightly() always
    # persists (persist=True hardcoded), and _persist() makes a synchronous
    # Supabase .execute() call — same bug class as the AI calls above, but
    # blocking DB I/O instead of LLM inference. Reachable from both
    # _nightly_audit_loop (main.py, background task) and the
    # POST /evolution/run-nightly route (routes.py, human-triggered).
    # Kept as a separate tuple since it's not an AI call, but scanned
    # together with _BLOCKING_AI_CALLS below — never scope this to one file.
    _BLOCKING_DB_CALLS = ("run_nightly",)

    def _scan_for_unwrapped_blocking_calls(self, path: pathlib.Path) -> list[str]:
        src = path.read_text()
        tree = ast.parse(src)
        offenders = []
        blocking_names = self._BLOCKING_AI_CALLS + self._BLOCKING_DB_CALLS
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                    if sub.func.attr in blocking_names:
                        seg = ast.get_source_segment(src, node) or ""
                        if "to_thread" not in seg and "run_in_executor" not in seg:
                            offenders.append(f"{path.name}:{node.name} -> {sub.func.attr}")
        return offenders

    def test_no_async_endpoint_calls_a_blocking_ai_path_directly(self):
        """AST-level, across every file with async defs that can reach a
        blocking AI call — not just HTTP routes. A call must be wrapped
        (to_thread/run_in_executor), never invoked bare on the event loop."""
        offenders = (self._scan_for_unwrapped_blocking_calls(self._ROUTES)
                    + self._scan_for_unwrapped_blocking_calls(self._MAIN))
        self.assertEqual(offenders, [],
                         f"blocking AI call on the event loop: {offenders}")

    def test_weekend_ai_background_loop_is_off_the_loop(self):
        """Direct check on the exact function that caused the 2026-08-10
        restart loop: _weekend_ai_loop fires 30s after every boot, so an
        un-wrapped blocking call here self-sustains a crash loop rather than
        just occasionally freezing."""
        src = self._MAIN.read_text()
        i = src.index("async def _weekend_ai_loop")
        body = src[i:i + 1200]
        self.assertIn("to_thread", body,
                      "_weekend_ai_loop must not run weekend_ai.run_cycle bare")

    def test_cortex_endpoints_are_off_the_loop(self):
        src = self._ROUTES.read_text()
        for marker in ("cortex_analyze_ep", "cortex_ask_ep"):
            i = src.index(f"def {marker}")
            body = src[i:i + 1600]
            self.assertIn("to_thread", body,
                          f"{marker} must not run its blocking AI call on the event loop")

    def test_nightly_audit_background_loop_is_off_the_loop(self):
        """THIRD INSTANCE: _nightly_audit_loop runs evolution.run_nightly(),
        which always persists to Supabase synchronously. Direct pinned check
        on the exact function, same reasoning as _weekend_ai_loop above."""
        src = self._MAIN.read_text()
        i = src.index("async def _nightly_audit_loop")
        body = src[i:i + 1600]
        self.assertIn("to_thread", body,
                      "_nightly_audit_loop must not run evolution.run_nightly bare")

    def test_run_nightly_http_route_is_off_the_loop(self):
        """Same evolution.run_nightly() blocking-DB-call bug, second call
        site: the human-triggered POST /evolution/run-nightly route."""
        src = self._ROUTES.read_text()
        i = src.index("def evolution_run_nightly")
        body = src[i:i + 800]
        self.assertIn("to_thread", body,
                      "evolution_run_nightly route must not run run_nightly bare")


class EntryEvidenceBoardTests(unittest.TestCase):
    """The board joins live position to the historical study. Its whole
    value depends on reading mean_R from the RIGHT aggregator — level_stats()
    predates R-multiple math entirely and would silently render every mean_R
    as None (caught by hand before this test existed)."""

    def test_historical_mean_R_is_populated_not_none(self):
        from app.services import entry_evidence as ee
        h = ee._historical("NIFTY")
        if not h.get("available"):
            self.skipTest("no cached NIFTY study in this environment")
        populated = [r for r in h["by_level"] if r.get("n", 0) >= 10]
        self.assertTrue(populated, "no level had enough sample to check")
        self.assertTrue(any(r["mean_R"] is not None for r in populated),
                        "mean_R is None across every level — wrong aggregator wired")

    def test_verdict_preferred_level_is_none(self):
        """The board must pass the study's own conclusion through unchanged,
        never a stronger claim than the study itself makes."""
        from app.services import entry_evidence as ee
        h = ee._historical("NIFTY")
        if not h.get("available"):
            self.skipTest("no cached NIFTY study in this environment")
        self.assertIsNone(h["verdict"]["preferred_level"])

    def test_no_setup_today_is_reported_not_guessed(self):
        from app.services import entry_evidence as ee
        from app.core.state import state
        state.candles = []
        b = ee.board("NIFTY")
        self.assertFalse(b["live"]["available"])
        self.assertIn("reason", b["live"])

    def test_board_never_raises_on_empty_state(self):
        from app.services import entry_evidence as ee
        from app.core.state import state
        state.candles = []
        try:
            ee.board("NIFTY")
        except Exception as e:
            self.fail(f"board() raised on empty state: {e}")


class InvalidationDirectionTests(unittest.TestCase):
    """Bug fix (owner, 2026-08-10): _invalidations() derived bullish/bearish
    from dec["action"], which is only "BUY CALL"/"BUY PUT" once a trade is
    ARMED — during every WAIT cycle it's just "WAIT", so this silently
    defaulted to bearish-side phrasing regardless of the live bias. Confirmed
    live: BULL bias, spot already above VWAP, yet invalidation read "above
    VWAP" (backwards for a bullish setup — that's already true, not a future
    invalidation). Fixed by passing the live sig["direction"] through, same
    signal _ai_dealer() already used correctly for the identical check."""

    def test_bullish_wait_state_invalidates_below_vwap_not_above(self):
        dec = {"action": "WAIT", "stop_loss": None}
        tech = {"vwap": 7654.8}
        inv = decision_contract._invalidations(dec, tech, direction="BULL")
        joined = " | ".join(inv)
        self.assertIn("below VWAP", joined)
        self.assertNotIn("above VWAP", joined)

    def test_bearish_wait_state_invalidates_above_vwap_not_below(self):
        dec = {"action": "WAIT", "stop_loss": None}
        tech = {"vwap": 7654.8}
        inv = decision_contract._invalidations(dec, tech, direction="BEAR")
        joined = " | ".join(inv)
        self.assertIn("above VWAP", joined)
        self.assertNotIn("below VWAP", joined)

    def test_no_direction_falls_back_to_action_not_always_bearish(self):
        """When direction isn't passed at all (defensive default), an armed
        CALL trade must still read as bullish — the pre-fix behavior for the
        one case it did handle right."""
        dec = {"action": "BUY CALL", "stop_loss": None}
        tech = {"vwap": 7654.8}
        inv = decision_contract._invalidations(dec, tech)
        joined = " | ".join(inv)
        self.assertIn("below VWAP", joined)


class IndicatorTests(unittest.TestCase):
    def test_rsi_on_a_flat_series_is_neutral_not_maximum(self):
        """Regression (fixed in a313c9d): a completely flat series has zero
        gains AND zero losses. Returning 100.0 made a dead instrument read as
        the strongest possible uptrend."""
        self.assertEqual(rsi([100.0] * 30), 50.0)

    def test_rsi_all_gains_is_maximum(self):
        self.assertEqual(rsi([100.0 + i for i in range(30)]), 100.0)


class StrategyRouterTests(unittest.TestCase):
    """Read-only aggregator over the four measurement systems. Its danger is
    not crashing — it is grading evidence more leniently than the owner does."""

    def test_grade_bar_matches_the_owners_declared_standard(self):
        """The owner's bar (2026-08-07) is ">=100 trading days OR >=500
        signals". A first draft used 100 samples/20 days and graded ORFE
        (83 days, 288 rows) DECISION_GRADE — telling the owner their own
        hypothesis was proven when by their own rule it was not. Locked here
        so it cannot silently drift looser again."""
        from app.services import strategy_router as sr
        self.assertEqual(sr.MIN_SAMPLE_DECISION_GRADE, 500)
        self.assertEqual(sr.MIN_DAYS_DECISION_GRADE, 100)

        self.assertEqual(sr._grade(288, 83), "DIRECTIONAL")   # ORFE today
        self.assertEqual(sr._grade(500, 1), "DECISION_GRADE")  # signals axis
        self.assertEqual(sr._grade(50, 100), "DECISION_GRADE")  # days axis
        self.assertEqual(sr._grade(10, 2), "BUILDING")
        self.assertEqual(sr._grade(0, 0), "NO_DATA")

    def test_imports_nothing_that_can_gate_a_trade(self):
        tree = ast.parse((_BACKEND / "app/services/strategy_router.py").read_text())
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imported.append((getattr(node, "module", "") or "")
                                + " " + ",".join(a.name for a in node.names))
        for imp in imported:
            for f in ("kill_switch", "confluence", "execution_gate", "weight_approval"):
                self.assertNotIn(f, imp)

    def test_survives_a_broken_source(self):
        """One measurement system failing must not take the aggregator down."""
        from app.services import strategy_router as sr

        def boom():
            raise RuntimeError("source exploded")

        value, err = sr._safe(boom)
        self.assertIsNone(value)
        self.assertIn("RuntimeError", err)

    def test_publishes_no_blended_edge_score(self):
        """Combining detection rate, calibration error, veto value and index
        points into one ranked number would invent a meaningless metric. The
        report must expose per-source units only."""
        from app.services import strategy_router as sr
        r = sr.report()
        for banned in ("overall_edge", "combined_score", "edge_score", "ranking"):
            self.assertNotIn(banned, r)
        self.assertIn("why_no_single_score", r)
        # calibration can never claim to express profit
        cal = next(s for s in r["sources"] if s["id"] == "shadow_calibration")
        self.assertFalse(cal["edge_expressible"])


class ObservationalLayerTests(unittest.TestCase):
    """Layers added as 'observational' must stay out of the scored composite.
    The moment one enters WEIGHTS or MANDATORY it starts moving real trades."""

    def test_observational_layers_are_not_scored_or_mandatory(self):
        for layer in ("candles", "supertrend", "evidence_rank", "structural_targets"):
            self.assertNotIn(layer, confluence.WEIGHTS,
                             f"{layer} must not be in the weighted composite")
            self.assertNotIn(layer, confluence.MANDATORY,
                             f"{layer} must not be a mandatory gate layer")

    def test_weighted_layers_sum_to_one(self):
        self.assertAlmostEqual(sum(confluence.WEIGHTS.values()), 1.0, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
