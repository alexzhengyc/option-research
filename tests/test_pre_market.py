"""
Test script for pre-market job (Dev Stage 9)

This script demonstrates how to run the pre-market job and verify ΔOI calculations.

Usage:
    python examples/test_pre_market.py
"""
import sys
from pathlib import Path
from datetime import date, timedelta

# Add lib to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "lib"))
sys.path.insert(0, str(project_root / "config"))
sys.path.insert(0, str(project_root / "jobs"))

from jobs.pre_market import PreMarketJob
from lib.supa import SUPA


def test_pre_market_job():
    """Test the pre-market job"""
    print("=" * 70)
    print("TESTING PRE-MARKET JOB")
    print("=" * 70)
    
    # Test for yesterday
    yesterday = date.today() - timedelta(days=1)
    
    print(f"\nTesting pre-market job for {yesterday}")
    print("This will:")
    print("1. Fetch yesterday's earnings events")
    print("2. Compare OI from yesterday vs. today")
    print("3. Calculate ΔOI for ATM ±2 strikes")
    print("4. Write to eds.oi_deltas")
    print("5. Optionally update DirScore with ΔOI")
    
    # Run job
    job = PreMarketJob(trade_date=yesterday, update_scores=True)
    df_results = job.run()
    
    if df_results.empty:
        print("\n⚠️  No results. This is expected if:")
        print("   - Yesterday had no earnings events")
        print("   - Post-close job hasn't run for yesterday yet")
        print("   - Database is empty")
        return False
    
    # Verify results
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    
    # Check database writes
    result = SUPA.schema("eds").table("oi_deltas") \
        .select("*") \
        .eq("trade_date", yesterday.isoformat()) \
        .execute()
    
    print(f"\n✓ Found {len(result.data)} ΔOI records in database")
    
    if result.data:
        print("\nSample records:")
        for record in result.data[:3]:
            print(f"  {record['symbol']}: "
                  f"calls={record['d_oi_calls']:+d}, "
                  f"puts={record['d_oi_puts']:+d}")
    
    # Check if scores were updated
    signals_result = SUPA.schema("eds").table("daily_signals") \
        .select("symbol,dirscore,decision") \
        .eq("trade_date", yesterday.isoformat()) \
        .execute()
    
    if signals_result.data:
        print(f"\n✓ Found {len(signals_result.data)} updated signals")
        print("\nSample signals:")
        for signal in signals_result.data[:3]:
            print(f"  {signal['symbol']}: "
                  f"score={signal.get('dirscore', 0):.3f}, "
                  f"decision={signal.get('decision', 'N/A')}")
    
    return True


def check_pre_market_requirements():
    """Check if pre-market job can run"""
    print("Checking pre-market job requirements...")
    
    # Check if we have yesterday's earnings events
    yesterday = date.today() - timedelta(days=1)
    
    result = SUPA.schema("eds").table("daily_signals") \
        .select("symbol,event_expiry", count="exact") \
        .eq("trade_date", yesterday.isoformat()) \
        .execute()
    
    if result.count == 0:
        print(f"\n❌ No earnings events found for {yesterday}")
        print("   Run post_close.py for yesterday first:")
        print(f"   python jobs/post_close.py --date {yesterday}")
        return False
    
    print(f"\n✓ Found {result.count} earnings events for {yesterday}")
    
    # Check if we have option snapshots from yesterday
    snapshot_result = SUPA.schema("eds").table("option_snapshots") \
        .select("option_symbol", count="exact") \
        .execute()
    
    if snapshot_result.count == 0:
        print("\n❌ No option snapshots found")
        print("   Run post_close.py first to generate snapshots")
        return False
    
    print(f"✓ Found {snapshot_result.count} option snapshots in database")
    
    return True


def main():
    """Main entry point"""
    print("Pre-Market Job Test Script\n")
    
    # Check requirements
    if not check_pre_market_requirements():
        print("\n⚠️  Pre-market job cannot run yet")
        print("   Make sure post_close.py has run for yesterday")
        return
    
    # Run test
    print("\n")
    success = test_pre_market_job()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ PRE-MARKET JOB TEST PASSED")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("ℹ️  Pre-market job test completed (no data available)")
        print("=" * 70)


if __name__ == "__main__":
    main()

