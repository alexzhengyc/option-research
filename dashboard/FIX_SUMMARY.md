# Authentication Error Fix Summary

## Problem
The dashboard was showing an authentication error:
```
AuthApiError: Invalid Refresh Token: Refresh Token Not Found
```

## Root Causes

1. **Supabase client was trying to manage auth sessions** - Not needed for local data access
2. **Schema wasn't specified** - Data is in `eds` schema, not `public`
3. **Missing permissions** - The `anon` role didn't have access to the `eds` schema

## Solutions Applied ✅

### 1. Updated Supabase Client Configuration
**File**: `dashboard/lib/supabase.ts`

```typescript
export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: false,      // Don't save auth sessions
    autoRefreshToken: false,     // Don't refresh tokens
    detectSessionInUrl: false    // Don't look for auth in URL
  },
  db: {
    schema: 'eds'                // Use correct schema
  }
})
```

### 2. Granted Permissions to anon Role
**File**: `supabase/migrations/20251015030000_grant_anon_access.sql`

```sql
-- Grant schema usage to anon role
grant usage on schema eds to anon;

-- Grant select permission on table
grant select on eds.intraday_signals to anon;

-- Update RLS policy to allow both anon and authenticated
create policy "read_intraday_signals" 
  on eds.intraday_signals 
  for select 
  to anon, authenticated 
  using (true);
```

### 3. Applied Migration
```bash
supabase migration up
```

## Verification

Ran test connection:
```bash
node test-connection.js
```

Result:
```
✅ Connection successful!
📊 Found 59 total signals
✨ Dashboard should work perfectly!
```

## What to Do Next

### 1. Clear Browser Cache (Important!)
   - Open DevTools (F12)
   - Go to Application → Storage
   - Clear Local Storage for localhost:3000
   - Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)

### 2. Restart Dev Server
```bash
cd /Users/alexzheng/Documents/GitHub/option-research/dashboard
npm run dev
```

### 3. Open Dashboard
Navigate to: http://localhost:3000

## Expected Result

You should now see:
- ✅ No authentication errors
- ✅ Stats cards with actual numbers
- ✅ Charts displaying data
- ✅ Table showing 59 signals
- ✅ Date filter working

## Files Changed

1. ✅ `dashboard/lib/supabase.ts` - Updated client config
2. ✅ `supabase/migrations/20251015030000_grant_anon_access.sql` - New migration
3. ✅ `dashboard/test-connection.js` - Test script (new)
4. ✅ `dashboard/TROUBLESHOOTING.md` - Documentation (new)

## Why This Happened

The initial setup used standard Supabase configuration which assumes:
- Authentication is needed
- Data is in `public` schema
- Only `authenticated` role needs access

But your setup:
- No authentication needed (local dev)
- Data is in `eds` schema
- `anon` role needs access (anonymous key)

## Prevention

For future projects:
1. Always specify the schema if not using `public`
2. Grant permissions to `anon` role for public read access
3. Disable auth features when not needed
4. Test with `anon` key before deploying

## Testing

Test the connection anytime:
```bash
cd /Users/alexzheng/Documents/GitHub/option-research/dashboard
node test-connection.js
```

This will verify:
- Supabase is running
- Schema is accessible
- Permissions are correct
- Data exists

---

**Status**: ✅ Fixed and verified
**Date**: October 15, 2025
**Signals in Database**: 59

