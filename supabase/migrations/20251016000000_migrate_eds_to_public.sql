-- Migration: Move tables from eds schema to public schema
-- This migration creates all tables in public schema, migrates data, and sets up proper access

-- ============================================================================
-- STEP 1: Create tables in public schema
-- ============================================================================

-- Table: earnings_events
create table if not exists public.earnings_events(
  symbol text not null,
  earnings_ts timestamptz not null,
  primary key(symbol, earnings_ts)
);

-- Table: option_contracts
create table if not exists public.option_contracts(
  option_symbol text primary key,
  symbol text not null,
  expiry date not null,
  strike numeric not null,
  option_type char(1) not null check (option_type in ('C','P'))
);

-- Table: option_snapshots
create table if not exists public.option_snapshots(
  asof_ts timestamptz not null,
  option_symbol text not null references public.option_contracts(option_symbol),
  underlying_px numeric,
  bid numeric, 
  ask numeric, 
  last numeric,
  iv numeric, 
  delta numeric, 
  gamma numeric, 
  theta numeric, 
  vega numeric,
  volume bigint, 
  oi bigint,
  primary key(asof_ts, option_symbol)
);

-- Table: daily_signals
create table if not exists public.daily_signals(
  trade_date date not null,
  symbol text not null,
  event_expiry date not null,
  rr_25d numeric,
  pcr_volume numeric, 
  pcr_notional numeric,
  vol_thrust_calls numeric, 
  vol_thrust_puts numeric,
  atm_iv_event numeric, 
  atm_iv_prev numeric, 
  atm_iv_next numeric, 
  iv_bump numeric,
  spread_pct_atm numeric, 
  mom_3d_betaadj numeric,
  dirscore numeric, 
  decision text check (decision in ('CALL','PUT','PASS_OR_SPREAD')),
  primary key(trade_date, symbol)
);

-- Table: oi_deltas
create table if not exists public.oi_deltas(
  trade_date date not null,
  symbol text not null,
  event_expiry date not null,
  d_oi_calls integer,
  d_oi_puts integer,
  primary key(trade_date, symbol)
);

-- Table: intraday_signals
create table if not exists public.intraday_signals (
  trade_date date not null,
  symbol text not null,
  event_expiry date,
  asof_ts timestamptz not null,
  spot_price numeric,
  rr_25d numeric,
  net_thrust numeric,
  vol_pcr numeric,
  beta_adj_return numeric,
  iv_bump numeric,
  spread_pct_atm numeric,
  z_rr_25d numeric,
  z_net_thrust numeric,
  z_vol_pcr numeric,
  z_beta_adj_return numeric,
  pct_iv_bump numeric,
  z_spread_pct_atm numeric,
  dirscore_now numeric,
  dirscore_ewma numeric,
  decision text not null check (decision in ('CALL','PUT','PASS')),
  structure text not null check (structure in ('NAKED','VERTICAL','SKIP')),
  direction text not null check (direction in ('CALL','PUT','NONE')),
  call_volume numeric,
  put_volume numeric,
  total_volume numeric,
  size_reduction numeric,
  notes text,
  ewma_alpha numeric,
  primary key(asof_ts, symbol)
);

-- ============================================================================
-- STEP 2: Migrate data from eds schema to public schema
-- ============================================================================

-- Migrate earnings_events
insert into public.earnings_events (symbol, earnings_ts)
select symbol, earnings_ts 
from eds.earnings_events
on conflict (symbol, earnings_ts) do nothing;

-- Migrate option_contracts
insert into public.option_contracts (option_symbol, symbol, expiry, strike, option_type)
select option_symbol, symbol, expiry, strike, option_type
from eds.option_contracts
on conflict (option_symbol) do nothing;

-- Migrate option_snapshots
insert into public.option_snapshots (
  asof_ts, option_symbol, underlying_px, bid, ask, last, 
  iv, delta, gamma, theta, vega, volume, oi
)
select 
  asof_ts, option_symbol, underlying_px, bid, ask, last,
  iv, delta, gamma, theta, vega, volume, oi
from eds.option_snapshots
on conflict (asof_ts, option_symbol) do nothing;

-- Migrate daily_signals
insert into public.daily_signals (
  trade_date, symbol, event_expiry, rr_25d, pcr_volume, pcr_notional,
  vol_thrust_calls, vol_thrust_puts, atm_iv_event, atm_iv_prev, 
  atm_iv_next, iv_bump, spread_pct_atm, mom_3d_betaadj, dirscore, decision
)
select 
  trade_date, symbol, event_expiry, rr_25d, pcr_volume, pcr_notional,
  vol_thrust_calls, vol_thrust_puts, atm_iv_event, atm_iv_prev,
  atm_iv_next, iv_bump, spread_pct_atm, mom_3d_betaadj, dirscore, decision
from eds.daily_signals
on conflict (trade_date, symbol) do nothing;

-- Migrate oi_deltas
insert into public.oi_deltas (trade_date, symbol, event_expiry, d_oi_calls, d_oi_puts)
select trade_date, symbol, event_expiry, d_oi_calls, d_oi_puts
from eds.oi_deltas
on conflict (trade_date, symbol) do nothing;

-- Migrate intraday_signals
insert into public.intraday_signals (
  trade_date, symbol, event_expiry, asof_ts, spot_price, rr_25d, net_thrust,
  vol_pcr, beta_adj_return, iv_bump, spread_pct_atm, z_rr_25d, z_net_thrust,
  z_vol_pcr, z_beta_adj_return, pct_iv_bump, z_spread_pct_atm, dirscore_now,
  dirscore_ewma, decision, structure, direction, call_volume, put_volume,
  total_volume, size_reduction, notes, ewma_alpha
)
select 
  trade_date, symbol, event_expiry, asof_ts, spot_price, rr_25d, net_thrust,
  vol_pcr, beta_adj_return, iv_bump, spread_pct_atm, z_rr_25d, z_net_thrust,
  z_vol_pcr, z_beta_adj_return, pct_iv_bump, z_spread_pct_atm, dirscore_now,
  dirscore_ewma, decision, structure, direction, call_volume, put_volume,
  total_volume, size_reduction, notes, ewma_alpha
from eds.intraday_signals
on conflict (asof_ts, symbol) do nothing;

-- ============================================================================
-- STEP 3: Create indexes for performance
-- ============================================================================

create index if not exists ix_snapshots_option_ts on public.option_snapshots(option_symbol, asof_ts);
create index if not exists ix_contracts_symbol_expiry on public.option_contracts(symbol, expiry);
create index if not exists ix_signals_date on public.daily_signals(trade_date);
create index if not exists ix_events_ts on public.earnings_events(earnings_ts);
create index if not exists ix_intraday_trade_date on public.intraday_signals(trade_date);
create index if not exists ix_intraday_symbol on public.intraday_signals(symbol);

-- ============================================================================
-- STEP 4: Enable Row Level Security (RLS)
-- ============================================================================

alter table public.earnings_events enable row level security;
alter table public.option_contracts enable row level security;
alter table public.option_snapshots enable row level security;
alter table public.daily_signals enable row level security;
alter table public.oi_deltas enable row level security;
alter table public.intraday_signals enable row level security;

-- ============================================================================
-- STEP 5: Create RLS Policies
-- ============================================================================

-- Policies for earnings_events
create policy "read_all_events" 
  on public.earnings_events 
  for select 
  to anon, authenticated 
  using (true);

-- Policies for option_contracts
create policy "read_all_contracts" 
  on public.option_contracts 
  for select 
  to anon, authenticated 
  using (true);

-- Policies for option_snapshots
create policy "read_all_snapshots" 
  on public.option_snapshots 
  for select 
  to anon, authenticated 
  using (true);

-- Policies for daily_signals
create policy "read_all_signals" 
  on public.daily_signals 
  for select 
  to anon, authenticated 
  using (true);

-- Policies for oi_deltas
create policy "read_all_oi_deltas" 
  on public.oi_deltas 
  for select 
  to anon, authenticated 
  using (true);

-- Policies for intraday_signals
create policy "read_intraday_signals" 
  on public.intraday_signals 
  for select 
  to anon, authenticated 
  using (true);

-- ============================================================================
-- STEP 6: Grant permissions
-- ============================================================================

-- Grant all permissions to service_role (for backend operations)
grant all on public.earnings_events to service_role;
grant all on public.option_contracts to service_role;
grant all on public.option_snapshots to service_role;
grant all on public.daily_signals to service_role;
grant all on public.oi_deltas to service_role;
grant all on public.intraday_signals to service_role;

-- Grant select permissions to anon and authenticated (for dashboard/frontend)
grant select on public.earnings_events to anon, authenticated;
grant select on public.option_contracts to anon, authenticated;
grant select on public.option_snapshots to anon, authenticated;
grant select on public.daily_signals to anon, authenticated;
grant select on public.oi_deltas to anon, authenticated;
grant select on public.intraday_signals to anon, authenticated;

-- ============================================================================
-- STEP 7: Optional - Drop old eds schema tables (commented out for safety)
-- ============================================================================
-- Uncomment these lines after verifying the migration was successful:
-- drop table if exists eds.intraday_signals cascade;
-- drop table if exists eds.option_snapshots cascade;
-- drop table if exists eds.daily_signals cascade;
-- drop table if exists eds.oi_deltas cascade;
-- drop table if exists eds.option_contracts cascade;
-- drop table if exists eds.earnings_events cascade;
-- drop schema if exists eds cascade;

