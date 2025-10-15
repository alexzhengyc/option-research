"""
Example: Get Recent Earnings Reports

This example demonstrates how to fetch recent and upcoming earnings reports
using the Finnhub API client.
"""
import sys
from pathlib import Path
from datetime import date, timedelta

# Add lib to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "lib"))

from lib.finnhub_client import FinnhubClient


def example_basic_earnings_calendar():
    """Example: Get all earnings for the next 7 days"""
    print("=" * 60)
    print("Example 1: Basic Earnings Calendar")
    print("=" * 60)
    
    client = FinnhubClient()
    
    # Get earnings for next 7 days
    start_date = date.today()
    end_date = start_date + timedelta(days=7)
    
    print(f"Fetching earnings from {start_date} to {end_date}...\n")
    
    earnings = client.get_earnings_calendar(
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"Found {len(earnings)} earnings events\n")
    
    # Display first 10 events
    for event in earnings[:10]:
        symbol = event.get("symbol", "N/A")
        date_str = event.get("date", "N/A")
        time = event.get("hour", "N/A")
        eps_est = event.get("epsEstimate", "N/A")
        
        print(f"{symbol:8s} | {date_str} {time:5s} | EPS Est: {eps_est}")
    
    if len(earnings) > 10:
        print(f"... and {len(earnings) - 10} more")
    print()


def example_single_day_earnings():
    """Example: Get earnings for a single day (defaults to today)"""
    print("=" * 60)
    print("Example 2: Single Day Earnings")
    print("=" * 60)
    
    client = FinnhubClient()
    
    # Fetch earnings for today (or specify a different date)
    target_date = date.today()
    # To fetch for a specific date, use: target_date = date(2025, 10, 30)
    
    print(f"Fetching earnings for {target_date}...\n")
    
    earnings = client.get_earnings_calendar(
        start_date=target_date,
        end_date=target_date
    )
    
    print(f"Found {len(earnings)} earnings events on {target_date}:\n")
    
    if earnings:
        # Group by timing
        bmo_earnings = [e for e in earnings if e.get("hour") == "bmo"]
        amc_earnings = [e for e in earnings if e.get("hour") == "amc"]
        unspecified = [e for e in earnings if e.get("hour") not in ["bmo", "amc"]]
        
        if bmo_earnings:
            print(f"Before Market Open ({len(bmo_earnings)}):")
            for event in bmo_earnings[:5]:
                symbol = event.get("symbol", "N/A")
                eps_est = event.get("epsEstimate", "N/A")
                print(f"  {symbol:8s} | EPS Est: {eps_est}")
            if len(bmo_earnings) > 5:
                print(f"  ... and {len(bmo_earnings) - 5} more\n")
            else:
                print()
        
        if amc_earnings:
            print(f"After Market Close ({len(amc_earnings)}):")
            for event in amc_earnings[:5]:
                symbol = event.get("symbol", "N/A")
                eps_est = event.get("epsEstimate", "N/A")
                print(f"  {symbol:8s} | EPS Est: {eps_est}")
            if len(amc_earnings) > 5:
                print(f"  ... and {len(amc_earnings) - 5} more\n")
            else:
                print()
        
        if unspecified:
            print(f"Unspecified Timing ({len(unspecified)}):")
            for event in unspecified[:5]:
                symbol = event.get("symbol", "N/A")
                eps_est = event.get("epsEstimate", "N/A")
                print(f"  {symbol:8s} | EPS Est: {eps_est}")
            if len(unspecified) > 5:
                print(f"  ... and {len(unspecified) - 5} more")
            print()
    else:
        print("No earnings events found for this date.")
    print()


def example_single_symbol():
    """Example: Get earnings for a single symbol"""
    print("=" * 60)
    print("Example 3: Single Symbol Earnings")
    print("=" * 60)
    
    client = FinnhubClient()
    symbol = "AAPL"
    
    # Look ahead 60 days
    start_date = date.today()
    end_date = start_date + timedelta(days=60)
    
    print(f"Fetching earnings for {symbol}...")
    print(f"Date range: {start_date} to {end_date}\n")
    
    # Fetch with symbol filter
    earnings = client.get_earnings_calendar(
        start_date=start_date,
        end_date=end_date,
        symbol=symbol
    )
    
    if earnings:
        print(f"Found {len(earnings)} earnings event(s) for {symbol}:\n")
        
        for event in earnings:
            date_str = event.get("date", "N/A")
            time = event.get("hour", "N/A")
            eps_actual = event.get("epsActual", "N/A")
            eps_estimate = event.get("epsEstimate", "N/A")
            revenue_actual = event.get("revenueActual", "N/A")
            revenue_estimate = event.get("revenueEstimate", "N/A")
            
            print(f"Date: {date_str} {time}")
            print(f"  EPS:     Actual={eps_actual}, Estimate={eps_estimate}")
            print(f"  Revenue: Actual={revenue_actual}, Estimate={revenue_estimate}")
            print()
    else:
        print(f"No earnings found for {symbol} in the next 60 days.")
    print()


def example_earnings_with_filtering():
    """Example: Get earnings and filter by criteria"""
    print("=" * 60)
    print("Example 4: Earnings with Filtering")
    print("=" * 60)
    
    client = FinnhubClient()
    
    # Get earnings for next 14 days
    start_date = date.today()
    end_date = start_date + timedelta(days=14)
    
    print(f"Fetching earnings from {start_date} to {end_date}...\n")
    
    earnings = client.get_earnings_calendar(
        start_date=start_date,
        end_date=end_date
    )
    
    # Filter for after-market-close (AMC) earnings only
    amc_earnings = [e for e in earnings if e.get("hour") == "amc"]
    
    print(f"Total earnings: {len(earnings)}")
    print(f"After-market-close earnings: {len(amc_earnings)}\n")
    
    print("AMC Earnings (first 10):")
    for event in amc_earnings[:10]:
        symbol = event.get("symbol", "N/A")
        date_str = event.get("date", "N/A")
        print(f"  {symbol:8s} - {date_str}")
    
    if len(amc_earnings) > 10:
        print(f"  ... and {len(amc_earnings) - 10} more")
    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("RECENT EARNINGS REPORTS EXAMPLES")
    print("=" * 60 + "\n")
    
    try:
        # Run all examples
        example_basic_earnings_calendar()
        example_single_day_earnings()
        example_single_symbol()
        example_earnings_with_filtering()
        
        print("=" * 60)
        print("All examples completed successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure you have:")
        print("1. Set FINNHUB_API_KEY in your .env file")
        print("2. Installed required packages: pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()

