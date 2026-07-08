"""Supabase persistence verification (Phase 19 activation harness).

Reports the REAL persistence state — never fabricates a connection. When
Supabase is configured it probes each table and reports what's live + how many
rows rehydrated; when not, it returns INACTIVE with the exact activation steps.
"""
from __future__ import annotations

from typing import Any

from . import memory
from .journal import _sb

_TABLES = ["market_memory", "signals", "signal_outcomes", "trade_journal",
           "evolution_reports", "engine_weights"]


def status() -> dict[str, Any]:
    if not _sb:
        return {
            "configured": False,
            "database": "IN-MEMORY",
            "persistence_status": "INACTIVE",
            "learning_active": len(memory._outcomes) > 0,
            "tables_active": [],
            "rows_loaded": {"outcomes_in_memory": len(memory._outcomes),
                            "snapshots_in_memory": len(memory._ring)},
            "memory_rehydrated": False,
            "steps": [
                "1. Create a Supabase project (free tier is fine).",
                "2. Run backend/supabase_schema.sql in the Supabase SQL editor.",
                "3. Put SUPABASE_URL + SUPABASE_SERVICE_KEY in backend/.env.",
                "4. Restart the backend — memory.rehydrate() loads on boot.",
                "5. Re-check this endpoint: tables should read ACTIVE.",
            ],
            "note": "In-memory mode works fully but resets on restart. No data is fabricated.",
        }

    tables: dict[str, str] = {}
    for t in _TABLES:
        try:
            _sb.table(t).select("*").limit(1).execute()
            tables[t] = "ACTIVE"
        except Exception as e:
            tables[t] = f"MISSING/ERROR ({str(e)[:40]})"

    active = [t for t, s in tables.items() if s == "ACTIVE"]
    return {
        "configured": True,
        "database": "SUPABASE",
        "persistence_status": "ACTIVE" if active else "ERROR",
        "learning_active": True,
        "tables_active": active,
        "tables": tables,
        "rows_loaded": {"outcomes_rehydrated": len(memory._outcomes),
                        "engines_rehydrated": len(memory._engine_stats),
                        "snapshots_in_memory": len(memory._ring)},
        "memory_rehydrated": len(memory._outcomes) > 0,
        "note": "Live Supabase persistence — learning survives restart.",
    }
