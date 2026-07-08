"""Static application configuration (NOT broker credentials).

Broker credentials (Client ID / Access Token) are supplied at runtime via
the Settings page and live only in core.state.AppState.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase (optional — journal/signals fall back to in-memory store)
    supabase_url: str = ""
    supabase_service_key: str = ""

    # Engine cadence (seconds) — tuned to the fastest values that stay under
    # the broker rate limit (global 1.1s gate ≈ 54 req/min ceiling). At these
    # intervals the steady-state load is ~48 req/min:
    #   spot 2s≈30 + option 5s≈12 + ai 30s≈4 + scanner 120s≈2.
    # All env-overridable via CAT_* if a faster broker plan is available.
    spot_interval: float = 2.0      # live price ticker (was 3s)
    option_interval: float = 5.0    # CE/PE, OI, ΔOI, futures-derived (was 15s)
    greeks_interval: float = 5.0    # Greeks ride the option cycle
    ai_interval: float = 30.0       # decision/narrator/structure (was 180s)

    # Signal engine
    confidence_threshold: float = 65.0  # percent, configurable
    risk_free_rate: float = 0.07

    # Security: when set, the API requires login (Settings -> Secure Login)
    app_password: str = ""

    # Portfolio risk defaults (editable at runtime via Settings)
    capital: float = 1000000.0
    risk_per_trade_pct: float = 1.0

    # CORS
    frontend_origin: str = "*"

    class Config:
        env_file = ".env"
        env_prefix = "CAT_"


settings = Settings()
