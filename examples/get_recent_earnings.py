"""
Example: Get Recent Earnings Reports

This example demonstrates how to fetch recent and upcoming earnings reports
using the Finnhub API client.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add lib to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "lib"))

from lib.finnhub_client import FinnhubClient


def get_today_and_tomorrow_earnings():
    """Get earnings for today and tomorrow in PT timezone"""
    print("=" * 60)
    print("Today and Tomorrow Earnings (PT Timezone)")
    print("=" * 60)
    
    client = FinnhubClient()
    
    # Get current time in PT timezone
    pt_tz = ZoneInfo("America/Los_Angeles")
    now_pt = datetime.now(pt_tz)
    today_pt = now_pt.date()
    tomorrow_pt = today_pt + timedelta(days=1)
    
    print(f"Current PT Time: {now_pt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Fetching earnings for: {today_pt} and {tomorrow_pt}\n")
    
    # Fetch earnings for today and tomorrow
    earnings = client.get_earnings_calendar(
        start_date=today_pt,
        end_date=tomorrow_pt
    )
    
    print(f"Found {len(earnings)} total earnings events\n")
    
    # Group by date
    today_earnings = [e for e in earnings if e.get("date") == str(today_pt)]
    tomorrow_earnings = [e for e in earnings if e.get("date") == str(tomorrow_pt)]
    
    # Display today's earnings
    if today_earnings:
        print(f"TODAY ({today_pt}) - {len(today_earnings)} events:")
        print("-" * 60)
        
        # Group by timing
        bmo = [e for e in today_earnings if e.get("hour") == "bmo"]
        amc = [e for e in today_earnings if e.get("hour") == "amc"]
        unspecified = [e for e in today_earnings if e.get("hour") not in ["bmo", "amc"]]
        
        if bmo:
            print(f"\n  Before Market Open ({len(bmo)}):")
            for event in bmo:
                symbol = event.get("symbol", "N/A")
                eps_est = event.get("epsEstimate", "N/A")
                print(f"    {symbol:8s} | EPS Est: {eps_est}")
        
        if amc:
            print(f"\n  After Market Close ({len(amc)}):")
            for event in amc:
                symbol = event.get("symbol", "N/A")
                eps_est = event.get("epsEstimate", "N/A")
                print(f"    {symbol:8s} | EPS Est: {eps_est}")
        
        if unspecified:
            print(f"\n  Unspecified Timing ({len(unspecified)}):")
            for event in unspecified:
                symbol = event.get("symbol", "N/A")
                eps_est = event.get("epsEstimate", "N/A")
                print(f"    {symbol:8s} | EPS Est: {eps_est}")
        print()
    else:
        print(f"TODAY ({today_pt}): No earnings events found.\n")
    
    # Display tomorrow's earnings
    if tomorrow_earnings:
        print(f"TOMORROW ({tomorrow_pt}) - {len(tomorrow_earnings)} events:")
        print("-" * 60)
        
        # Group by timing
        bmo = [e for e in tomorrow_earnings if e.get("hour") == "bmo"]
        amc = [e for e in tomorrow_earnings if e.get("hour") == "amc"]
        unspecified = [e for e in tomorrow_earnings if e.get("hour") not in ["bmo", "amc"]]
        
        if bmo:
            print(f"\n  Before Market Open ({len(bmo)}):")
            for event in bmo:
                symbol = event.get("symbol", "N/A")
                eps_est = event.get("epsEstimate", "N/A")
                print(f"    {symbol:8s} | EPS Est: {eps_est}")
        
        if amc:
            print(f"\n  After Market Close ({len(amc)}):")
            for event in amc:
                symbol = event.get("symbol", "N/A")
                eps_est = event.get("epsEstimate", "N/A")
                print(f"    {symbol:8s} | EPS Est: {eps_est}")
        
        if unspecified:
            print(f"\n  Unspecified Timing ({len(unspecified)}):")
            for event in unspecified:
                symbol = event.get("symbol", "N/A")
                eps_est = event.get("epsEstimate", "N/A")
                print(f"    {symbol:8s} | EPS Est: {eps_est}")
        print()
    else:
        print(f"TOMORROW ({tomorrow_pt}): No earnings events found.\n")


def main():
    """Get today and tomorrow's earnings in PT timezone"""
    print("\n" + "=" * 60)
    print("EARNINGS: TODAY & TOMORROW (PT)")
    print("=" * 60 + "\n")
    
    try:
        get_today_and_tomorrow_earnings()
        
        print("=" * 60)
        print("Completed successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure you have:")
        print("1. Set FINNHUB_API_KEY in your .env file")
        print("2. Installed required packages: pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()

