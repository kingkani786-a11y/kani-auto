-- CLOUD AI TRADER X PRO — Phase 19 Supabase Memory Engine
-- Permanent learning memory. Run this once in the Supabase SQL editor.
-- The app degrades gracefully to in-memory when these tables / creds are absent;
-- with them present, accuracy / calibration / Brier / engine-reliability survive
-- every restart, refresh, redeploy and reboot.
--
-- Auth: set SUPABASE_URL and SUPABASE_SERVICE_KEY in the backend environment.

-- 1) Rolling market snapshots (price / PCR / OI / Greeks / max-pain) ----------
create table if not exists market_memory (
    id          bigint generated always as identity primary key,
    ts          timestamptz default now(),
    symbol      text,
    spot        double precision,
    pcr         double precision,
    max_pain    double precision,
    call_oi     double precision,
    put_oi      double precision,
    atm_iv      double precision,
    atm_delta_ce double precision,
    expiry      text
);
create index if not exists idx_market_memory_symbol_ts on market_memory (symbol, ts desc);

-- 2) Every generated signal --------------------------------------------------
create table if not exists signals (
    id          bigint generated always as identity primary key,
    created_at  timestamptz default now(),
    symbol      text,
    market_type text,
    signal      text,
    entry       double precision,
    stop_loss   double precision,
    target1     double precision,
    target2     double precision,
    target3     double precision,
    confidence  double precision,
    reasons     jsonb
);

-- 3) Settled outcomes — the core self-learning table -------------------------
--    Rehydrated on startup into _outcomes + _engine_stats (memory.rehydrate()).
create table if not exists signal_outcomes (
    id           bigint generated always as identity primary key,
    created_at   timestamptz default now(),
    symbol       text,
    signal       text,
    regime       text,
    session      text,
    layers       jsonb,
    engines_pass jsonb,             -- which engines were PASS at entry
    win          int,               -- 1 win / 0 loss
    pnl          double precision,  -- points
    r_multiple   double precision,
    confidence   double precision,  -- predicted confidence (for calibration/Brier)
    grade        text,
    direction    text,
    entry        double precision,
    stop         double precision,
    target       double precision,
    exit         double precision,
    dna          jsonb,             -- Phase 20 feature snapshot (trend/regime/pcr/adx/atr/vix/animal…)
    strike       text,              -- recommended strike at signal time
    premium_expansion_pct double precision,  -- planned premium expansion %
    opened       double precision,  -- epoch seconds
    closed       double precision   -- epoch seconds
);
create index if not exists idx_signal_outcomes_closed on signal_outcomes (closed desc);

-- 4) Trade journal (manual + auto) ------------------------------------------
create table if not exists trade_journal (
    id          uuid primary key,
    created_at  timestamptz default now(),
    date        text, time text, market text, signal text,
    entry double precision, exit double precision,
    stop_loss double precision, target double precision,
    pnl double precision, confidence double precision,
    notes text, reason text, grade text, screenshot text
);

-- 5b) Phase 22 — human-approved engine weights (production apply state) --------
create table if not exists engine_weights (
    weight_key  text primary key,   -- confluence WEIGHTS key (trend/structure/oi/greeks)
    engine      text,
    multiplier  double precision,    -- applied multiplier (1.0 = neutral)
    status      text,                -- APPLIED | REVERTED
    updated_at  text
);

-- 5c) Missed-winner evidence (gate-calibration data; V1.0 validation) ---------
create table if not exists missed_winners (
    id      bigint generated always as identity primary key,
    ts      double precision,
    bias    text,
    reason  text,
    points  double precision,
    start   double precision,
    closed  double precision
);
create index if not exists idx_missed_winners_closed on missed_winners (closed desc);

-- 5) Daily evolution / audit reports (Phase 21/23) ---------------------------
create table if not exists evolution_reports (
    id          bigint generated always as identity primary key,
    created_at  timestamptz default now(),
    period      text,              -- daily | weekly | monthly
    accuracy    double precision,
    calibration double precision,
    brier       double precision,
    best_engine text,
    worst_engine text,
    report      jsonb              -- full snapshot for audit trail
);
