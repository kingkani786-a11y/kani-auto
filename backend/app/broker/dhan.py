"""DhanHQ v2 REST integration layer.

Auth model matches the product requirement exactly: only Client ID +
Access Token (which Dhan rotates daily). No API secret, no OTP, no
refresh token. All methods raise BrokerError with a readable message so
the UI can surface what went wrong.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import time
from typing import Any

import httpx

from ..broker.instruments import Instrument

log = logging.getLogger("broker.dhan")
BASE = "https://api.dhan.co/v2"


class BrokerError(Exception):
    pass


class MarketClosedError(BrokerError):
    """No live price because the market is closed — a normal WAIT, not a fault."""


def _envelope_reason(data: Any) -> str | None:
    """Extract the broker's own status/message from a price-less 200 response."""
    if not isinstance(data, dict):
        return None
    for k in ("remarks", "message", "error", "errorMessage", "error_message",
              "reason", "status", "code"):
        v = data.get(k)
        if isinstance(v, dict):
            v = v.get("message") or v.get("error") or v.get("remarks") or str(v)
        if v and str(v).strip().lower() not in ("success", "ok", "200"):
            return f"{k}={v}"
    return None


def _data_is_empty(data: Any) -> bool:
    """True if the response carries no instrument data block."""
    if not isinstance(data, dict):
        return True
    d = data.get("data")
    return d is None or (isinstance(d, (dict, list)) and len(d) == 0)


# ---- Universal Dhan response parser (Phase 4) -------------------------------
# Dhan's marketfeed responses vary by API version / segment (string vs numeric
# segment keys, alternate price fields). Rather than assume one exact shape, we
# locate the value by recursively searching for any of the known field names.
# Never assumes a single format; degrades to None instead of raising.
PARSER_VERSION = "2.1-universal"
_PRICE_KEYS = ("last_price", "ltp", "LTP", "last_traded_price", "lastTradedPrice",
               "lastPrice", "ltt", "close", "price", "last", "value",
               "marketPrice", "market_price", "tradePrice", "trade_price",
               "currentPrice", "current_price")

# Task 7 — auto-learned JSON paths: once a price is located for an endpoint,
# remember the path and try it first next time. {endpoint: [path keys]}
_learned_paths: dict[str, list] = {}


def _find_value_path(obj: Any, keys: tuple[str, ...], _depth: int = 0,
                     _path: tuple = ()) -> tuple[Any, tuple]:
    """Depth-first search returning (value, path) for the first matching key
    (case-insensitive). Handles dict / list / nested / numeric-or-string keys."""
    if _depth > 8 or obj is None:
        return None, ()
    if isinstance(obj, dict):
        low = {str(k).lower(): k for k in obj}
        for want in keys:
            if want.lower() in low:
                k = low[want.lower()]
                val = obj[k]
                if isinstance(val, (int, float, str)):
                    return val, _path + (k,)
        for k, v in obj.items():
            found, p = _find_value_path(v, keys, _depth + 1, _path + (k,))
            if found is not None:
                return found, p
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            found, p = _find_value_path(v, keys, _depth + 1, _path + (i,))
            if found is not None:
                return found, p
    return None, ()


def _find_value(obj: Any, keys: tuple[str, ...]) -> Any:
    """Back-compat: value only."""
    return _find_value_path(obj, keys)[0]


def _value_at_path(obj: Any, path: list) -> Any:
    """Resolve a previously-learned path; None if it no longer exists."""
    cur = obj
    try:
        for step in path:
            cur = cur[step]
        return cur
    except (KeyError, IndexError, TypeError):
        return None


def _coerce_float(v: Any) -> float | None:
    try:
        f = float(v)
        return f if f == f else None      # reject NaN
    except (TypeError, ValueError):
        return None


def locate_ltp(data: Any, segment: str = "", security_id: Any = None
               ) -> tuple[float | None, str, str]:
    """Universal LTP extraction returning (value, matched_field, matched_path).
    Tries documented path → numeric-segment variant → full recursive search.
    Returns (None, '', '') when no usable price exists."""
    sid = str(security_id)
    # 1) documented v2 path
    try:
        v = data["data"][segment][sid]["last_price"]
        f = _coerce_float(v)
        if f is not None:
            return f, "last_price", f"data.{segment}.{sid}.last_price"
    except (KeyError, TypeError, IndexError):
        pass
    # 2) numeric-segment-key variant (the '13' bug class)
    try:
        for seg_key, seg_val in (data.get("data") or {}).items():
            if isinstance(seg_val, dict) and sid in seg_val:
                val, p = _find_value_path(seg_val[sid], _PRICE_KEYS)
                f = _coerce_float(val)
                if f is not None:
                    return f, (p[-1] if p else ""), "data." + str(seg_key) + "." + sid + "." + ".".join(map(str, p))
    except (AttributeError, TypeError):
        pass
    # 3) full recursive fallback — find any price field anywhere
    val, p = _find_value_path(data, _PRICE_KEYS)
    f = _coerce_float(val)
    if f is not None:
        return f, (p[-1] if p else ""), ".".join(map(str, p))
    return None, "", ""


def parse_ltp(data: Any, segment: str = "", security_id: Any = None) -> float | None:
    """Back-compat wrapper — value only."""
    return locate_ltp(data, segment, security_id)[0]


class RateLimitError(BrokerError):
    """Broker returned 429 — all data calls pause for a cooldown window."""


class DhanClient:
    # Global pacing: Dhan data APIs throttle hard. Every request from any
    # part of the app (spot, chain, scanner, charts) flows through one gate.
    # Dhan data endpoints (quote/ltp) are ~1 req/sec — keep the floor at ~1.1s.
    _BASE_GAP = 1.1          # baseline seconds between any two broker requests
    _gap = 1.1              # dynamic: widens after 429s, decays on success
    _last_req = 0.0          # class-level: shared across reconnects
    _cooldown_until = 0.0    # set on 429; all calls short-circuit until then
    _cooldown_step = 30.0    # smart cooldown: escalates on repeated 429s
    # Request analytics (Module 1/14): rolling request timestamps + latency
    _req_times: "deque[float]" = None  # type: ignore[assignment]
    _latencies: "deque[float]" = None  # type: ignore[assignment]
    _total_requests = 0
    _total_429 = 0                      # LIFETIME, display only (rate_limit_events)
    _429_times = None                   # sliding 1h window for SCORING (lazy-init)
    BUDGET_PER_MIN = 45      # self-imposed budget (well under Dhan data limits)

    @classmethod
    def _init_stats(cls) -> None:
        from collections import deque as _dq
        if cls._req_times is None:
            cls._req_times = _dq(maxlen=600)
            cls._latencies = _dq(maxlen=200)
        if cls._429_times is None:
            # cap 500: the penalty saturates at 8 events, so 500 is ample headroom
            cls._429_times = _dq(maxlen=500)

    @classmethod
    def stats(cls) -> dict:
        """Broker Stability Layer telemetry for the health dashboard."""
        cls._init_stats()
        now = time.monotonic()
        last_min = [t for t in cls._req_times if now - t < 60]
        rate = len(last_min)
        utilization = round(rate / cls.BUDGET_PER_MIN * 100, 1)
        avg_lat = round(sum(cls._latencies) / len(cls._latencies) * 1000, 0) if cls._latencies else None
        cooling = now < cls._cooldown_until
        score = 100.0
        # Sliding 1h window (owner-approved 2026-07-21). This was
        # `min(cls._total_429 * 5, 40)` over a MONOTONIC lifetime counter that
        # never reset or decayed: after 8 rate-limit hits EVER, a permanent -40,
        # so one transient cooldown (-30) put the score under Safe Mode's 40
        # threshold and froze trading. The gate drifted tighter purely with
        # uptime, not with real risk.
        # Copies the sibling idiom four lines above (`_req_times`, 60s), NOT the
        # Kill Switch's fixed daily boundary — a fixed reset would reintroduce
        # the same defect as a midnight cliff. `_total_429` stays untouched for
        # the lifetime display figure: display history != live health.
        _recent_429 = [t for t in cls._429_times if now - t < 3600]
        score -= min(len(_recent_429) * 5, 40)
        score -= max(utilization - 80, 0) * 1.5       # running hot hurts
        if cooling:
            score -= 30
        if avg_lat and avg_lat > 800:
            score -= 10
        return {
            "health_score": round(max(score, 0), 0),
            "requests_per_min": rate,
            "budget_per_min": cls.BUDGET_PER_MIN,
            "utilization_pct": utilization,
            "avg_latency_ms": avg_lat,
            "total_requests": cls._total_requests,
            "rate_limit_events": cls._total_429,
            "cooldown_active": cooling,
            "cooldown_remaining_sec": round(max(cls._cooldown_until - now, 0), 0),
            "current_gap_ms": round(cls._gap * 1000, 0),
        }

    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self._gate = asyncio.Lock()
        self._http = httpx.AsyncClient(
            base_url=BASE,
            timeout=10.0,
            headers={
                "access-token": access_token,
                "client-id": client_id,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kw) -> Any:
        DhanClient._init_stats()
        now = time.monotonic()
        if now < DhanClient._cooldown_until:
            wait = int(DhanClient._cooldown_until - now) + 1
            raise RateLimitError(
                f"Broker rate-limit cooldown — data resumes in ~{wait}s.")
        async with self._gate:                       # space out ALL broker calls
            # dynamic throttle: stay inside the self-imposed per-minute budget
            recent = [t for t in DhanClient._req_times if time.monotonic() - t < 60]
            if len(recent) >= DhanClient.BUDGET_PER_MIN:
                await asyncio.sleep(2.0)             # budget exhausted — back off
            gap = time.monotonic() - DhanClient._last_req
            if gap < DhanClient._gap:
                await asyncio.sleep(DhanClient._gap - gap)
            DhanClient._last_req = time.monotonic()
            started = time.monotonic()
            try:
                r = await self._http.request(method, path, **kw)
            except httpx.HTTPError as e:
                raise BrokerError(f"Broker unreachable: {e}") from e
            DhanClient._req_times.append(started)
            DhanClient._latencies.append(time.monotonic() - started)
            DhanClient._total_requests += 1
        if r.status_code == 429:
            DhanClient._total_429 += 1                       # lifetime (display)
            DhanClient._init_stats()
            DhanClient._429_times.append(time.monotonic())    # sliding (scoring)
            # smart cooldown: each consecutive 429 doubles the pause (cap 5m)
            DhanClient._cooldown_until = time.monotonic() + DhanClient._cooldown_step
            pause = int(DhanClient._cooldown_step)
            DhanClient._cooldown_step = min(DhanClient._cooldown_step * 2, 300.0)
            # dynamic throttling: permanently widen the gap a little
            DhanClient._gap = min(DhanClient._gap * 1.4, 1.5)
            log.warning("429 from broker — cooldown %ss, gap now %.0fms",
                        pause, DhanClient._gap * 1000)
            raise RateLimitError(
                f"Broker rate limit hit (429). Pausing all data requests for {pause}s "
                "to protect your account from being blocked.")
        # healthy response: decay the gap and the cooldown escalation slowly
        DhanClient._gap = max(DhanClient._gap * 0.995, DhanClient._BASE_GAP)
        DhanClient._cooldown_step = max(DhanClient._cooldown_step * 0.99, 30.0)
        if r.status_code == 401:
            try:
                j = r.json()
                detail = j.get("errorMessage") or j.get("error_message") or str(j)
            except Exception:
                detail = r.text[:200]
            if path.startswith(("/marketfeed", "/optionchain", "/charts")):
                # Trading-scope tokens pass /fundlimit but data endpoints 401
                # when the account has no active Data APIs subscription.
                raise BrokerError(
                    "Market data refused (401). Your token authenticated, but Dhan "
                    "rejected the data endpoints — this usually means the 'Data APIs' "
                    "subscription is not active on your account. Enable it at "
                    "web.dhan.co → My Profile → DhanHQ Trading APIs → Data APIs, then "
                    f"generate a fresh token. Broker said: {detail}"
                )
            raise BrokerError(
                f"Invalid or expired Access Token. Update it in Settings. Broker said: {detail}"
            )
        if r.status_code >= 400:
            raise BrokerError(f"Broker API error {r.status_code}: {r.text[:300]}")
        return r.json()

    # ---------- auth ----------
    async def validate(self) -> dict:
        """Proves the token works for BOTH scopes the app needs: trading
        (fundlimit) and market data (ltp probe) — so a missing Data APIs
        subscription surfaces at SAVE & CONNECT, not as a cryptic banner."""
        from .instruments import INSTRUMENTS

        # 1) Token / auth / reachability — the ONLY hard requirement. A trading-
        #    scope token passes /fundlimit even without a Data-APIs subscription,
        #    so this cleanly separates "bad token / network" from "no data feed".
        #    Raises BrokerError on invalid token / wrong client id / unreachable.
        data = await self._request("GET", "/fundlimit")

        result = {"valid": True, "detail": data, "broker_status": "CONNECTED",
                  "market_status": "OPEN", "data_status": "OK",
                  "message": "Broker connected successfully."}
        # 2) Data-scope probe — INFORMATIONAL only; it must never fail the connect.
        try:
            await self.get_ltp(INSTRUMENTS["NIFTY"])
        except MarketClosedError:
            result.update(market_status="CLOSED",
                          message="Broker connected. Market is currently closed.")
        except RateLimitError:
            result.update(data_status="RATE_LIMITED",
                          message="Broker connected. Briefly rate-limited; will resume.")
        except BrokerError as e:
            msg = str(e).lower()
            if any(w in msg for w in ("subscri", "data api", "401", "refused", "unauthor")):
                result.update(data_status="SUBSCRIPTION_REQUIRED",
                              message="Broker connected. Dhan Data API subscription required for live data.")
            else:
                result.update(data_status="UNVERIFIED",
                              message="Broker connected. Live data not yet verified.")
        return result

    # ---------- market data ----------
    async def get_ltp(self, inst: Instrument) -> float:
        payload = {inst.segment: [inst.security_id]}
        # Step 2 — log the exact request context once per call (debug).
        log.debug("LTP request symbol=%s market=%s segment=%s security_id=%s url=%s payload=%s",
                  inst.symbol, inst.market_type, inst.segment, inst.security_id,
                  "/marketfeed/ltp", payload)
        last_data: Any = None
        for attempt in (1, 2):                                   # Step/Task — retry once
            t0 = time.monotonic()
            data = await self._request("POST", "/marketfeed/ltp", json=payload)
            last_data = data
            elapsed = (time.monotonic() - t0) * 1000
            val, field, path = locate_ltp(data, inst.segment, inst.security_id)
            if val is not None and val > 0:
                _learned_paths["/marketfeed/ltp"] = path.split(".")
                log.debug("LTP ok field=%s path=%s value=%s elapsed=%.0fms attempt=%d",
                          field, path, val, elapsed, attempt)
                return val
            # Step 3 — full untruncated raw + each envelope field
            log.warning("LTP no-price [parser %s] symbol=%s seg=%s id=%s attempt=%d "
                        "elapsed=%.0fms envelope_reason=%s data_empty=%s RAW=%s",
                        PARSER_VERSION, inst.symbol, inst.segment, inst.security_id, attempt,
                        elapsed, _envelope_reason(data), _data_is_empty(data), repr(data))

        # Step 4/5/9/10 — surface the ACTUAL reason instead of a generic message.
        from ..core.state import is_market_open
        reason = _envelope_reason(last_data)
        # Market-closed FIRST: when shut, Dhan often returns a data block with
        # last_price 0/stale (so it's not "empty") — that is NOT a fault.
        if not is_market_open(inst.market_type):
            raise MarketClosedError("Market Closed - Live price unavailable.")
        # A broker message that signals a subscription problem → explicit guidance
        if reason and any(w in reason.lower() for w in ("subscri", "not authorized",
                                                        "unauthor", "forbidden", "access")):
            raise BrokerError("Dhan Data API subscription required.")
        if reason:
            raise BrokerError(f"Broker returned no price ({reason}).")
        if _data_is_empty(last_data):
            raise BrokerError(
                f"Empty data for {inst.symbol} (id {inst.security_id}, seg {inst.segment}) — "
                "likely Dhan Data API subscription inactive or invalid security id.")
        raise BrokerError(f"No price field in broker response for {inst.symbol}.")

    @staticmethod
    def _quote_node(data: Any, segment: str, security_id: Any) -> dict | None:
        """Locate the instrument's quote block across response-shape variants."""
        try:
            node = data["data"][segment][str(security_id)]
            if isinstance(node, dict):
                return node
        except (KeyError, TypeError, IndexError):
            pass
        seg_block = (data.get("data") or {}) if isinstance(data, dict) else {}
        for seg_val in (seg_block.values() if isinstance(seg_block, dict) else []):
            if isinstance(seg_val, dict) and isinstance(seg_val.get(str(security_id)), dict):
                return seg_val[str(security_id)]
        return None

    async def get_quote(self, inst: Instrument) -> dict:
        """Full quote: ltp, volume, OI, ohlc — used for commodities."""
        payload = {inst.segment: [inst.security_id]}
        for attempt in (1, 2):                                   # Task 6 — retry once
            data = await self._request("POST", "/marketfeed/quote", json=payload)
            node = self._quote_node(data, inst.segment, inst.security_id)
            if isinstance(node, dict) and node:
                return node
            # Task 1 — full untruncated raw response
            log.warning("Quote no-data [parser %s] endpoint=/marketfeed/quote request=%s "
                        "attempt=%d RAW=%s", PARSER_VERSION, payload, attempt, repr(data))
        raise BrokerError("Broker response contains no quote.")

    _expiry_cache: dict[int, tuple[float, list]] = {}  # security_id -> (ts, expiries)

    async def get_expiries(self, inst: Instrument) -> list[str]:
        """Cached 6h — the expiry list barely changes intraday and this was
        doubling the option-chain request load."""
        hit = DhanClient._expiry_cache.get(inst.security_id)
        if hit and time.monotonic() - hit[0] < 6 * 3600:
            return hit[1]
        data = await self._request(
            "POST",
            "/optionchain/expirylist",
            json={"UnderlyingScrip": inst.security_id, "UnderlyingSeg": inst.segment},
        )
        expiries = sorted(data.get("data", []))   # ISO dates — nearest first, guaranteed
        if expiries:
            DhanClient._expiry_cache[inst.security_id] = (time.monotonic(), expiries)
        return expiries

    async def get_option_chain(self, inst: Instrument, expiry: str) -> dict:
        """Returns {last_price, oc: {strike: {ce: {...}, pe: {...}}}}."""
        data = await self._request(
            "POST",
            "/optionchain",
            json={
                "UnderlyingScrip": inst.security_id,
                "UnderlyingSeg": inst.segment,
                "Expiry": expiry,
            },
        )
        return data.get("data", {})

    # ---------- stock universe (scrip master) ----------
    _scrips: list[dict] | None = None  # class-level cache, survives reconnects
    _commodity_futs: dict[str, list[tuple[datetime.date, int]]] = {}
    _vix_id: int | None = None          # India VIX index security id (V11)

    async def load_scrip_master(self) -> int:
        """Download + cache the Dhan instrument master (NSE/BSE equities).
        Lets the user search ANY listed stock — covers NIFTY 500 and BSE."""
        if DhanClient._scrips is not None:
            return len(DhanClient._scrips)
        import csv as _csv
        import io
        try:
            r = await self._http.get(
                "https://images.dhan.co/api-data/api-scrip-master-detailed.csv",
                timeout=60.0,
            )
            if r.status_code != 200:
                r = await self._http.get(
                    "https://images.dhan.co/api-data/api-scrip-master.csv", timeout=60.0
                )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise BrokerError(f"Could not download instrument master: {e}") from e

        rows = _csv.DictReader(io.StringIO(r.text))
        # column names differ between master variants — resolve fuzzily
        def col(row: dict, *names: str) -> str:
            for n in names:
                if n in row and row[n]:
                    return row[n]
            return ""

        scrips: list[dict] = []
        commodity_futs: dict[str, list[tuple[datetime.date, int]]] = {}
        wanted_commodities = ("GOLD", "SILVER", "CRUDEOIL", "NATURALGAS")
        for row in rows:
            instr = col(row, "SEM_INSTRUMENT_NAME", "INSTRUMENT", "INSTRUMENT_TYPE").upper()
            exch = col(row, "SEM_EXM_EXCH_ID", "EXCH_ID", "EXCHANGE").upper()
            sym = col(row, "SEM_TRADING_SYMBOL", "TRADING_SYMBOL", "SYMBOL_NAME")
            sid = col(row, "SEM_SMST_SECURITY_ID", "SECURITY_ID")
            if not sym or not sid:
                continue

            # India VIX (index) — captured for the V11 volatility context.
            if instr == "INDEX" and exch == "NSE" and "VIX" in (sym + " " + col(row, "SM_SYMBOL_NAME")).upper():
                try:
                    DhanClient._vix_id = int(float(sid))
                except ValueError:
                    pass
                continue

            # MCX commodity futures: collect every live contract so the
            # active (nearest) one can be auto-selected — no manual IDs.
            if instr == "FUTCOM" and exch == "MCX":
                # UNDERLYING_SYMBOL is the clean base (e.g. CRUDEOIL); the
                # detailed master's expiry column is SM_EXPIRY_DATE.
                base = col(row, "UNDERLYING_SYMBOL", "SM_SYMBOL_NAME", "SYMBOL_NAME").upper() \
                    or sym.split("-")[0].split()[0].upper()
                if base in wanted_commodities:
                    raw_exp = col(row, "SM_EXPIRY_DATE", "SEM_EXPIRY_DATE", "EXPIRY_DATE")[:10]
                    try:
                        exp = datetime.date.fromisoformat(raw_exp)
                        commodity_futs.setdefault(base, []).append((exp, int(float(sid))))
                    except ValueError:
                        pass
                continue

            if instr != "EQUITY" or exch not in ("NSE", "BSE"):
                continue
            series = col(row, "SEM_SERIES", "SERIES").upper()
            if exch == "NSE" and series not in ("EQ", "BE", ""):
                continue
            name = col(row, "SM_SYMBOL_NAME", "SYMBOL_NAME", "DISPLAY_NAME") or sym
            try:
                scrips.append({"symbol": sym.upper(), "name": name.title(),
                               "security_id": int(float(sid)), "exchange": exch})
            except ValueError:
                continue
        DhanClient._scrips = scrips
        DhanClient._commodity_futs = commodity_futs
        log.info("Scrip master loaded: %d equities, %d commodity future chains",
                 len(scrips), len(commodity_futs))
        return len(scrips)

    def resolve_commodities(self) -> dict[str, int]:
        """Active (nearest unexpired) MCX contract per commodity."""
        today = datetime.date.today()
        out: dict[str, int] = {}
        for name, contracts in DhanClient._commodity_futs.items():
            live = sorted(c for c in contracts if c[0] >= today)
            if live:
                out[name] = live[0][1]
        return out

    def search_stocks(self, query: str, limit: int = 20) -> list[dict]:
        if not DhanClient._scrips:
            return []
        q = query.upper().strip()
        starts = [s for s in DhanClient._scrips if s["symbol"].startswith(q)]
        contains = [s for s in DhanClient._scrips
                    if q in s["symbol"] or q in s["name"].upper()]
        seen, out = set(), []
        for s in starts + contains:
            k = (s["symbol"], s["exchange"])
            if k not in seen:
                seen.add(k)
                out.append(s)
            if len(out) >= limit:
                break
        return out

    async def get_india_vix(self) -> float | None:
        """India VIX LTP for the V11 volatility context. None if unresolved."""
        if not DhanClient._vix_id:
            return None
        try:
            data = await self._request("POST", "/marketfeed/ltp",
                                       json={"IDX_I": [DhanClient._vix_id]})
            return parse_ltp(data, "IDX_I", DhanClient._vix_id)
        except (BrokerError, KeyError, TypeError):
            return None

    async def get_quotes_batch(self, segment: str, ids: list[int]) -> dict:
        """Full quotes for many instruments in one call — scanner fuel."""
        data = await self._request("POST", "/marketfeed/quote", json={segment: ids})
        return data.get("data", {}).get(segment, {})

    async def get_daily_candles(
        self, inst: Instrument, from_date: str, to_date: str
    ) -> list[dict]:
        """Daily OHLC history — used by the backtesting engine."""
        data = await self._request(
            "POST",
            "/charts/historical",
            json={
                "securityId": str(inst.security_id),
                "exchangeSegment": inst.segment,
                "instrument": "INDEX" if inst.market_type == "INDEX" else "FUTCOM",
                "expiryCode": 0,
                "fromDate": from_date,
                "toDate": to_date,
            },
        )
        candles = []
        for i in range(len(data.get("open", []))):
            candles.append({
                "time": data["timestamp"][i],
                "open": data["open"][i], "high": data["high"][i],
                "low": data["low"][i], "close": data["close"][i],
                "volume": data.get("volume", [0] * (i + 1))[i],
            })
        return candles

    # Dhan native intraday intervals; other TFs are resampled from these.
    TF_MAP = {"1m": ("1", 1), "3m": ("1", 3), "5m": ("5", 5), "15m": ("15", 15),
              "30m": ("15", 30), "1H": ("60", 60), "4H": ("60", 240)}

    async def get_tf_candles(self, inst: Instrument, tf: str, min_candles: int = 500) -> list[dict]:
        """Timeframe-aware history with >= min_candles, windowing past the
        broker's per-request day limit. '1D' uses the daily endpoint."""
        from ..engines.mtf import resample

        if tf == "1D":
            today = datetime.date.today()
            return await self.get_daily_candles(
                inst, (today - datetime.timedelta(days=900)).isoformat(), today.isoformat()
            )
        if tf not in self.TF_MAP:
            raise BrokerError(f"Unsupported timeframe {tf}")
        base, target_min = self.TF_MAP[tf]
        need_base = min_candles * (target_min // int(base))
        candles: list[dict] = []
        to = datetime.date.today()
        for _ in range(8):  # max 8 windows of 5 days
            frm = to - datetime.timedelta(days=5)
            try:
                chunk = await self._intraday_window(inst, base, frm, to)
            except BrokerError:
                break
            candles = chunk + candles
            if len(candles) >= need_base:
                break
            to = frm - datetime.timedelta(days=1)
        candles.sort(key=lambda c: c["time"])
        return resample(candles, target_min) if target_min > int(base) else candles

    async def _intraday_window(self, inst: Instrument, interval: str,
                               frm: datetime.date, to: datetime.date) -> list[dict]:
        data = await self._request(
            "POST", "/charts/intraday",
            json={
                "securityId": str(inst.security_id),
                "exchangeSegment": inst.segment,
                "instrument": "INDEX" if inst.market_type == "INDEX"
                              else "FUTCOM" if inst.market_type == "COMMODITY" else "EQUITY",
                "interval": interval,
                "fromDate": frm.isoformat(),
                "toDate": to.isoformat(),
            },
        )
        return [
            {"time": data["timestamp"][i], "open": data["open"][i], "high": data["high"][i],
             "low": data["low"][i], "close": data["close"][i],
             "volume": data.get("volume", [0] * (i + 1))[i]}
            for i in range(len(data.get("open", [])))
        ]

    async def get_intraday_range(self, inst: Instrument, interval: str,
                                 from_date: "datetime.date", to_date: "datetime.date") -> list[dict]:
        """Multi-month 1-min/5-min history for RESEARCH backtests (ORFE, 2026-08-07)
        — distinct from get_tf_candles(), which is tuned for live indicator
        warm-up (500 recent candles, 5-day windows) and deliberately capped
        at 40 days total. Dhan's own docs: /charts/intraday holds up to 5
        years but caps each REQUEST at 90 days — so this chunks by 90 days,
        oldest-first, same _request() path as every other call (shared
        rate-limit budget/backoff applies automatically, no separate throttle
        needed). Read-only historical pull; never called from the live loop."""
        out: list[dict] = []
        cur = from_date
        while cur <= to_date:
            window_end = min(cur + datetime.timedelta(days=90), to_date)
            chunk = await self._intraday_window(inst, interval, cur, window_end)
            out.extend(chunk)
            cur = window_end + datetime.timedelta(days=1)
        out.sort(key=lambda c: c["time"])
        return out

    async def get_intraday_candles(
        self, inst: Instrument, interval: str = "5", lookback_days: int = 5
    ) -> list[dict]:
        """OHLCV candles for the technical engine (EMA/VWAP/ATR/ADX)."""
        to = datetime.date.today()
        frm = to - datetime.timedelta(days=lookback_days)
        data = await self._request(
            "POST",
            "/charts/intraday",
            json={
                "securityId": str(inst.security_id),
                "exchangeSegment": inst.segment,
                "instrument": "INDEX" if inst.market_type == "INDEX"
                              else "FUTCOM" if inst.market_type == "COMMODITY" else "EQUITY",
                "interval": interval,
                "fromDate": frm.isoformat(),
                "toDate": to.isoformat(),
            },
        )
        candles = []
        for i in range(len(data.get("open", []))):
            candles.append(
                {
                    "time": data["timestamp"][i],
                    "open": data["open"][i],
                    "high": data["high"][i],
                    "low": data["low"][i],
                    "close": data["close"][i],
                    "volume": data.get("volume", [0] * (i + 1))[i],
                }
            )
        return candles
