# ARCHITECTURE — Cloud AI Trader X Pro (Architecture-Frozen, RC1)

**Stack**: FastAPI backend (always-on via LaunchAgent, port 8000) · Next.js 15
frontend (port 3000) · DhanHQ v2 broker (Client ID + Access Token, in-memory
only, never persisted) · Supabase persistence (7 tables). Advisory-only —
no order placement code exists.

## The full lifecycle (every link live)

```
Market → Opportunity → Strike → Gate → Decision → (Execution by human)
      → Verdict → Learning → Evidence → Proposal → Approval → Improvement
```

## Engine map (frozen set)

| Engine | Role | Key module |
|---|---|---|
| Confluence (12-layer) | directional scoring, mandatory gate, adaptive threshold, calibration FORCE-WAIT | `engines/confluence.py` |
| Universal Strike Engine | chain-capability detected per instrument (index/stock/MCX identical); ranking, premium plan | `engines/strike_selector.py`, `_option_tick` |
| Opportunity Engine | staged L1 quotes → L2 chains (top-N, spaced, cooldown-deferential) → L3 full engine on click | `services/opportunity.py` |
| Execution Gate | ONE authoritative BUY/WAIT/NO-TRADE + quality bar | `engines/execution_gate.py` |
| Verdict Engine | blocked-side shadow trades → CAPITAL_SAVED / MISSED_WINNER / NEUTRAL, per-module + per-regime, verdict confidence | `services/verdicts.py` |
| Audit tracker | taken-side WINNER/LOSER settle | `services/audit.py` |
| Exit / Re-entry / Cycle | trade management, banded exits, re-entry safety rule, chained forecast | `engines/exit_intelligence.py` |
| Historical Learning | 5-yr daily setups, vol-regime & DOW splits, analogue days (Market Memory), nightly refresh | `services/historical_learning.py` |
| Market DNA / Memory | live pattern snapshots + similarity | `engines/market_dna.py`, memory service |
| Kill Switch / Safe Mode / Capital Protection / Traps / NTZ / Gamma Shield | capital protection stack (overrides everything) | respective engines |
| Weight Approval | QUEUE → APPROVE → SIMULATE → APPLY (human-only) | `services/weight_approval.py` |
| Scanner + Index Radar | L1 momentum ranking (batch quotes) | `services/scanner.py`, `engines/index_radar.py` |

## Data-integrity guards (never fabricate)

- Universal LTP parser (11+ payload shapes), MarketClosedError-first resolution
- **Put-call parity chain sanity** at ingest (every instrument) AND at
  opportunity publish — parity-violating chains are rejected loudly
- Strike-step inference for stock chains; sorted expiries (nearest-first)
- Intraday expected-move horizon (1-day sigma cap), to-expiry kept separately
- Instrument-aware N/A (chain-less contracts never blocked on option layers)
- Rate budget: chain deep-scans defer when broker cooldown is active

## Modes

- **Trading** — decision-first stack (Mission/Command → Opportunity → Index →
  Strike/Plan/Qty → Point Capture → shields → diagnostics)
- **Research** — all analytics, learning, memory, evolution, audit
