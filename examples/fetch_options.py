#!/usr/bin/env python
"""Example script demonstrating Polygon.io options chain integration.

Usage:
    python examples/fetch_options.py --ticker AAPL --expiry 2024-04-19
    
    # Compute features for pipeline
    python examples/fetch_options.py --ticker AAPL --earnings-date 2024-04-17 --compute-features

Prerequisites:
    1. Install dependencies: pip install -e .
    2. Set POLYGON_API_KEY environment variable or create .env file
"""
import argparse
from pathlib import Path

from dotenv import load_dotenv

from option_research import PolygonClient


def main():
    """Fetch and display options chain data."""
    parser = argparse.ArgumentParser(description="Fetch options chain from Polygon.io")
    parser.add_argument(
        "--ticker",
        type=str,
        required=True,
        help="Stock ticker symbol (e.g., AAPL)",
    )
    parser.add_argument(
        "--expiry",
        type=str,
        default=None,
        help="Options expiry date in ISO format (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--earnings-date",
        type=str,
        default=None,
        help="Earnings date (will compute expiry as first Friday after)",
    )
    parser.add_argument(
        "--compute-features",
        action="store_true",
        help="Compute pipeline features (RR, PCR, spreads)",
    )
    parser.add_argument(
        "--atm-window",
        type=float,
        default=0.10,
        help="ATM window for feature computation (default: 0.10 = ±10%%)",
    )
    args = parser.parse_args()

    # Load environment variables from .env file
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Initialize Polygon client
    try:
        client = PolygonClient()
    except ValueError as e:
        print(f"Error: {e}")
        print("\nTo get a free API key:")
        print("1. Visit https://polygon.io/")
        print("2. Sign up for an account")
        print("3. Copy your API key")
        print("4. Set environment variable: export POLYGON_API_KEY=your_key")
        print("   Or create a .env file in the project root")
        return 1

    # Determine expiry
    if args.earnings_date:
        expiry = PolygonClient.get_earnings_expiry(args.earnings_date)
        print(f"Earnings date: {args.earnings_date}")
        print(f"Computed event expiry: {expiry}\n")
    elif args.expiry:
        expiry = args.expiry
    else:
        print("Error: Must provide either --expiry or --earnings-date")
        return 1

    ticker = args.ticker.upper()

    try:
        # Fetch current stock price
        print(f"Fetching data for {ticker}...")
        spot_price = client.get_stock_price(ticker)
        print(f"Current price: ${spot_price:.2f}\n")

        if args.compute_features:
            # Compute pipeline features
            print("Computing chain features...")
            features = client.compute_chain_features(
                ticker=ticker,
                expiry=expiry,
                spot_price=spot_price,
                atm_window_pct=args.atm_window,
            )

            print(f"\n{'='*60}")
            print(f"PIPELINE FEATURES FOR {ticker} (expiry: {expiry})")
            print(f"{'='*60}")
            print(f"As of:                    {features['as_of']}")
            print(f"Spot price:               ${features['spot_price']:.2f}")
            print(f"Risk Reversal (25Δ):      {features['risk_reversal']:.4f}")
            print(f"Put volume (notional):    ${features['put_volume_notional']:,.0f}")
            print(f"Call volume (notional):   ${features['call_volume_notional']:,.0f}")
            print(f"PCR (notional):           {features['put_volume_notional'] / features['call_volume_notional']:.4f}")
            print(f"Median spread %:          {features['spread_pct'] * 100:.2f}%")
            print(f"Total notional volume:    ${features['total_notional_volume']:,.0f}")
            print(f"Number of calls (ATM):    {features['num_calls']}")
            print(f"Number of puts (ATM):     {features['num_puts']}")
            print(f"{'='*60}\n")

        else:
            # Fetch and display chain
            print(f"Fetching option chain for expiry {expiry}...")
            chain = client.get_option_chain(ticker, expiry, include_greeks=True)

            if not chain:
                print(f"No options found for {ticker} expiry {expiry}")
                return 0

            # Filter to show only near-the-money options
            atm_window = spot_price * args.atm_window
            lower = spot_price - atm_window
            upper = spot_price + atm_window
            atm_chain = [c for c in chain if lower <= c.strike <= upper]

            print(f"\nFound {len(chain)} total contracts ({len(atm_chain)} ATM)")
            print(f"\nShowing ATM ±{args.atm_window * 100:.0f}% contracts:\n")

            # Display chain
            print(f"{'Strike':<8} {'Type':<5} {'Bid':<8} {'Ask':<8} {'Last':<8} {'Vol':<8} {'OI':<10} {'IV':<8} {'Delta':<8}")
            print("-" * 90)

            for contract in sorted(atm_chain, key=lambda c: (c.strike, c.option_type)):
                iv_str = f"{contract.implied_volatility:.4f}" if contract.implied_volatility else "N/A"
                delta_str = f"{contract.delta:+.4f}" if contract.delta else "N/A"
                
                print(
                    f"{contract.strike:<8.2f} {contract.option_type.upper():<5} "
                    f"${contract.bid:<7.2f} ${contract.ask:<7.2f} ${contract.last:<7.2f} "
                    f"{contract.volume:<8} {contract.open_interest:<10} "
                    f"{iv_str:<8} {delta_str:<8}"
                )

    except RuntimeError as e:
        print(f"Error fetching data: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

