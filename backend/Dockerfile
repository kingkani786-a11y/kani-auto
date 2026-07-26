# Cloud AI Trader — Backend (FastAPI/uvicorn)
#
# Broker credentials (Dhan Client ID/Token) are DELIBERATELY never baked into
# this image or injected via env — owner's explicit decision (2026-07-26):
# they're entered through the Settings UI at runtime and held in
# state.credentials (in-process memory only), exactly as the non-Docker
# deployment already works. Only non-broker config (Supabase, app password,
# Gemini/Anthropic key, capital/risk defaults) comes via .env — see
# backend/.env.example for the full list.
FROM python:3.14-slim

WORKDIR /app

# curl only for the HEALTHCHECK below — kept out of the final layer size
# concerns by using --no-install-recommends
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# google-genai is commented out in requirements.txt (repo convention: "install
# only the provider you use") but this deployment runs CAT_AI_PROVIDER=gemini
# live — installed explicitly so the image matches actual running behavior.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "google-genai>=1.0"

COPY app ./app

# No .git directory is copied into the image, so _startup_commit()'s git
# subprocess would always return "unknown" — baked in via build arg instead
# (routes.py checks GIT_COMMIT env first, falls back to git for native runs).
ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=$GIT_COMMIT

# CAT_DATA_DIR already exists as an env hook (opportunity_metrics.py,
# premium_series.py, period_pivot_cache.py all honor it) — reused here to
# redirect the black-box log directory onto the mounted volume, zero new code.
ENV CAT_DATA_DIR=/app/data
RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
