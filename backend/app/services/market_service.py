"""Market Service — owns every background loop.

Lifecycle contract (the FINAL REQUIREMENT of the spec):
  * Process start  -> NOTHING runs. No API calls, no data, no math.
  * SAVE & CONNECT -> validate() against broker; only on success do the
    loops start:  spot 3s | option-chain + Greeks 15s | AI analysis 180s.
  * New token saved -> stop() tears down the old session and start() brings
    everything back, no process restart.
"""
from __future__ import annotations

import asyncio
import logging
import time

from ..broker.dhan import BrokerError, DhanClient, MarketClosedError
from ..broker.instruments import get_instrument
from ..config import settings
from ..core.state import state, is_market_open
from ..core.text import truncate_at_word
from ..engines import (anomaly, confluence, decision as decision_eng,
                       dom as dom_eng, index_analytics, smart_money)
from ..engines.lifecycle import Lifecycle
from ..services import alerts, journal, market_session_manager, memory, paper, scanner
from ..ws.manager import manager

log = logging.getLogger("market")

LIFECYCLE_ALERT_KINDS = {"ARMED": "ARMED", "TRIGGERED": "ENTRY", "ENTRY": "ENTRY",
                         "TARGET": "TARGET", "EXIT": "SL", "WATCH": "SETUP"}


def _friendly_error(e: Exception) -> dict:
    """Priority 9/12 — translate any broker exception into a calm, user-facing
    status. The raw text is kept only for logs/debug, never shown as the headline."""
    msg = str(e).lower()
    if "subscri" in msg or "data apis" in msg or "data api" in msg:
        kind, text = "SUBSCRIPTION", "Dhan Data API subscription required"
    elif "token" in msg or "401" in msg or "unauthor" in msg:
        kind, text = "AUTH", "Broker authentication failed — update your token in Settings"
    elif "rate limit" in msg or "429" in msg:
        kind, text = "RATE_LIMIT", "Rate limited by broker — pausing briefly, will resume"
    elif "unreachable" in msg or "network" in msg or "timeout" in msg:
        kind, text = "NETWORK", "Network issue — reconnecting…"
    elif "empty data" in msg or "no price" in msg:
        kind, text = "WAITING", "Waiting for live market data…"
    else:
        kind, text = "BROKER", "Broker issue — retrying automatically"
    # RC1.16.10 fix #6 (owner state-precedence spec): Market Closed →
    # quote failures are EXPECTED → never claim a broker fault while the
    # broker is fine and the market is simply shut. "Retrying" implies a
    # failure that does not exist.
    if kind in ("BROKER", "NETWORK", "WAITING") and not is_market_open(state.market_type):
        kind, text = "MARKET_CLOSED", ("Awaiting market open — broker connection "
                                       "healthy, quote polling paused")
    return {"message": text, "kind": kind, "raw": str(e)[:200]}


class MarketService:
    def __init__(self) -> None:
        self.client: DhanClient | None = None
        self._prev_quote: dict = {}
        # V24 — per-symbol option-chain capability (discovered, not assumed);
        # a failed commodity probe is re-tried every 10 minutes
        self._chain_cap: dict = {}
        self._quote_meta: dict = {}   # symbol -> cached OHLC/volume/DOM (30s refresh)
        self.lifecycle = Lifecycle()

    # ---------- lifecycle ----------
    async def connect(self, client_id: str, access_token: str) -> dict:
        """Validate credentials, then start all engines. Raises BrokerError."""
        await self.stop()  # disconnect old session if any
        client = DhanClient(client_id, access_token)
        # Fails ONLY on invalid token / wrong client id / network. Market-closed
        # and missing-data-subscription return success with a status flag.
        vinfo = await client.validate()

        self.client = client
        state.credentials.client_id = client_id
        state.credentials.access_token = access_token
        state.connected = True
        state.connected_at = time.time()
        state.data_quality = "CLOSED" if vinfo.get("market_status") == "CLOSED" else "GOOD"
        await self.start()
        log.info("Connected as %s — engines started (%s)", client_id, vinfo.get("message"))
        return {"connected": True,
                "market_status": vinfo.get("market_status"),
                "data_status": vinfo.get("data_status"),
                "message": vinfo.get("message", "Broker connected successfully.")}

    async def start(self) -> None:
        loops = [
            self._spot_loop(),
            self._option_loop(),
            self._ai_loop(),
            self._scanner_loop(),
            self._status_loop(),
        ]
        state.tasks = [asyncio.create_task(l) for l in loops]
        # background: load the stock universe for search (non-blocking)
        state.tasks.append(asyncio.create_task(self._load_universe()))

    async def _load_universe(self) -> None:
        try:
            n = await self.client.load_scrip_master()
            state.heartbeats["universe"] = time.time()
            # auto-resolve active MCX contracts — commodities just work
            from ..broker.instruments import set_security_override
            resolved = self.client.resolve_commodities()
            for sym, sid in resolved.items():
                set_security_override(sym, sid)
            log.info("Stock universe ready: %d symbols; commodities resolved: %s",
                     n, resolved or "none found")
            if resolved:
                await manager.broadcast("status", state.status())
        except Exception as e:
            log.warning("scrip master load failed: %s", e)

    async def stop(self) -> None:
        for t in state.tasks:
            t.cancel()
        state.tasks = []
        if self.client:
            await self.client.close()
            self.client = None
        state.connected = False
        await manager.broadcast("status", state.status())

    async def set_symbol(self, symbol: str) -> None:
        inst = get_instrument(symbol)
        state.symbol = inst.symbol
        state.market_type = inst.market_type

        # ---- HARD SYMBOL ISOLATION ----
        # Wipe EVERY per-symbol surface so no prior symbol's analysis, triggers,
        # narrator, roadmap or decision can leak into the new one.
        self.lifecycle.reset()
        state.spot = state.option_chain = state.analytics = {}
        state.greeks = state.smart_money = state.signal = state.risk = {}
        state.intelligence = {}      # <- held gamma wall / triggers / narrator / roadmap
        state.decision = {}
        state.candles = []
        self._quote_meta.pop(inst.symbol, None)
        self._prev_quote.pop(inst.symbol, None)
        # reset engine-internal per-symbol caches
        try:
            from ..engines import confluence
            confluence._prev_ctx.pop(inst.symbol, None)
            from ..engines import expiry as _exp
            _exp._prev.pop(inst.symbol, None)
        except Exception:
            pass

        # tell the browser to clear its analysis slices immediately (don't wait
        # for the next push — otherwise stale cards show until the AI cycle)
        await manager.broadcast("reset", {"symbol": inst.symbol})
        await manager.broadcast("status", state.status())
        # Run an immediate AI cycle so the dashboard isn't blank for long
        asyncio.create_task(self._safe(self._ai_cycle))

    # ---------- loops ----------
    async def _spot_loop(self) -> None:
        while True:
            await self._safe(self._spot_tick)
            await asyncio.sleep(settings.spot_interval)

    async def _option_loop(self) -> None:
        await asyncio.sleep(2)   # stagger: offset from the spot loop
        while True:
            await self._safe(self._option_tick)
            await asyncio.sleep(settings.option_interval)

    async def _ai_loop(self) -> None:
        await asyncio.sleep(7)  # let first market data land; stagger
        while True:
            await self._safe(self._ai_cycle)
            await asyncio.sleep(settings.ai_interval)

    async def _scanner_loop(self) -> None:
        await asyncio.sleep(20)
        while True:
            from ..broker.dhan import DhanClient
            try:
                # lowest-priority loop: skip while cooling OR market closed
                if (self.client and not DhanClient.stats()["cooldown_active"]
                        and is_market_open(state.market_type)):
                    await scanner.scan(self.client, state.watchlist, state.market_type)
                    state.heartbeats["scanner"] = time.time()
                    await manager.broadcast("scanner", scanner.results)
                    # V26 — Level-2 deep scan on the strongest L1 candidates
                    from . import opportunity
                    await opportunity.build_board(self.client, scanner.results)
                # Global context feed (cache-gated 180s; runs even off-hours —
                # US futures trade nearly 24h; context-only per doctrine)
                from . import global_feed
                await global_feed.refresh()
                # Weekly/Monthly pivots (S/R Phase 2, owner 2026-07-23) —
                # cache-gated 6h, one broker call per refresh; safe even
                # off-hours (uses only already-closed daily candles)
                if self.client:
                    from . import period_pivot_cache
                    inst = get_instrument(state.symbol)
                    await period_pivot_cache.refresh(self.client, inst)
                    # Owner Step 10 (MTF Confluence, 2026-07-27) — 4H candles,
                    # cache-gated 20min (mtf_4h_cache.py). Same low-frequency
                    # discipline as the pivot cache above; a 4H bar only
                    # closes 6x/day so per-cycle refetching would be waste
                    # that competes with the shared broker rate budget.
                    from . import mtf_4h_cache
                    await mtf_4h_cache.refresh(self.client, inst)
                    # Bug fix, V7.0 observation phase (2026-07-27) — 1H
                    # candles, cache-gated 10min (mtf_1h_cache.py). 1H was
                    # originally resampled from state.candles (capped at 600
                    # 1-min bars = 10h), which can never produce the 30
                    # complete 1H bars mtf_confluence.py requires — confirmed
                    # live, 1H silently never reached "ready". Same
                    # low-frequency real-fetch pattern as the 4H cache above.
                    from . import mtf_1h_cache
                    await mtf_1h_cache.refresh(self.client, inst)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("scanner pass failed: %s", e)
            await asyncio.sleep(120)   # 2 min — scanner is non-urgent

    async def _status_loop(self) -> None:
        """RC1.15 — Source-of-Truth fix: state.status() (market_open,
        market_status, countdown) was previously broadcast only on connect/
        disconnect/symbol-switch. A tab left open across the 9:15 open/15:30
        close transition never received a fresh copy — 'Live analysis
        resumes automatically... no refresh needed' was a false promise.
        Zero broker calls (pure local computation) — safe at a short interval,
        runs regardless of market hours so the transition itself self-heals."""
        while True:
            await asyncio.sleep(20)
            try:
                await self._auto_switch_market()
                await manager.broadcast("status", state.status())
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("status broadcast failed")

    async def _auto_switch_market(self) -> None:
        """V7 Market Independence Phase A (owner, 2026-07-23; LTS freeze
        exception — foundational, not a feature add). Zero broker calls (same
        contract as this loop's other work) — resolve_active_market_type() is
        pure local time math, same as is_market_open().

        Root cause this closes: state.market_type only ever changed on an
        explicit set_symbol() call, so nothing ever asked "is a DIFFERENT
        market open right now?" — the platform sat idle at NSE close even
        while MCX was live. Currency intentionally excluded from the cascade
        (Dhan CDS access unverified, owner 2026-07-23 — parked, not silently
        dropped; see market_session_manager.market_overview()).

        Never overrides a manual pin (auto_market_switch=False), and never
        fabricates a switch target when every registered market is closed —
        that stays an honest WAIT, same as today."""
        if not state.auto_market_switch or not self.client:
            return
        active = market_session_manager.resolve_active_market_type()
        if active is None or active == state.market_type:
            return
        candidates = market_session_manager.candidates_for(active)
        if not candidates:
            return
        # prefer the last scanner pass's top-ranked candidate for the target
        # market (the same ranking already trusted for INDEX); else the
        # registry's first entry as an honest, declared fallback — never an
        # invented "best commodity to trade" preference.
        ranked = [r["symbol"] for r in scanner.results if r.get("market_type") == active]
        best = ranked[0] if ranked else candidates[0]
        log.info("Market Independence: %s closed, %s open — switching %s -> %s",
                 state.market_type, active, state.symbol, best)
        await self.set_symbol(best)

    async def _safe(self, fn) -> None:
        try:
            await fn()
            state.data_quality = "GOOD"
        except MarketClosedError as e:
            # normal idle state — not a data fault; don't trip POOR/kill switch
            state.data_quality = "CLOSED"
            log.info("market closed: %s", e)
        except BrokerError as e:
            state.data_quality = "POOR"
            log.warning("broker error: %s", e)
            await manager.broadcast("error", _friendly_error(e))
        except asyncio.CancelledError:
            raise
        except Exception:
            state.data_quality = "DEGRADED"
            log.exception("engine tick failed")

    # ---------- ticks ----------
    async def _spot_tick(self) -> None:
        """Fast 3s loop: lightweight LTP only. The heavy full quote (OHLC,
        volume, DOM) is refreshed at most every 30s to respect Dhan's ~1/sec
        data limit — this is the change that stops the 429 storms."""
        if not self.client:
            return
        inst = get_instrument(state.symbol)
        if inst.security_id == 0:
            return  # contract not resolved yet (scrip master still loading)

        # Phase 4/12 — market closed: pause feed (no broker calls), calm WAIT state.
        if not is_market_open(inst.market_type):
            state.data_quality = "CLOSED"
            return

        ltp = await self.client.get_ltp(inst)            # cheap; 1 call
        if ltp <= 0:
            return

        meta = self._quote_meta.get(inst.symbol, {})
        now = time.time()
        if now - meta.get("ts", 0) > 30:                 # periodic heavy refresh
            try:
                q = await self.client.get_quote(inst)
                ohlc = q.get("ohlc") or {}
                meta = {
                    "high": float(ohlc.get("high") or 0),
                    "low": float(ohlc.get("low") or 0),
                    "ref": float(ohlc.get("close") or ohlc.get("open") or 0),
                    "volume": float(q.get("volume") or 0),
                    "dom": dom_eng.analyze(q.get("depth"), ltp),
                    "ts": now,
                }
                self._quote_meta[inst.symbol] = meta
            except BrokerError:
                pass                                     # keep last meta; LTP still flows

        prev = state.spot.get("ltp", ltp)
        ref = meta.get("ref") or state.spot.get("day_open", ltp)
        state.spot = {
            "symbol": inst.symbol,
            "ltp": ltp,
            "change": round(ltp - ref, 2),
            "change_pct": round((ltp / ref - 1) * 100, 2) if ref else 0.0,
            "high": meta.get("high", 0.0),
            "low": meta.get("low", 0.0),
            "volume": meta.get("volume", 0.0),
            "tick_dir": "up" if ltp > prev else "down" if ltp < prev else "flat",
            "day_open": state.spot.get("day_open", ltp),
            "dom": meta.get("dom", {"available": False}),
            "ts": now,
        }
        state.heartbeats["spot"] = time.time()
        paper.mark_to_market({inst.symbol: ltp})
        memory.update_outcomes(inst.symbol, ltp)

        # Phase 3 audit forward-tracking — uses the existing tick (no new data)
        try:
            from ..services import audit
            audit.on_tick(ltp)
        except Exception:
            pass

        # lifecycle is price-driven between AI cycles
        if self.lifecycle.on_tick(ltp):
            snap = self.lifecycle.snapshot()
            await manager.broadcast("lifecycle", snap)
            kind = LIFECYCLE_ALERT_KINDS.get(snap["state"])
            if kind:
                last = snap["history"][-1] if snap["history"] else {}
                await alerts.send(kind, f"{inst.symbol} — {snap['state']}",
                                  last.get("note", ""), inst.symbol)
        await manager.broadcast("spot", state.spot)

    async def _option_tick(self) -> None:
        if not self.client:
            return
        inst = get_instrument(state.symbol)
        if inst.security_id == 0:
            return
        if not is_market_open(inst.market_type):     # Phase 4 — pause when closed
            return

        # V24 Universal Strike Engine — try the option-chain pipeline for ANY
        # instrument (index or MCX commodity). Capability comes from the broker
        # response, never assumed from market type. Chain-less contracts (or
        # missing MCX option subscription) fall back to the quote pipeline and
        # the honest N/A path; a failed commodity probe re-tries every 10 min.
        use_chain = False
        cap = self._chain_cap.get(inst.symbol)
        probe = inst.market_type == "INDEX" or cap is None or cap.get("ok") \
            or time.time() - cap.get("ts", 0) > 600
        if probe:
            try:
                expiries = await self.client.get_expiries(inst)
                if expiries:
                    chain = await self.client.get_option_chain(inst, expiries[0])
                    spot = float(chain.get("last_price") or state.spot.get("ltp") or 0)
                    analytics = index_analytics.analyze_chain(
                        chain, spot, expiries[0], inst.strike_step)
                    # V40 universal sanity — a parity-violating chain never
                    # enters the pipeline for ANY instrument (index/stock/MCX);
                    # we keep the last good snapshot and log loudly instead
                    if analytics.get("chain") and not index_analytics.chain_sane(analytics, spot):
                        log.warning("chain sanity FAILED for %s (expiry %s) — snapshot rejected",
                                    inst.symbol, expiries[0])
                        analytics = {}
                    if analytics.get("chain"):
                        state.analytics = analytics
                        state.greeks = analytics.get("greeks", {})
                        state.option_chain = {"chain": analytics.get("chain", []),
                                              "atm": analytics.get("atm_strike")}
                        flow = smart_money.analyze_option_flow(analytics)
                        use_chain = True
                        # RC1.16.2 — score stored premium projections against
                        # the live chain whenever spot reaches a projected
                        # level (measurement only, zero extra broker calls)
                        try:
                            from . import premium_accuracy
                            premium_accuracy.check(inst.symbol, spot,
                                                   analytics.get("chain"))
                        except Exception:
                            log.exception("premium accuracy check failed")
                            try:
                                from . import premium_accuracy
                                premium_accuracy.note_error()
                            except Exception:
                                pass
                        # MODE Phase A — opportunity-layer move detection on
                        # the watched strikes (alert-only; gate untouched)
                        try:
                            from . import move_detector
                            await move_detector.scan(
                                inst.symbol, spot, analytics.get("chain"),
                                (state.decision or {}).get("strike_queue"))
                        except Exception:
                            log.exception("move detector failed")
                        # Premium Radar — always-on ATM±N premium tracking for the
                        # buyer (read-only; wider coverage than MODE's queue).
                        try:
                            from . import premium_radar
                            premium_radar.scan(inst.symbol, spot, analytics.get("chain"))
                        except Exception:
                            log.exception("premium radar failed")
            except MarketClosedError:
                raise
            except Exception as e:
                if inst.market_type == "INDEX":
                    raise           # index chain failures keep old semantics (retry next tick)
                log.info("no option chain for %s (%s) — quote mode", inst.symbol, e)
            if inst.market_type != "INDEX":
                self._chain_cap[inst.symbol] = {"ok": use_chain, "ts": time.time()}
        if inst.market_type == "INDEX" and not use_chain:
            return
        if not use_chain:
            q = await self.client.get_quote(inst)
            ltp = float(q.get("last_price") or 0)
            oi = float(q.get("oi") or 0)
            prev = self._prev_quote.get(inst.symbol, {"ltp": ltp, "oi": oi})
            p_chg = (ltp / prev["ltp"] - 1) * 100 if prev["ltp"] else 0.0
            oi_chg = (oi / prev["oi"] - 1) * 100 if prev["oi"] else 0.0
            self._prev_quote[inst.symbol] = {"ltp": ltp, "oi": oi}
            state.analytics = {
                "oi": oi, "volume": q.get("volume", 0),
                "underlying_flow": smart_money.classify_underlying(p_chg, oi_chg),
            }
            flow = {"activities": [state.analytics["underlying_flow"]],
                    "bias": "NEUTRAL", "score": 0,
                    "underlying": state.analytics["underlying_flow"]}

        state.smart_money = flow
        state.heartbeats["options"] = time.time()
        state.heartbeats["greeks"] = time.time()
        memory.record_snapshot(inst.symbol, float(state.spot.get("ltp") or 0), state.analytics)

        # anomaly detection: unusual OI / volume / IV / sudden moves
        for a in anomaly.observe(inst.symbol, float(state.spot.get("ltp") or 0), state.analytics):
            await alerts.send("SYSTEM", f"{inst.symbol} anomaly: {a['kind'].replace('_', ' ').title()}",
                              a["message"], inst.symbol)
            await manager.broadcast("anomaly", a)
        await manager.broadcast("analytics", {
            "analytics": {k: v for k, v in state.analytics.items() if k != "chain"},
            "greeks": state.greeks,
            "smart_money": state.smart_money,
            "option_chain": state.option_chain,
        })

    async def _ai_cycle(self) -> None:
        """Cloud AI Trader X cycle: 1m candles -> 10-layer confluence engine."""
        if not self.client:
            return
        inst = get_instrument(state.symbol)
        if not is_market_open(inst.market_type):     # Phase 4 — pause AI when closed
            return
        candles_1m = await self.client.get_intraday_candles(inst, interval="1", lookback_days=4)
        if len(candles_1m) < 60:
            return
        state.candles = candles_1m[-600:]

        spot = float(state.spot.get("ltp") or candles_1m[-1]["close"])
        # regime-aware learning: judge this cycle by how the *current* regime
        # has historically performed (falls back to overall accuracy)
        prev_regime = (state.intelligence.get("layers", {})
                       .get("regime", {}).get("regime", ""))
        # validated data quality (Module 13) feeds the safety gate directly
        from . import data_quality, scanner
        from ..engines import market_context
        dq = data_quality.report()["overall"]

        # V11 institutional context — levels from candles we already have (no
        # extra calls); India VIX is one cheap LTP on this 3-min loop.
        levels = market_context.institutional_levels(state.candles)
        try:
            vix = await self.client.get_india_vix()
            if vix:
                market_context.set_vix(vix)
        except BrokerError:
            pass

        # Global-feed Layer-4 (owner-ordered): score yesterday's Next-Session
        # bias against today's actual gap, once day_open is known. No extra calls.
        if levels.get("day_open") and levels.get("prev_day_close"):
            try:
                from . import global_feed
                global_feed.score_overnight_prediction(levels["day_open"], levels["prev_day_close"])
            except Exception:
                log.exception("overnight prediction scoring failed")

        # Phase 14 — Kill Switch (capital protection): evaluate before deciding
        from . import kill_switch as ks_eng, analytics as _an
        from ..broker.dhan import DhanClient
        from ..engines import mtf as _mtf, technicals as _tech
        _c5 = _mtf.resample(state.candles, 5)
        atr_pct = (_tech.atr(_c5) / spot * 100) if (spot and _c5) else 0.0
        _dq_full = data_quality.report()
        _cal = (_an.performance().get("calibration") or {}).get("calibration_score")
        ks = ks_eng.evaluate(dq, atr_pct,
                             float((state.intelligence.get("layers", {}).get("regime", {}) or {}).get("score") or 50),
                             memory._outcomes, DhanClient.stats().get("cooldown_active", False),
                             calibration_score=_cal,
                             data_completeness=_dq_full.get("completeness"),
                             market_closed=not is_market_open(inst.market_type))
        state.kill_switch = ks

        packet = confluence.run(
            spot, inst.market_type, state.candles,
            state.analytics, state.smart_money or {}, dq,
            symbol=inst.symbol,
            historical_accuracy=memory.historical_accuracy(prev_regime),
            levels=levels, breadth=scanner.breadth(), kill_switch=ks,
        )

        # Calibration Watch (owner, 2026-07-23, item #4) — observational only,
        # no calibration/kill-switch logic touched. Same extraction memory.
        # track_signal already uses below, just also recorded for the daily
        # WATCH trigger (calibration_watch.py).
        try:
            from . import calibration_watch as _cal_watch
            _sig_conf = float(packet["signal"].get("dynamic_confidence")
                               or packet["signal"].get("confidence") or 0) or None
            _cal_watch.record(_cal, _sig_conf)
        except Exception:
            pass

        # lifecycle context update + outcome tracking for historical accuracy
        prev_state = self.lifecycle.state
        self.lifecycle.on_analysis(packet, packet["layers"]["structure"], spot)
        if self.lifecycle.state != prev_state and self.lifecycle.state in LIFECYCLE_ALERT_KINDS:
            snap = self.lifecycle.snapshot()
            last = snap["history"][-1] if snap["history"] else {}
            await alerts.send(LIFECYCLE_ALERT_KINDS[self.lifecycle.state],
                              f"{inst.symbol} — {self.lifecycle.state}",
                              last.get("note", ""), inst.symbol)
        _matrix = (packet["layers"].get("intelligence", {}) or {}).get("decision_matrix", {})
        _pass = [r["layer"] for r in _matrix.get("rows", []) if r.get("verdict") == "PASS"]
        # Phase 20 — capture the DNA feature snapshot + strike/premium at signal
        # time so future setups can be matched against this one.
        from ..engines import market_dna
        _vixv = market_context.get_vix().get("value")
        _dna_snap = market_dna.snapshot(packet["layers"], state.analytics, atr_pct, _vixv)
        _strk = packet.get("strike") or {}
        _ptargets = _strk.get("premium_targets") or []
        _ptgt = (_ptargets[0] if isinstance(_ptargets, list) and _ptargets else None)
        memory.track_signal(inst.symbol, packet["signal"],
                            regime=packet["layers"]["regime"]["regime"],
                            session=packet["layers"].get("session", {}).get("session", ""),
                            engines_pass=_pass, dna=_dna_snap,
                            strike=_strk.get("strike"),
                            premium_entry=_strk.get("premium_entry"),
                            premium_target=_ptgt)
        # live DNA match — what has historically happened in setups like this one
        try:
            state.market_dna = market_dna.analyze(_dna_snap, list(memory._outcomes))
        except Exception:
            log.exception("market dna failed")

        # V11 phase-change / future-path / risk alerts (deduped vs last cycle)
        prev_layers = state.intelligence.get("layers", {})
        new_phases = set(packet["layers"]["regime"].get("phases", []))
        old_phases = set(prev_layers.get("regime", {}).get("phases", []))
        emerged = new_phases - old_phases
        if emerged:
            await alerts.send("SETUP", f"{inst.symbol} — phase change",
                              ", ".join(p.replace("_", " ").title() for p in emerged), inst.symbol)
        # RC1.16.10 display-truth fix #1: this is the INTERNAL India-context
        # engine (VIX/GIFT/regime — engines/global_context.py), NOT the
        # external Global Market Context feed (services/global_feed.py).
        # The old wording "Global context turned RISKY" collided with the
        # 🌐 GLOBAL CONTEXT card and misattributed the cause.
        gc_now = packet["layers"].get("global_context", {}).get("condition")
        if gc_now == "RISKY" and prev_layers.get("global_context", {}).get("condition") != "RISKY":
            await alerts.send("SL", f"{inst.symbol} — risk elevated",
                              "India risk context turned RISKY (VIX/regime) — protect capital",
                              inst.symbol)

        # V10 decision synthesis: collapse everything into the 3-second view
        lc_snap = self.lifecycle.snapshot()
        decision = decision_eng.build(packet, lc_snap, spot)

        # Phase 28 — Probability Ladder (derivation-only): P(reach T1/T2/T3) + P(SL)
        try:
            from ..engines import probability_ladder
            _sig = packet["signal"]
            _prob = packet["layers"].get("probability", {}) or {}
            decision["probability_ladder"] = probability_ladder.compute(
                _sig.get("entry"), _sig.get("stop_loss"),
                [_sig.get("target1"), _sig.get("target2"), _sig.get("target3")],
                _sig.get("direction", ""),
                float(_prob.get("expected_move") or 0),
                float(_prob.get("prob_success") or 50))
        except Exception:
            log.exception("probability ladder failed")

        # Phase 27 / 26 / Confidence Explainer (all derivation-only, additive)
        try:
            from ..engines import entry_zone, premium_forecast, confidence_explainer
            decision["entry_zone"] = entry_zone.classify(packet["layers"], packet["signal"], spot)
            decision["premium_forecast"] = premium_forecast.forecast(
                packet["layers"], packet.get("strike") or {}, spot)
            decision["confidence_breakdown"] = confidence_explainer.explain(
                packet["layers"], packet["signal"])
        except Exception:
            log.exception("entry-zone / premium-forecast / explainer failed")

        # Phase 29 Simulator + Phase 30 Options Professor (derivation-only)
        try:
            from ..engines import simulator, options_professor
            _vixv = market_context.get_vix().get("value")
            state.simulator = simulator.simulate(packet["layers"], spot, _vixv)
            decision["options_professor"] = options_professor.explain(
                packet["layers"], packet["signal"], decision, packet.get("strike") or {})
        except Exception:
            log.exception("simulator / options professor failed")

        # Phase 1/5/13 — Decision Intelligence: one institutional decision +
        # trade-quality score + governance, synthesised from existing engines.
        try:
            from ..engines import decision_intelligence
            decision["intelligence_synthesis"] = decision_intelligence.synthesize(
                packet["layers"], packet["signal"], decision, state.market_dna)
        except Exception:
            log.exception("decision intelligence failed")

        # Phase 7 + 6 — Signal Maturity + Entry Trigger (derivation-only).
        try:
            from ..engines import signal_maturity
            import datetime as _dt, zoneinfo as _zi
            _now_ist = _dt.datetime.now(_zi.ZoneInfo("Asia/Kolkata"))
            _dte = (packet["layers"].get("expiry") or {}).get("days_to_expiry")
            # monthly expiry ≈ last Thursday of the month at 0 DTE
            _is_monthly = (_dte == 0 and _now_ist.weekday() == 3
                           and (_now_ist + _dt.timedelta(days=7)).month != _now_ist.month)
            decision["signal_maturity"] = signal_maturity.evaluate(
                inst.symbol, packet["layers"], packet["signal"], decision,
                tf="normal", monthly_expiry=_is_monthly)
        except Exception:
            log.exception("signal maturity failed")

        # Phase D — Safe Mode (infrastructure disaster recovery). Evaluated HERE,
        # BEFORE the checklist/gate consume it — fixes the stale-reasons bug where
        # WHY-NO-TRADE showed last cycle's safe-mode triggers.
        try:
            from . import safe_mode as sm
            sig_age = (time.time() - state.heartbeats["signal_engine"]) if "signal_engine" in state.heartbeats else None
            smst = sm.evaluate(state.connected, dq, DhanClient.stats(),
                               len(manager.clients), sig_age)
            state.safe_mode = smst
            if smst.get("active") and decision.get("is_trade"):
                decision["is_trade"] = False
                decision["primary_action"] = "FORCE WAIT"
                decision["action"] = "WAIT"
                decision["reason"] = "SAFE MODE: " + "; ".join(smst["triggers"])
                decision["safe_mode_override"] = True
        except Exception:
            log.exception("safe mode eval failed")

        # V1.0 P10 — Smart Alerts: transition-only triggers (no spam). Fires a
        # notification the moment the entry window OPENS/EXPIRES, the kill switch
        # activates, or feed quality collapses — so windows aren't missed.
        try:
            _sm2 = decision.get("signal_maturity") or {}
            _st = (_sm2.get("entry_trigger") or {}).get("status")
            _prev_st = getattr(self, "_prev_trigger_status", None)
            if _st in ("READY", "FIRE NOW") and _prev_st not in ("READY", "FIRE NOW"):
                await alerts.send("ENTRY", f"{inst.symbol} — ENTRY WINDOW OPEN ({_st})",
                                  f"Maturity {_sm2.get('maturity_score')}/100 — act within the window",
                                  inst.symbol)
            elif _st == "ENTRY CLOSED" and _prev_st in ("READY", "FIRE NOW"):
                await alerts.send("SETUP", f"{inst.symbol} — entry window EXPIRED",
                                  "Window closed without entry", inst.symbol)
            self._prev_trigger_status = _st

            _ks_active = bool(ks.get("active"))
            if _ks_active and not getattr(self, "_prev_ks_active", False):
                await alerts.send("SL", f"{inst.symbol} — KILL SWITCH ACTIVATED",
                                  truncate_at_word("; ".join(ks.get("reasons", [])), 140), inst.symbol)
            self._prev_ks_active = _ks_active

            if dq == "POOR" and getattr(self, "_prev_dq_alert", "") != "POOR":
                await alerts.send("SL", "Feed quality degraded to POOR",
                                  "Check Feed Diagnostics — WAITs may be data-driven, not market-driven",
                                  inst.symbol)
            self._prev_dq_alert = dq
        except Exception:
            log.exception("smart alerts failed")

        # Phase 2/3/8 — Live Entry Checklist + Fire Score + WHY-NOT (derivation).
        try:
            from ..engines import entry_checklist
            decision["entry_checklist"] = entry_checklist.build(
                packet["layers"], packet["signal"], decision, ks, state.safe_mode)
        except Exception:
            log.exception("entry checklist failed")

        # Layer 6 — Probability Candle Projection (forward-only, no repaint).
        try:
            from ..engines import candle_projection
            decision["candle_projection"] = candle_projection.project(spot, packet["layers"])
        except Exception:
            log.exception("candle projection failed")

        # AI Market Path Predictor — fuse existing engines into one "where next?"
        try:
            from ..engines import market_path
            decision["market_path"] = market_path.predict(packet["layers"], spot, levels)
        except Exception:
            log.exception("market path failed")

        # Module 9 — AI Confidence Evolution (derivation-only time series).
        try:
            from ..engines import confidence_evolution
            decision["confidence_evolution"] = confidence_evolution.update(
                inst.symbol, packet["signal"], packet["layers"])
        except Exception:
            log.exception("confidence evolution failed")

        # V26 §1 — Entry Score Timeline (fire score over time → approaching/fading).
        try:
            from ..engines import entry_score_timeline
            decision["entry_score_timeline"] = entry_score_timeline.update(inst.symbol, decision)
        except Exception:
            log.exception("entry score timeline failed")

        # Section 24 — Final Execution Gate (authoritative gated verdict; advisory,
        # does NOT mutate the decision pipeline). Runs after all inputs are ready.
        try:
            from ..engines import execution_gate
            decision["execution_gate"] = execution_gate.evaluate(
                packet["layers"], packet["signal"], decision, dq, ks,
                state.safe_mode, state.market_dna)
            # RC1.16.6 — Incident #001 explainability: each active blocker
            # carries its own ledger track record (research display only)
            from . import verdicts as _vd
            decision["execution_gate"]["blocker_research"] = _vd.blocker_research(
                decision["execution_gate"].get("blocking_reasons"))
        except Exception:
            log.exception("execution gate failed")

        # V8 Step 8 — Gamma Shield (advisory; trader dislikes gamma-spike trades)
        try:
            from ..engines import gamma_shield
            decision["gamma_shield"] = gamma_shield.evaluate(packet["layers"], spot)
        except Exception:
            log.exception("gamma shield failed")

        # Missed Winner Engine — evidence layer: log winners the gate gave up.
        try:
            from . import missed_winner
            _eg = decision.get("execution_gate") or {}
            _mp = decision.get("market_path") or {}
            missed_winner.track(spot, bool(decision.get("is_trade")),
                                _mp.get("bias", ""), _eg.get("blocking_reasons") or [])
            decision["missed_winner"] = missed_winner.summary()
        except Exception:
            log.exception("missed winner failed")

        # V40.1 — Decision Verdict Engine: blocked cycles open shadow trades at
        # the preparing plan's own SL/T1 → CAPITAL_SAVED / MISSED_WINNER /
        # NEUTRAL, attributed per blocking module (evidence, never thresholds)
        try:
            from . import verdicts
            verdicts.observe(decision, packet["signal"], spot,
                             regime=(packet["layers"].get("regime") or {}).get("regime") or "")
            # RC1.3 audit — broadcast only the slim summary every cycle; the
            # full efficiency tables live at GET /api/verdicts (payload diet)
            _vr = verdicts.report()
            decision["gate_efficiency"] = {
                "settled": _vr["settled"], "open_shadows": _vr["open_shadows"],
                "modules_measured": sum(1 for r in _vr["gate_efficiency"] if r["status"] == "MEASURED"),
            }
        except Exception:
            log.exception("verdict engine failed")

        # V24.5 — One-Click Execution Card + Opportunity Radar (Golden Rule).
        try:
            from ..engines import execution_card
            decision["execution_card"] = execution_card.build(
                packet["layers"], packet["signal"], decision, packet.get("strike") or {}, spot)
        except Exception:
            log.exception("execution card failed")

        # V20 — ONE AI Master Score: plain average of the five core scores the
        # platform already computes (consolidation for display, no new model;
        # the individual scores remain available in Research)
        try:
            _di = decision.get("intelligence_synthesis") or {}
            _parts = [
                float(_di.get("conviction") or 0),
                float((decision.get("entry_checklist") or {}).get("fire_score") or 0),
                float((decision.get("signal_maturity") or {}).get("maturity_score") or 0),
                float((_di.get("trade_quality") or {}).get("score") or 0) / 10.0,
                float((packet["layers"].get("probability") or {}).get("prob_success") or 0),
            ]
            _avail = [p for p in _parts if p > 0]
            if _avail:
                _ms = round(sum(_avail) / len(_avail))
                decision["master_score"] = {
                    "score": _ms, "stars": max(1, min(5, round(_ms / 20))),
                    "note": "Average of conviction, fire, maturity, quality, probability.",
                }
        except Exception:
            log.exception("master score failed")

        # V20-P1 — Meta orchestration headline (the gate IS the meta layer;
        # this surfaces its ONE verdict + ONE dominant reason) + AI Trust
        # (system reliability now — distinct from setup strength; historical
        # accuracy joins the mix once the database has settled trades)
        try:
            _eg = decision.get("execution_gate") or {}
            _blocks = _eg.get("blocking_reasons") or []
            _headline = None
            if _blocks:
                _order = ("kill switch", "safe mode", "data quality", "capital", "risk",
                          "no trade zone", "trap", "liquidity", "order flow", "mandatory",
                          "calibration")
                _low = [b.lower() for b in _blocks]
                for _key in _order:
                    _hit = next((b for b, l in zip(_blocks, _low) if _key in l), None)
                    if _hit:
                        _headline = _hit
                        break
                _headline = _headline or _blocks[0]
            decision["meta"] = {"verdict": _eg.get("final_decision") or "WAIT",
                                "headline": _headline}

            _dqs = {"GOOD": 95.0, "DEGRADED": 60.0, "CLOSED": 50.0,
                    "UNKNOWN": 50.0, "POOR": 20.0}.get(state.data_quality, 50.0)
            _tq = (decision.get("intelligence_synthesis") or {}).get("trade_quality") or {}
            _agree = float(_tq.get("engine_agreement_pct") or 50.0)
            _cal = (packet["signal"].get("calibration") or {})
            _checks = [v for v in _cal.values() if isinstance(v, dict) and "pass" in v]
            _cal_pct = (sum(1 for v in _checks if v["pass"]) / len(_checks) * 100) if _checks else 50.0
            decision["ai_trust"] = {
                "score": round(0.4 * _dqs + 0.3 * _agree + 0.3 * _cal_pct),
                "components": {"data_quality": round(_dqs), "engine_agreement": round(_agree),
                               "calibration": round(_cal_pct)},
                "note": "Feed/data 40% + engine agreement 30% + calibration 30%. "
                        "Historical accuracy joins after validated trades.",
            }
        except Exception:
            log.exception("meta/trust failed")

        # Phase A — Strike Queue (READY / WATCH / PREPARING, ranked by score)
        try:
            _strikes = sorted(packet.get("strikes") or [],
                              key=lambda s: s.get("selection_score", 0), reverse=True)[:5]
            _buy_ok = (decision.get("signal_maturity") or {}).get("buy_allowed")
            _q = []
            for i, s in enumerate(_strikes):
                sc = float(s.get("selection_score") or 0)
                # moneyness tag (ATM within half a strike step)
                _stk, _typ = float(s.get("strike") or 0), s.get("type")
                if spot and _stk and abs(_stk - spot) <= (inst.strike_step or 50) / 2:
                    _money = "ATM"
                elif (_typ == "CE" and _stk < spot) or (_typ == "PE" and _stk > spot):
                    _money = "ITM"
                else:
                    _money = "OTM"
                _q.append({
                    "strike": s.get("strike"), "type": s.get("type"),
                    "premium": s.get("premium_entry"), "score": round(sc, 0),
                    "stars": 5 if sc >= 80 else 4 if sc >= 65 else 3 if sc >= 50 else 2,
                    "prob_itm": s.get("prob_itm_pct"),
                    "moneyness": _money,
                    "spread_pct": s.get("spread_pct"),
                    # V13 — premium plan (already computed by the strike selector)
                    "premium_sl": s.get("premium_stop_loss"),
                    "premium_t1": s.get("premium_target1"),
                    "premium_t2": s.get("premium_target2"),
                    "premium_t3": s.get("premium_target3"),
                    "status": ("READY" if i == 0 and _buy_ok else "WATCH" if i <= 1 else "PREPARING"),
                })
            decision["strike_queue"] = _q
        except Exception:
            log.exception("strike queue failed")

        # V32 Layer-6 — Market Personality: which historical day does today
        # resemble? Zero broker calls (features cached from the learning run;
        # today's shape from candles already in memory). Absent until the
        # historical learning run has been executed — never guessed.
        try:
            from . import historical_learning as _hlmem
            _ref = _hlmem._last_ref.get(state.symbol)
            if _ref and _ref.get("prev_close") and _ref.get("atr"):
                import datetime as _dt4
                _tod = _dt4.date.today()
                _today_c = [c for c in state.candles
                            if c.get("time", 0) > 10_000
                            and _dt4.date.fromtimestamp(c["time"]) == _tod]
                if len(_today_c) >= 5:
                    _o = _today_c[0]["open"]
                    _h = max(c["high"] for c in _today_c)
                    _l = min(c["low"] for c in _today_c)
                    _last = _today_c[-1]["close"]
                    _pc, _atr = _ref["prev_close"], _ref["atr"]
                    _feats_prev = _hlmem._day_features.get(state.symbol) or []
                    mm = _hlmem.similar_days(
                        state.symbol,
                        gap=(_o / _pc - 1) * 100, day_ret=(_last / _pc - 1) * 100,
                        range_atr=(_h - _l) / _atr if _atr else 1.0,
                        prev_ret=_feats_prev[-1]["day_ret"] if _feats_prev else 0.0)
                    if mm:
                        decision["market_memory"] = mm
        except Exception:
            log.exception("market memory failed")

        # V13 — AI Index Selector (momentum radar; ONE batch quote call/min)
        try:
            from ..engines import index_radar
            _rad = await index_radar.build(self.client, state.symbol)
            if _rad:
                decision["index_radar"] = _rad
        except Exception:
            log.exception("index radar failed")

        # V12 §10 — AI Position Sizing (decision-support only; never places orders).
        # Reuses portfolio_risk.position_size on the selected strike's premium
        # entry/SL with the user's capital + risk % from Settings — no new math.
        try:
            from ..config import settings as _cfg
            from ..engines import portfolio_risk
            _st = packet.get("strike") or {}
            # RC1.16.2 — record this cycle's projections for live accuracy
            # scoring (ordering check + entry-reproduce error + level touches)
            try:
                from . import premium_accuracy
                premium_accuracy.observe(inst.symbol, _st, spot)
            except Exception:
                log.exception("premium accuracy observe failed")
                try:
                    from . import premium_accuracy
                    premium_accuracy.note_error()
                except Exception:
                    pass
            _pe, _psl = _st.get("premium_entry"), _st.get("premium_stop_loss")
            # V17 — sized whenever a strike plan exists (live OR preparing),
            # so the trader knows the quantity before the setup fires
            if _pe and _psl and float(_pe) > float(_psl):
                # RC1.4 defense-in-depth: an out-of-bounds capital is GARBAGE,
                # not a big account — fall back to the default and say so
                # (clamping ₹1e12 to ₹100cr would silently pretend wealth)
                _cap_raw = float(_cfg.capital or 0)
                _cap_ok = 10_000 <= _cap_raw <= 1_000_000_000
                _cap_safe = _cap_raw if _cap_ok else 1_000_000.0
                ps = portfolio_risk.position_size(
                    _cap_safe, _cfg.risk_per_trade_pct, float(_pe), float(_psl), inst.lot_size)
                if not _cap_ok:
                    ps["capital_invalid_reset"] = True
                ps.update({
                    "ready": True, "capital": _cap_safe,
                    "risk_pct": _cfg.risk_per_trade_pct, "lot_size": inst.lot_size,
                    "per_lot_risk": round(abs(float(_pe) - float(_psl)) * inst.lot_size, 2),
                    "capital_required": round(float(_pe) * (ps.get("qty") or 0), 2),
                    "preparing": not bool(decision.get("is_trade")),
                })
                # V18 — expected P/L at T1 (premium plan × sized qty; scenario, not promise)
                _t1 = _st.get("premium_target1")
                if _t1 and ps.get("qty"):
                    ps["expected_profit_t1"] = round((float(_t1) - float(_pe)) * ps["qty"], 2)
                decision["position_sizing"] = ps
            else:
                decision["position_sizing"] = {
                    "ready": True, "qty": 0, "lot_size": inst.lot_size,
                    "note": "Sizing appears with a BUY signal — capital & risk % come from Settings.",
                }
        except Exception:
            log.exception("position sizing failed")

        # V30 — today's risk budget (display-only facts from paper trades;
        # hard limits stay with the kill switch, never invented here)
        try:
            import datetime as _dt
            _today = _dt.date.today().isoformat()
            from ..config import settings as _cfg2
            _cap2_raw = float(_cfg2.capital or 0)
            _cap2 = _cap2_raw if 10_000 <= _cap2_raw <= 1_000_000_000 else 1_000_000.0
            _max_notional = _cap2 * 10
            _all = paper.list_trades()
            # RC1.2 — implausible legacy rows (notional > 10× capital) are
            # excluded from the Today line and counted as data-suspect
            _sane = [t for t in _all
                     if float(t.get("qty") or 0) * float(t.get("entry") or 0) <= _max_notional]
            _suspect = len(_all) - len(_sane)
            _closed = [t for t in _sane
                       if t.get("status") == "CLOSED" and (t.get("closed_at") or "").startswith(_today)]
            _openn = [t for t in _sane if t.get("status") == "OPEN"]
            _pnl = sum(t.get("pnl") or 0 for t in _closed)
            decision["risk_budget"] = {
                "trades_today": len(_closed) + len(_openn),
                "realized_pnl": round(_pnl, 2),
                "realized_pct": round(_pnl / _cap2 * 100, 2),
                "excluded_suspect": _suspect,
            }
        except Exception:
            log.exception("risk budget failed")

        # V28 §6 — AI Market Clock (session-phase awareness)
        try:
            from ..engines import market_clock
            decision["market_clock"] = market_clock.now_phase(inst.market_type)
        except Exception:
            log.exception("market clock failed")

        # V29 — Alpha Detection (score + queue + timing + confidence distribution)
        try:
            from ..engines import alpha_engine
            decision["alpha"] = alpha_engine.build(
                packet["layers"], packet["signal"], decision, state.market_dna)
        except Exception:
            log.exception("alpha engine failed")

        # Exit Intelligence (derivation-only; active when a trade is live)
        try:
            from ..engines import exit_intelligence
            state.exit_intel = exit_intelligence.analyze(packet["layers"], lc_snap, packet["signal"], spot, state.candles)
        except Exception:
            log.exception("exit intelligence failed")

        # Owner Step 10 (MTF Confluence, 2026-07-27) — real per-timeframe
        # analysis, additive only (see mtf_confluence.py's own docstring for
        # why this never touches the existing mtf.py/calibration gate).
        # 1m/3m/5m/15m are resampled from the already-fetched state.candles
        # (zero new broker calls); Daily/1H/4H reuse their own low-frequency
        # caches (period_pivot_cache.py, mtf_1h_cache.py, mtf_4h_cache.py —
        # also zero new calls per cycle, refreshed on their own slow
        # schedule above). 1H switched from resample to its own cache
        # 2026-07-27 (bug fix — see mtf_1h_cache.py's docstring).
        try:
            from ..engines import mtf_confluence
            from . import period_pivot_cache, mtf_1h_cache, mtf_4h_cache
            _daily = period_pivot_cache.get(state.symbol).get("daily_candles") or []
            _h1 = mtf_1h_cache.get(state.symbol)
            _h4 = mtf_4h_cache.get(state.symbol)
            decision["mtf_confluence"] = mtf_confluence.analyze(
                state.candles, _h1, _h4, _daily, packet["signal"].get("direction"))
        except Exception:
            log.exception("mtf confluence failed")

        # Phase 3 audit: record this decision for forward-tracked validation
        try:
            from . import audit
            audit.record_decision(
                decision, packet["layers"].get("intelligence", {}), packet["signal"], spot,
                float((packet["signal"].get("tech") or {}).get("atr") or 0),
                packet["layers"].get("global_context", {}).get("bias", "NEUTRAL"),
                packet["layers"]["regime"]["regime"],
                packet["layers"].get("session", {}).get("session", ""))
        except Exception:
            log.exception("audit record failed")  # never affects main flow

        state.intelligence = {**packet, "lifecycle": lc_snap, "decision": decision}
        state.signal = {**packet["signal"], "symbol": inst.symbol, "ts": packet["ts"]}
        state.decision = decision
        state.risk = packet["risk"]
        state.heartbeats["signal_engine"] = time.time()
        try:
            from . import ai_timeline
            ai_timeline.scan()   # AI Journal — record transitions (read-only, additive)
        except Exception:
            pass
        journal.log_signal(inst.symbol, inst.market_type, packet["signal"])
        await manager.broadcast("signal", {
            "signal": state.signal,
            "risk": packet["risk"],
            "layers": packet["layers"],
            "strike": packet["strike"],
            "strikes": packet.get("strikes", []),
            "warning": packet["warning"],
            "narrative": packet["narrative"],
            "coach": packet.get("coach", []),
            "decision": decision,
            "exit_intel": state.exit_intel,
            "lifecycle": lc_snap,
            "kill_switch": ks,
            "market_dna": state.market_dna,
            "safe_mode": state.safe_mode,
        })

    def health(self) -> dict:
        now = time.time()
        age = lambda k: round(now - state.heartbeats[k], 1) if k in state.heartbeats else None
        fresh = lambda k, lim: ("OK" if (state.heartbeats.get(k) and now - state.heartbeats[k] < lim)
                                else "STALE" if state.heartbeats.get(k) else "IDLE")
        from ..api.routes import _candle_cache
        from ..broker.dhan import DhanClient

        return {
            "broker": "CONNECTED" if state.connected else "DISCONNECTED",
            "broker_stability": DhanClient.stats(),
            "cache": {"candle_entries": len(_candle_cache)},
            "memory_samples": len(memory._ring),
            "learning_samples": len(memory._outcomes),
            "websocket_clients": len(manager.clients),
            "token": ("VALID" if state.connected else "NOT SET" if not state.credentials.present else "UNVERIFIED"),
            "data_quality": state.data_quality,
            "data_delay_sec": age("spot"),
            "database": self._db_status(),
            "engines": {
                "spot_feed": {"status": fresh("spot", 12), "last_run_sec": age("spot")},
                "option_chain": {"status": fresh("options", 45), "last_run_sec": age("options")},
                "greeks": {"status": fresh("greeks", 45), "last_run_sec": age("greeks")},
                "signal_engine": {"status": fresh("signal_engine", 420), "last_run_sec": age("signal_engine")},
                "scanner": {"status": fresh("scanner", 150), "last_run_sec": age("scanner")},
                "stock_universe": {"status": "OK" if "universe" in state.heartbeats else "IDLE",
                                   "last_run_sec": age("universe")},
            },
        }

    @staticmethod
    def _db_status() -> str:
        from .journal import _sb
        return "SUPABASE" if _sb else "IN-MEMORY"


service = MarketService()
