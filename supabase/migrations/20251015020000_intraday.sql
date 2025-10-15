-- Stage 10: Intraday signal storage
-- Adds table for 12:55 PM PT decision snapshots per Method.md

create table if not exists eds.intraday_signals (
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

create index if not exists ix_intraday_trade_date on eds.intraday_signals(trade_date);
create index if not exists ix_intraday_symbol on eds.intraday_signals(symbol);

-- Grant permissions on the new table
grant all on eds.intraday_signals to service_role;
grant select on eds.intraday_signals to authenticated;

alter table eds.intraday_signals enable row level security;
create policy "read_intraday_signals" on eds.intraday_signals for select to authenticated using (true);
