# Quick Start Guide

Get the dashboard running in under 2 minutes!

## Prerequisites Check

Before starting, verify you have:
- ✅ Node.js 18+ installed (`node --version`)
- ✅ Supabase CLI installed (`supabase --version`)
- ✅ Local Supabase running (`supabase status`)

## Step 1: Environment Setup (30 seconds)

```bash
cd dashboard
cp .env.example .env.local
```

The default `.env.local` should contain:
```env
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
```

> 💡 This is the default Supabase local development anon key. No changes needed!

## Step 2: Install Dependencies (60 seconds)

```bash
npm install
```

## Step 3: Start Supabase (if not running)

```bash
# Navigate to project root
cd ..

# Start Supabase
supabase start

# You should see output like:
# API URL: http://127.0.0.1:54321
# Studio URL: http://127.0.0.1:54323
```

## Step 4: Verify Data Exists

```bash
# Check if you have intraday signals
supabase db reset  # If needed to reset database

# Or run the intraday pipeline to generate signals
python jobs/intraday.py
```

## Step 5: Launch Dashboard! (5 seconds)

```bash
cd dashboard
npm run dev
```

Open your browser to: **http://localhost:3000**

## Expected Result

You should see:
- ✅ Dashboard with "Intraday Dashboard" header
- ✅ Four stat cards at the top
- ✅ Date filter dropdown (top right)
- ✅ Charts and Table tabs
- ✅ Data displayed (if signals exist in database)

## Troubleshooting

### "Error fetching signals"
**Problem**: Can't connect to Supabase

**Solutions**:
1. Check Supabase is running:
   ```bash
   supabase status
   ```
2. If not running, start it:
   ```bash
   cd /path/to/option-research
   supabase start
   ```
3. Verify URL in `.env.local` matches the API URL from `supabase status`

### "No signals found"
**Problem**: Database is empty

**Solutions**:
1. Run the intraday pipeline:
   ```bash
   cd /path/to/option-research
   python jobs/intraday.py
   ```
2. Or insert test data:
   ```sql
   -- Open Supabase Studio: http://127.0.0.1:54323
   -- Run SQL Editor with sample data
   INSERT INTO eds.intraday_signals (
     trade_date, symbol, asof_ts, decision, structure, direction,
     spot_price, dirscore_now, dirscore_ewma
   ) VALUES (
     CURRENT_DATE, 'TEST', NOW(), 'CALL', 'NAKED', 'CALL',
     100.0, 0.75, 0.70
   );
   ```

### Port 3000 already in use
**Problem**: Another app is using port 3000

**Solution**: Use a different port:
```bash
npm run dev -- -p 3001
```
Then open: http://localhost:3001

### Module not found errors
**Problem**: Dependencies not installed correctly

**Solution**: Reinstall dependencies:
```bash
rm -rf node_modules package-lock.json
npm install
```

## Next Steps

Once running, try:

1. **Filter by Date**: Use the date dropdown to view specific days
2. **Switch Views**: Toggle between "Charts" and "Table View"
3. **Explore Data**: Hover over charts for detailed tooltips
4. **Check Stats**: Monitor call/put ratios in stat cards

## Common Development Commands

```bash
# Development server (with hot reload)
npm run dev

# Production build (for deployment)
npm run build

# Start production server
npm run start

# Lint code
npm run lint
```

## Development Workflow

1. Make changes to components in `components/` or `app/`
2. Browser automatically reloads with changes
3. Check console for any errors
4. Test with different date filters
5. Verify charts and tables update correctly

## Architecture Overview

```
dashboard/
├── app/
│   ├── page.tsx          # Main dashboard page
│   └── layout.tsx        # Root layout
├── components/
│   ├── stats-cards.tsx   # Stat cards
│   ├── signals-chart.tsx # All charts
│   └── signals-table.tsx # Data table
├── hooks/
│   └── useIntradaySignals.ts  # Data hooks
├── lib/
│   └── supabase.ts       # DB client
└── types/
    └── supabase.ts       # TypeScript types
```

## Performance Tips

1. **Date Filtering**: Use date filter to reduce data load
2. **Table Pagination**: Consider adding pagination for large datasets
3. **Chart Sampling**: Limit to top N symbols for better performance

## Getting Help

1. Check the main [README.md](README.md)
2. Review [FEATURES.md](FEATURES.md) for detailed documentation
3. Inspect browser console for errors
4. Check Supabase logs: `supabase logs db`

## Success Checklist

- [x] Dependencies installed
- [x] Supabase running
- [x] Environment variables configured
- [x] Dashboard accessible at http://localhost:3000
- [x] Data displaying correctly
- [x] Charts rendering
- [x] Table showing signals
- [x] Date filter working

**You're all set! Happy trading! 📈**

