"""Trade journal + signal history. Supabase when configured, in-memory otherwise."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from ..config import settings

log = logging.getLogger("journal")

_sb = None
if settings.supabase_url and settings.supabase_service_key:
    try:
        from supabase import create_client

        _sb = create_client(settings.supabase_url, settings.supabase_service_key)
    except Exception as e:  # missing dep or bad creds — degrade gracefully
        log.warning("Supabase unavailable, using in-memory journal: %s", e)

_memory: list[dict] = []


def add_entry(entry: dict[str, Any]) -> dict:
    row = {
        "id": str(uuid.uuid4()),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "date": entry.get("date") or time.strftime("%Y-%m-%d"),
        "time": entry.get("time") or time.strftime("%H:%M:%S"),
        "market": entry.get("market", ""),
        "signal": entry.get("signal", ""),
        "entry": entry.get("entry"),
        "exit": entry.get("exit"),
        "stop_loss": entry.get("stop_loss"),
        "target": entry.get("target"),
        "pnl": entry.get("pnl"),
        "confidence": entry.get("confidence"),
        "notes": entry.get("notes", ""),
        "reason": entry.get("reason", ""),
        "grade": entry.get("grade", ""),
        "screenshot": entry.get("screenshot", ""),
    }
    if _sb:
        try:
            _sb.table("trade_journal").insert(row).execute()
            return row
        except Exception as e:
            log.error("Supabase insert failed, falling back: %s", e)
    _memory.append(row)
    return row


def list_entries(limit: int = 200) -> list[dict]:
    if _sb:
        try:
            res = (
                _sb.table("trade_journal")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            log.error("Supabase read failed, falling back: %s", e)
    return list(reversed(_memory[-limit:]))


def log_signal(symbol: str, market_type: str, signal: dict[str, Any]) -> None:
    if not _sb or signal.get("signal") in (None, "NO TRADE"):
        return
    try:
        _sb.table("signals").insert({
            "symbol": symbol,
            "market_type": market_type,
            "signal": signal.get("signal"),
            "entry": signal.get("entry"),
            "stop_loss": signal.get("stop_loss"),
            "target1": signal.get("target1"),
            "target2": signal.get("target2"),
            "target3": signal.get("target3"),
            "confidence": signal.get("confidence"),
            "reasons": signal.get("reasons"),
        }).execute()
    except Exception as e:
        log.error("Signal log failed: %s", e)
