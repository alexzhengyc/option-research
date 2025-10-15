-- Grant anon role access to eds schema and intraday_signals table
-- This allows the dashboard to read data using the anon key

-- Grant schema usage to anon role
grant usage on schema eds to anon;

-- Grant select permission on intraday_signals table to anon
grant select on eds.intraday_signals to anon;

-- Update RLS policy to allow anon role
drop policy if exists "read_intraday_signals" on eds.intraday_signals;
create policy "read_intraday_signals" 
  on eds.intraday_signals 
  for select 
  to anon, authenticated 
  using (true);

