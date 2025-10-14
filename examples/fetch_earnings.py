#!/usr/bin/env python
"""Example script demonstrating Finnhub earnings calendar integration.

Usage:
    python examples/fetch_earnings.py
    
    # With custom parameters
    python examples/fetch_earnings.py --days 14 --min-market-cap 10000000000

Prerequisites:
    1. Install dependencies: pip install -e .
    2. Set FINNHUB_API_KEY environment variable or create .env file
"""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from option_research import FinnhubClient


def main():
    """Fetch and display upcoming earnings events."""
    parser = argparse.ArgumentParser(description="Fetch upcoming earnings calendar")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look ahead (default: 7)",
    )
    parser.add_argument(
        "--min-market-cap",
        type=float,
        default=None,
        help="Minimum market cap in dollars (e.g., 1e9 for $1B)",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default=None,
        help="Fetch earnings for specific ticker only",
    )
    args = parser.parse_args()

    # Load environment variables from .env file
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Initialize Finnhub client
    try:
        client = FinnhubClient()
    except ValueError as e:
        print(f"Error: {e}")
        print("\nTo get a free API key:")
        print("1. Visit https://finnhub.io/register")
        print("2. Sign up for a free account")
        print("3. Copy your API key")
        print("4. Set environment variable: export FINNHUB_API_KEY=your_key")
        print("   Or create a .env file in the project root")
        return 1

    # Fetch earnings
    try:
        if args.ticker:
            print(f"Fetching earnings for {args.ticker}...")
            event = client.get_earnings_for_ticker(args.ticker, days_ahead=args.days)
            
            if event:
                events = [event]
            else:
                print(f"No upcoming earnings found for {args.ticker} in next {args.days} days")
                return 0
        else:
            print(f"Fetching earnings calendar for next {args.days} days...")
            events = client.get_upcoming_earnings(
                days_ahead=args.days,
                min_market_cap=args.min_market_cap,
            )

        if not events:
            print("No earnings events found matching criteria")
            return 0

        # Display results
        print(f"\nFound {len(events)} earnings events:\n")
        print(f"{'Ticker':<8} {'Earnings Date':<15} {'Event Expiry':<15} {'EPS Est':<10} {'Quarter'}")
        print("-" * 70)

        for event in events:
            eps_str = f"${event.eps_estimate:.2f}" if event.eps_estimate else "N/A"
            quarter_str = f"Q{event.quarter} {event.year}" if event.quarter and event.year else "N/A"
            
            print(
                f"{event.ticker:<8} {event.earnings_date:<15} {event.event_expiry:<15} "
                f"{eps_str:<10} {quarter_str}"
            )

        # Show market cap filter info
        if args.min_market_cap:
            print(f"\n(Filtered to market cap ≥ ${args.min_market_cap:,.0f})")

    except RuntimeError as e:
        print(f"Error fetching data: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

