// Quick test script to verify Supabase connection
// Run with: node test-connection.js

const { createClient } = require('@supabase/supabase-js')

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'http://127.0.0.1:54321'
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0'

const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: false,
    autoRefreshToken: false,
    detectSessionInUrl: false
  },
  db: {
    schema: 'eds'
  }
})

async function testConnection() {
  console.log('🔍 Testing Supabase connection...\n')
  console.log(`URL: ${supabaseUrl}`)
  console.log(`Schema: eds\n`)

  try {
    // Test query
    const { data, error, count } = await supabase
      .from('intraday_signals')
      .select('*', { count: 'exact', head: false })
      .limit(5)

    if (error) {
      console.error('❌ Error:', error.message)
      console.error('Details:', error)
      process.exit(1)
    }

    console.log(`✅ Connection successful!`)
    console.log(`📊 Found ${count} total signals`)
    console.log(`\n📋 Sample data (first 5 records):`)
    console.log(JSON.stringify(data, null, 2))
    
    if (data && data.length > 0) {
      console.log('\n✨ Dashboard should work perfectly!')
    } else {
      console.log('\n⚠️  No data found. Run: python jobs/intraday.py')
    }

  } catch (err) {
    console.error('❌ Connection failed:', err.message)
    console.error('\n💡 Troubleshooting:')
    console.error('   1. Check Supabase is running: supabase status')
    console.error('   2. Verify migrations applied: supabase db reset')
    console.error('   3. Check .env.local has correct URL and key')
    process.exit(1)
  }
}

testConnection()

