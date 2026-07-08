# KNOWN LIMITATIONS

*Honesty ledger — every "why doesn't it…?" answered in advance.
A limitation listed here is a fact, not a bug.*

## Data
- **Historical option-chain data unavailable** — Dhan provides historical
  candles for underlyings only. Premium/strike/IV history cannot be learned
  without an external EOD source (NSE bhavcopy ingestion = separate project).
- **Global market feeds not connected** — US futures, DXY, yields, etc. need an
  external API the owner must choose and supply. Until then the dashboard shows
  "Waiting for Data Source" (never fabricated).
- **News intelligence not connected** — same as above ("News Feed Not Connected").
- **Intraday history depth ~40 sessions** (broker limit) — strategy-level
  intraday backtests (VWAP/ORB win-rates) would be under-sampled and are
  therefore not published.
- **Named-event learning absent** (Budget/RBI/FOMC/Expiry-day tagging) — needs a
  reliable event-calendar source; day-of-week learning exists instead.

## Universe
- **Stock universe = configured watchlist** — the scanner/opportunity board
  ranks indices + watchlist. Widen it by adding F&O stocks to the watchlist.
- **MCX contract IDs resolve at runtime** for the connected instrument
  (contracts roll monthly) — unconnected commodities may be skipped by scans.

## Learning
- **Learning quality depends on validated live trades** — every "building /
  LEARNING" label fills only from settled outcomes (Rules 5–7).
- **Verdicts settle on ~30s cycle ticks** — violent gap moves can shave verdict
  confidence (the verdict carries its own confidence for this reason).
- **Shadow verdicts cover the connected instrument** — blocked-trade verdicts
  need live ticks; other symbols get coarser 30-min direction grading only.

## Scope
- **Advisory only** — the system never places orders and never sees real fills;
  P&L shown is level-based (underlying points), position tracking is via
  Paper Trading / lifecycle, not broker positions.
- **Intraday engine** — SWING/BTST/POSITION recommendations are intentionally
  not offered (no daily-timeframe decision stack).
