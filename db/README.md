# Database

This directory contains database migrations and local database files.

## Supabase Setup

### Local Development

1. **Install Supabase CLI** (if not already installed):
   ```bash
   brew install supabase/tap/supabase
   ```

2. **Initialize Supabase locally**:
   ```bash
   supabase init
   ```

3. **Start local Supabase**:
   ```bash
   supabase start
   ```
   This will start a local Postgres instance with Supabase services.

4. **Run the initial migration**:
   ```bash
   supabase db reset
   ```
   Or manually apply the migration:
   ```bash
   psql postgresql://postgres:postgres@localhost:54322/postgres -f db/000_init.sql
   ```

5. **Get your local connection details**:
   ```bash
   supabase status
   ```
   Note the API URL and service_role key for your `.env` file.

### Production Deployment

1. **Via Supabase SQL Editor**:
   - Log into your Supabase project dashboard
   - Navigate to SQL Editor
   - Copy and paste the contents of `000_init.sql`
   - Execute the script

2. **Via Supabase CLI**:
   ```bash
   supabase link --project-ref your-project-ref
   supabase db push
   ```

## Migrations

- `000_init.sql` - Initial schema creation with:
  - `eds` schema
  - Core tables: earnings_events, option_contracts, option_snapshots, daily_signals, oi_deltas
  - Performance indexes
  - Row Level Security (RLS) policies

## Schema Overview

### Tables

- **earnings_events**: Stores upcoming earnings announcements
- **option_contracts**: Option contract metadata (symbol, strike, expiry, etc.)
- **option_snapshots**: Time-series option market data
- **daily_signals**: Computed trading signals and decisions
- **oi_deltas**: Open interest changes over time

### Security

All tables have Row Level Security (RLS) enabled:
- Authenticated users can read all data
- Only service role can write/modify data (used by pipeline jobs)

