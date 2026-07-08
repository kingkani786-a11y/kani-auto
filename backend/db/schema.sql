-- CLOUD AI TRADER — Supabase schema
-- Credentials are deliberately NOT stored server-side by default; the access
-- token lives only in backend process memory and the user's browser
-- localStorage. If you must persist them, use Supabase Vault, never a table.

create table if not exists trade_journal (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  date date not null default current_date,
  time text,
  market text not null,
  signal text not null,
  entry numeric,
  exit numeric,
  stop_loss numeric,
  target numeric,
  pnl numeric,
  confidence numeric,
  notes text default ''
);

create table if not exists signals (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  symbol text not null,
  market_type text not null,
  signal text not null,
  entry numeric,
  stop_loss numeric,
  target1 numeric,
  target2 numeric,
  target3 numeric,
  confidence numeric,
  reasons jsonb
);

-- V4: journal extensions
alter table trade_journal add column if not exists reason text default '';
alter table trade_journal add column if not exists grade text default '';
alter table trade_journal add column if not exists screenshot text default '';

-- V4: Historical Market Memory (price / chain / OI / PCR / Greeks history)
create table if not exists market_memory (
  id uuid primary key default gen_random_uuid(),
  ts timestamptz not null default now(),
  symbol text not null,
  spot numeric,
  pcr numeric,
  max_pain numeric,
  call_oi numeric,
  put_oi numeric,
  atm_iv numeric,
  atm_delta_ce numeric,
  expiry text
);
create index if not exists idx_memory_symbol_ts on market_memory (symbol, ts desc);
alter table market_memory enable row level security;

create index if not exists idx_journal_created on trade_journal (created_at desc);
create index if not exists idx_signals_created on signals (created_at desc);

-- Backend uses the service-role key; lock the tables down for anon clients.
alter table trade_journal enable row level security;
alter table signals enable row level security;

-- signal_outcomes table for the self-learning engine
create table if not exists signal_outcomes (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  symbol text not null,
  signal text,
  regime text,
  layers jsonb,
  win boolean
);
create index if not exists idx_outcomes_regime on signal_outcomes (regime, created_at desc);
alter table signal_outcomes enable row level security;
