-- Stage 1: Schema Creation
-- This migration creates the earnings detection system (EDS) schema and tables

-- Optional: for time-series performance (if available in your project)
-- create extension if not exists timescaledb;

-- Create schema
create schema if not exists eds;

-- Grant usage on schema to authenticated users and service role
grant usage on schema eds to authenticated, service_role;
grant all on schema eds to service_role;

-- Table: earnings_events
-- Stores upcoming earnings announcements
create table if not exists eds.earnings_events(
  symbol text not null,
  earnings_ts timestamptz not null,
  primary key(symbol, earnings_ts)
);

-- Table: option_contracts
-- Stores metadata about option contracts
create table if not exists eds.option_contracts(
  option_symbol text primary key,
  symbol text not null,
  expiry date not null,
  strike numeric not null,
  option_type char(1) not null check (option_type in ('C','P'))
);

-- Table: option_snapshots
-- Stores time-series option market data snapshots
create table if not exists eds.option_snapshots(
  asof_ts timestamptz not null,
  option_symbol text not null references eds.option_contracts(option_symbol),
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
-- Stores computed daily trading signals
create table if not exists eds.daily_signals(
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
-- Stores open interest changes
create table if not exists eds.oi_deltas(
  trade_date date not null,
  symbol text not null,
  event_expiry date not null,
  d_oi_calls integer,
  d_oi_puts integer,
  primary key(trade_date, symbol)
);

-- Grant permissions on tables
grant all on all tables in schema eds to service_role;
grant select on all tables in schema eds to authenticated;

-- Indexes for performance
create index if not exists ix_snapshots_option_ts on eds.option_snapshots(option_symbol, asof_ts);
create index if not exists ix_contracts_symbol_expiry on eds.option_contracts(symbol, expiry);
create index if not exists ix_signals_date on eds.daily_signals(trade_date);
create index if not exists ix_events_ts on eds.earnings_events(earnings_ts);

-- Optional: promote snapshots to hypertable for TimescaleDB
-- Uncomment the following line if you have TimescaleDB extension enabled:
-- select create_hypertable('eds.option_snapshots','asof_ts', if_not_exists => true);

-- Stage 2: Row Level Security (RLS) & Access Model
-- Enable RLS on all tables (best practice for security)
-- Note: Service role key bypasses RLS

alter table eds.earnings_events enable row level security;
alter table eds.option_contracts enable row level security;
alter table eds.option_snapshots enable row level security;
alter table eds.daily_signals enable row level security;
alter table eds.oi_deltas enable row level security;

-- Create simple policies for read access
-- Authenticated users can read, but only service role can write
create policy "read_all_snapshots" on eds.option_snapshots for select to authenticated using (true);
create policy "read_all_signals" on eds.daily_signals for select to authenticated using (true);
create policy "read_all_events" on eds.earnings_events for select to authenticated using (true);
create policy "read_all_contracts" on eds.option_contracts for select to authenticated using (true);
create policy "read_all_oi_deltas" on eds.oi_deltas for select to authenticated using (true);

-- No insert/update policies needed; service role bypasses RLS for write operations

