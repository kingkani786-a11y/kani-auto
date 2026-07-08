"""Instrument registry mapping app symbols to broker (DhanHQ v2) identifiers.

Index security IDs are stable. MCX commodity contracts roll monthly —
update `security_id` for commodities from the Dhan instrument master
(https://images.dhan.co/api-data/api-scrip-master.csv) when contracts roll,
or wire up scrip-master auto-resolution in DhanClient.resolve_commodity().
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    symbol: str
    market_type: str        # INDEX | COMMODITY
    security_id: int        # Dhan securityId of the underlying
    segment: str            # IDX_I for indices, MCX_COMM for commodities
    lot_size: int
    strike_step: float
    tv_symbol: str          # TradingView chart symbol


INSTRUMENTS: dict[str, Instrument] = {
    # ---- INDEX ----
    "NIFTY":      Instrument("NIFTY", "INDEX", 13, "IDX_I", 75, 50, "NSE:NIFTY"),
    "BANKNIFTY":  Instrument("BANKNIFTY", "INDEX", 25, "IDX_I", 30, 100, "NSE:BANKNIFTY"),
    "SENSEX":     Instrument("SENSEX", "INDEX", 51, "IDX_I", 20, 100, "BSE:SENSEX"),
    "FINNIFTY":   Instrument("FINNIFTY", "INDEX", 27, "IDX_I", 65, 50, "NSE:FINNIFTY"),
    "MIDCPNIFTY": Instrument("MIDCPNIFTY", "INDEX", 442, "IDX_I", 120, 25, "NSE:MIDCPNIFTY"),
    # ---- COMMODITY (MCX; security_id must track the active contract) ----
    "GOLD":       Instrument("GOLD", "COMMODITY", 0, "MCX_COMM", 100, 100, "MCX:GOLD"),
    "SILVER":     Instrument("SILVER", "COMMODITY", 0, "MCX_COMM", 30, 100, "MCX:SILVER"),
    "CRUDEOIL":   Instrument("CRUDEOIL", "COMMODITY", 0, "MCX_COMM", 100, 50, "MCX:CRUDEOIL"),
    "NATURALGAS": Instrument("NATURALGAS", "COMMODITY", 0, "MCX_COMM", 1250, 5, "MCX:NATURALGAS"),
}


# Dynamic registry for stocks resolved from the Dhan scrip master at runtime.
DYNAMIC: dict[str, Instrument] = {}

# Runtime security-id overrides — used by the auto-resolved MCX contracts so
# commodities work without manual configuration (contracts roll monthly).
OVERRIDES: dict[str, int] = {}


def set_security_override(symbol: str, security_id: int) -> None:
    OVERRIDES[symbol.upper()] = security_id


def register_stock(symbol: str, security_id: int, exchange: str) -> Instrument:
    """exchange: NSE -> NSE_EQ, BSE -> BSE_EQ. Stocks trade in qty 1 for analysis."""
    seg = "NSE_EQ" if exchange.upper() == "NSE" else "BSE_EQ"
    tv = f"{'NSE' if seg == 'NSE_EQ' else 'BSE'}:{symbol.upper().replace('-', '_')}"
    inst = Instrument(symbol.upper(), "STOCK", security_id, seg, 1, 0, tv)
    DYNAMIC[inst.symbol] = inst
    return inst


def get_instrument(symbol: str) -> Instrument:
    import dataclasses

    s = symbol.upper()
    inst = INSTRUMENTS.get(s) or DYNAMIC.get(s)
    if inst is None:
        raise ValueError(f"Unsupported symbol: {symbol}")
    sid = OVERRIDES.get(s)
    if sid and sid != inst.security_id:
        inst = dataclasses.replace(inst, security_id=sid)
    return inst
