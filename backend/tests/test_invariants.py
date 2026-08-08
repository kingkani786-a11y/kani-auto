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
