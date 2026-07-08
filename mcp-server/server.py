"""CLOUD AI TRADER — MCP server.

Exposes the trading backend as MCP tools so any MCP client (Claude Code,
Claude Desktop, custom agents) can query live market state, signals and
the journal. Read-only by design except for journal entries — the MCP
layer can never place trades or change credentials.

Run:  pip install "mcp[cli]" httpx && python server.py
Env:  CAT_BACKEND_URL (default http://localhost:8000)
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

BACKEND = os.environ.get("CAT_BACKEND_URL", "http://localhost:8000")
mcp = FastMCP("cloud-ai-trader")


async def _get(path: str) -> Any:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BACKEND}{path}")
        r.raise_for_status()
        return r.json()


async def _post(path: str, body: dict) -> Any:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{BACKEND}{path}", json=body)
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def get_status() -> dict:
    """Connection, market-open state, selected symbol and data quality."""
    return await _get("/api/status")


@mcp.tool()
async def get_market_overview() -> dict:
    """Spot, analytics (PCR, max pain, OI), Greeks, smart-money, signal, risk."""
    return await _get("/api/market/overview")


@mcp.tool()
async def get_option_chain() -> dict:
    """The visible option chain (ATM ± 10 strikes) for the selected index."""
    return await _get("/api/market/optionchain")


@mcp.tool()
async def get_latest_signal() -> dict:
    """Latest AI signal with entry/SL/targets, confidence and risk assessment."""
    return await _get("/api/signal/latest")


@mcp.tool()
async def select_symbol(symbol: str) -> dict:
    """Switch analysis to another symbol (NIFTY, BANKNIFTY, SENSEX, FINNIFTY,
    MIDCPNIFTY, GOLD, SILVER, CRUDEOIL, NATURALGAS)."""
    return await _post("/api/symbol", {"symbol": symbol})


@mcp.tool()
async def get_intelligence() -> dict:
    """Full 10-layer confluence packet: layer scores, regime, probability,
    strike recommendation, early warning and the plain-language narrative."""
    return await _get("/api/intelligence")


@mcp.tool()
async def get_system_health() -> dict:
    """Broker/WS/token status, data delay and per-engine heartbeats."""
    return await _get("/api/health/system")


@mcp.tool()
async def get_paper_trades() -> dict:
    """Virtual paper-trading stats (P&L, win rate) and trade history."""
    return await _get("/api/paper")


@mcp.tool()
async def run_backtest(symbol: str, year: int) -> dict:
    """Backtest the daily approximation of the strategy (2022-2025)."""
    return await _post("/api/backtest", {"symbol": symbol, "year": year})


@mcp.tool()
async def get_scanner_results() -> list:
    """Latest 60s trade-scanner ranking across indices and the watchlist."""
    return await _get("/api/scanner")


@mcp.tool()
async def get_alerts() -> list:
    """Recent alerts (entries, targets, SLs, setups, scanner events)."""
    return await _get("/api/alerts")


@mcp.tool()
async def get_watchlist() -> dict:
    """User watchlist with live quotes and favorites."""
    return await _get("/api/watchlist")


@mcp.tool()
async def get_portfolio_risk() -> dict:
    """Portfolio exposure, open risk, max drawdown and suggested position size."""
    return await _get("/api/portfolio/risk")


@mcp.tool()
async def get_journal() -> list:
    """All trade journal entries, newest first."""
    return await _get("/api/journal")


@mcp.tool()
async def add_journal_entry(
    market: str,
    signal: str,
    entry: float | None = None,
    exit: float | None = None,
    stop_loss: float | None = None,
    target: float | None = None,
    pnl: float | None = None,
    confidence: float | None = None,
    notes: str = "",
) -> dict:
    """Record a trade in the journal."""
    return await _post("/api/journal", {
        "market": market, "signal": signal, "entry": entry, "exit": exit,
        "stop_loss": stop_loss, "target": target, "pnl": pnl,
        "confidence": confidence, "notes": notes,
    })


if __name__ == "__main__":
    mcp.run()
