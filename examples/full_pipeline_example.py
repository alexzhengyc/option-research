#!/usr/bin/env python
"""Complete pipeline example combining Finnhub earnings + Polygon options data.

This script demonstrates the full workflow:
1. Fetch upcoming earnings events from Finnhub
2. For each ticker, compute the event expiry (first Friday after earnings)
3. Fetch options chain from Polygon for that expiry
4. Compute pipeline features (RR, PCR, spreads, etc.)
5. Save features to CSV for scoring

Usage:
    python examples/full_pipeline_example.py --days 7 --output features.csv
    
    # Filter to large-cap stocks only
    python examples/full_pipeline_example.py --days 7 --min-market-cap 10000000000 --output features.csv

Prerequisites:
    1. Install dependencies: pip install -e .
    2. Set both FINNHUB_API_KEY and POLYGON_API_KEY environment variables or create .env file
"""
import argparse
import csv
from pathlib import Path

from dotenv import load_dotenv

from option_research import FinnhubClient, PolygonClient


def main():
    """Run complete data collection pipeline."""
    parser = argparse.ArgumentParser(
        description="Collect earnings + options data for pipeline"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look ahead for earnings (default: 7)",
    )
    parser.add_argument(
        "--min-market-cap",
        type=float,
        default=None,
        help="Minimum market cap in dollars (e.g., 1e9 for $1B)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV file path (optional)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of tickers to process (for testing)",
    )
    args = parser.parse_args()

    # Load environment variables
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Initialize clients
    try:
        finnhub_client = FinnhubClient()
        print("✓ Finnhub client initialized")
    except ValueError as e:
        print(f"Error: {e}")
        print("\nSet FINNHUB_API_KEY environment variable or create .env file")
        return 1

    try:
        polygon_client = PolygonClient()
        print("✓ Polygon client initialized")
    except ValueError as e:
        print(f"Error: {e}")
        print("\nSet POLYGON_API_KEY environment variable or create .env file")
        return 1

    print(f"\nFetching earnings calendar for next {args.days} days...\n")

    # Step 1: Get upcoming earnings
    try:
        earnings_events = finnhub_client.get_upcoming_earnings(
            days_ahead=args.days,
            min_market_cap=args.min_market_cap,
        )
    except RuntimeError as e:
        print(f"Error fetching earnings: {e}")
        return 1

    if not earnings_events:
        print("No earnings events found matching criteria")
        return 0

    print(f"Found {len(earnings_events)} earnings events\n")

    # Limit if requested (useful for testing)
    if args.limit:
        earnings_events = earnings_events[: args.limit]
        print(f"Processing first {args.limit} tickers\n")

    # Step 2: For each ticker, fetch options data and compute features
    all_features = []
    
    print(f"{'Ticker':<8} {'Earnings':<12} {'Expiry':<12} {'Spot':<10} {'Status'}")
    print("-" * 70)

    for event in earnings_events:
        ticker = event.ticker
        earnings_date = event.earnings_date
        expiry = event.event_expiry

        try:
            # Fetch spot price
            spot_price = polygon_client.get_stock_price(ticker)

            # Compute chain features
            features = polygon_client.compute_chain_features(
                ticker=ticker,
                expiry=expiry,
                spot_price=spot_price,
                atm_window_pct=0.10,
            )

            # Add earnings metadata
            features["earnings_date"] = earnings_date
            features["eps_estimate"] = event.eps_estimate
            features["quarter"] = event.quarter
            features["year"] = event.year

            all_features.append(features)
            
            status = "✓"
            print(
                f"{ticker:<8} {earnings_date:<12} {expiry:<12} "
                f"${spot_price:<9.2f} {status}"
            )

        except Exception as e:
            status = f"✗ {str(e)[:30]}"
            print(
                f"{ticker:<8} {earnings_date:<12} {expiry:<12} {'N/A':<10} {status}"
            )
            continue

    print(f"\nSuccessfully collected data for {len(all_features)} tickers")

    # Step 3: Display summary statistics
    if all_features:
        print("\n" + "=" * 70)
        print("SUMMARY STATISTICS")
        print("=" * 70)
        
        avg_rr = sum(f["risk_reversal"] for f in all_features) / len(all_features)
        avg_spread = sum(f["spread_pct"] for f in all_features) / len(all_features)
        avg_notional = sum(f["total_notional_volume"] for f in all_features) / len(all_features)
        
        print(f"Average Risk Reversal (25Δ):     {avg_rr:+.4f}")
        print(f"Average Spread %:                {avg_spread * 100:.2f}%")
        print(f"Average Total Notional Volume:   ${avg_notional:,.0f}")
        print(f"Total Tickers:                   {len(all_features)}")
        
        # Show top 3 by volume
        print("\nTop 3 by Volume:")
        top_by_volume = sorted(all_features, key=lambda x: x["total_notional_volume"], reverse=True)[:3]
        for i, feat in enumerate(top_by_volume, 1):
            print(f"  {i}. {feat['ticker']}: ${feat['total_notional_volume']:,.0f}")
        
        # Show extreme risk-reversals
        print("\nHighest Risk Reversals (most bullish skew):")
        top_rr = sorted(all_features, key=lambda x: x["risk_reversal"], reverse=True)[:3]
        for i, feat in enumerate(top_rr, 1):
            print(f"  {i}. {feat['ticker']}: {feat['risk_reversal']:+.4f}")
        
        print("\nLowest Risk Reversals (most bearish skew):")
        bottom_rr = sorted(all_features, key=lambda x: x["risk_reversal"])[:3]
        for i, feat in enumerate(bottom_rr, 1):
            print(f"  {i}. {feat['ticker']}: {feat['risk_reversal']:+.4f}")
        
        print("=" * 70)

    # Step 4: Save to CSV if requested
    if args.output and all_features:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Define CSV columns
        fieldnames = [
            "ticker",
            "as_of",
            "earnings_date",
            "expiry",
            "spot_price",
            "risk_reversal",
            "put_volume_notional",
            "call_volume_notional",
            "spread_pct",
            "total_notional_volume",
            "num_calls",
            "num_puts",
            "eps_estimate",
            "quarter",
            "year",
        ]
        
        with output_path.open("w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for features in all_features:
                # Write only the fields we want
                row = {k: features.get(k) for k in fieldnames}
                writer.writerow(row)
        
        print(f"\n✓ Features saved to: {output_path}")
        print(f"  ({len(all_features)} rows)")
        print("\nNext step: Use this data to compute directional scores!")
        print(f"  python -m option_research {output_path} --trade-date <date>")

    return 0


if __name__ == "__main__":
    exit(main())

