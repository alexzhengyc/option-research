# Troubleshooting Guide

## Authentication Error: "Invalid Refresh Token"

### Problem
You see this error in the browser console:
```
AuthApiError: Invalid Refresh Token: Refresh Token Not Found
```

### Root Cause
The Supabase client was trying to manage authentication sessions, but for local development reading from the `eds` schema, we don't need authentication.

### Solution ✅
This has been fixed! The Supabase client is now configured with:
- `persistSession: false` - Don't save sessions
- `autoRefreshToken: false` - Don't refresh tokens
- `detectSessionInUrl: false` - Don't look for auth in URL
- `schema: 'eds'` - Use the correct database schema

### Clear Browser Cache

If you still see the error after the fix:

1. **Clear Browser Storage**:
   - Open DevTools (F12)
   - Go to Application/Storage tab
   - Clear "Local Storage" for localhost:3000
   - Clear "Session Storage" for localhost:3000
   - Refresh the page

2. **Hard Refresh**:
   - Chrome/Edge: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
   - Firefox: `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)
   - Safari: `Cmd+Option+R`

3. **Restart Dev Server**:
   ```bash
   # Stop the server (Ctrl+C)
   # Start fresh
   npm run dev
   ```

## Testing the Connection

Run the test script to verify everything works:

```bash
cd /Users/alexzheng/Documents/GitHub/option-research/dashboard
node test-connection.js
```

Expected output:
```
✅ Connection successful!
📊 Found X total signals
📋 Sample data (first 5 records):
[...]
✨ Dashboard should work perfectly!
```

## Common Issues

### Issue 1: "Cannot connect to Supabase"

**Check if Supabase is running:**
```bash
cd /Users/alexzheng/Documents/GitHub/option-research
supabase status
```

If not running:
```bash
supabase start
```

### Issue 2: "Table 'intraday_signals' does not exist"

**Apply migrations:**
```bash
cd /Users/alexzheng/Documents/GitHub/option-research
supabase db reset
```

### Issue 3: "No data showing"

**Generate signals:**
```bash
cd /Users/alexzheng/Documents/GitHub/option-research
python jobs/intraday.py
```

**Verify data exists:**
```sql
-- In Supabase Studio (http://127.0.0.1:54323)
-- Or use psql:
SELECT COUNT(*) FROM eds.intraday_signals;
```

### Issue 4: "Permission denied"

**Check RLS policies:**
The `eds.intraday_signals` table has Row Level Security enabled with a policy that allows `SELECT` for the `authenticated` role. The anon key should work.

If issues persist, temporarily disable RLS:
```sql
ALTER TABLE eds.intraday_signals DISABLE ROW LEVEL SECURITY;
```

## Environment Variables

Verify your `.env.local` file:

```bash
cd /Users/alexzheng/Documents/GitHub/option-research/dashboard
cat .env.local
```

Should contain:
```env
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
```

## Checking Supabase Configuration

Verify the API is exposed with the `eds` schema:

```bash
cd /Users/alexzheng/Documents/GitHub/option-research
cat supabase/config.toml | grep -A 5 "\[api\]"
```

Should show:
```toml
[api]
enabled = true
port = 54321
schemas = ["public", "graphql_public", "eds"]
```

## Network Issues

Test the API directly:

```bash
curl -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0" \
     http://127.0.0.1:54321/rest/v1/intraday_signals?limit=1
```

Expected: JSON response with signal data

## Browser Console Errors

### Error: "Failed to fetch"
- Supabase is not running
- Wrong URL in `.env.local`
- Port 54321 is blocked

### Error: "401 Unauthorized"
- Wrong anon key in `.env.local`
- RLS policy blocking access

### Error: "404 Not Found"
- Table doesn't exist (run migrations)
- Wrong schema (should be `eds`)

## Development vs Production

**For Local Development:**
- Uses `http://127.0.0.1:54321`
- Uses default anon key (safe for local)
- No authentication needed
- Schema: `eds`

**For Production (future):**
- Use production Supabase URL
- Use production anon key
- Consider authentication
- Keep schema: `eds`

## Still Having Issues?

1. **Stop everything and start fresh:**
   ```bash
   # Stop Next.js dev server (Ctrl+C)
   
   # Stop Supabase
   cd /Users/alexzheng/Documents/GitHub/option-research
   supabase stop
   
   # Start Supabase fresh
   supabase start
   
   # Apply migrations
   supabase db reset
   
   # Generate test data
   python jobs/intraday.py
   
   # Start dashboard
   cd dashboard
   npm run dev
   ```

2. **Check all the things:**
   ```bash
   # Run verification script
   cd /Users/alexzheng/Documents/GitHub/option-research/dashboard
   ./verify-setup.sh
   ```

3. **Test connection:**
   ```bash
   node test-connection.js
   ```

4. **Check browser console:**
   - Open DevTools (F12)
   - Look for specific error messages
   - Check Network tab for failed requests

## Quick Fixes Checklist

- [ ] Supabase is running (`supabase status`)
- [ ] Migrations applied (`supabase db reset`)
- [ ] Data exists (`SELECT COUNT(*) FROM eds.intraday_signals`)
- [ ] `.env.local` has correct values
- [ ] Browser cache cleared (Local Storage + hard refresh)
- [ ] Dev server restarted
- [ ] Node modules installed (`npm install`)
- [ ] No build errors (`npm run build`)

## Success Indicators

When everything works, you should see:
- ✅ Dashboard loads without errors
- ✅ Stats cards show numbers (not "Loading...")
- ✅ Charts render with data
- ✅ Table shows signals
- ✅ No red errors in browser console
- ✅ Date filter works

---

**Last Updated:** After fixing auth token issue
**Status:** ✅ Resolved with schema configuration

