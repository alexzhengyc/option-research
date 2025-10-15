"""
Score Today's Earnings Reports

This script:
1. Finds earnings reports for today
2. Gets option chain data for each symbol
3. Computes signals and scores
4. Displays ranked opportunities
"""
import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np

# Add lib to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "lib"))

from lib import (
    get_expiries,
    get_chain_snapshot,
    filter_expiries_around_earnings,
    compute_all_signals,
    compute_scores_batch
)
from lib.finnhub_client import FinnhubClient


def main():
    """Score today's earnings reports"""
    print("=" * 70)
    print("EARNINGS SCORES FOR TODAY")
    print("=" * 70)
    print(f"Date: {date.today()}")
    print()
    
    # Step 1: Get today's earnings (ALL symbols, not filtered)
    print("1. Finding earnings reports for today...")
    today = date.today()
    
    client = FinnhubClient()
    earnings_calendar = client.get_earnings_calendar(
        start_date=today,
        end_date=today
    )
    
    if not earnings_calendar:
        print("   No earnings found for today!")
        print()
        print("Try looking ahead to next few days:")
        print(f"   python {Path(__file__).name} --days-ahead 7")
        return
    
    print(f"   Found {len(earnings_calendar)} earnings events today!")
    print()
    
    # Convert to the format expected by filter_expiries_around_earnings
    earnings_events = []
    for event in earnings_calendar:
        symbol = event.get("symbol")
        earnings_date = event.get("date")  # Format: "YYYY-MM-DD"
        earnings_time = event.get("hour")  # Format: "bmo", "amc", or None
        
        if not symbol or not earnings_date:
            continue
        
        # Parse the date
        try:
            dt = datetime.strptime(earnings_date, "%Y-%m-%d")
            
            # Set time based on hour field
            if earnings_time == "bmo":
                dt = dt.replace(hour=9, minute=0)
            elif earnings_time == "amc":
                dt = dt.replace(hour=16, minute=30)
            else:
                # Default to after-market close
                dt = dt.replace(hour=16, minute=30)
            
            earnings_events.append({
                "symbol": symbol,
                "earnings_ts": dt,
                "earnings_date": dt.date()
            })
        except ValueError:
            continue
    
    print(f"   Processed {len(earnings_events)} earnings events")
    print()
    
    # Show first 10
    print("   Sample (first 10):")
    for event in earnings_events[:10]:
        print(f"   - {event['symbol']}: {event['earnings_ts']}")
    if len(earnings_events) > 10:
        print(f"   ... and {len(earnings_events) - 10} more")
    print()
    
    # Step 2: Filter for tradeable events (with valid expiries)
    print("2. Filtering for tradeable events...")
    
    tradeable_events = filter_expiries_around_earnings(
        earnings_events=earnings_events,
        get_expiries_func=get_expiries,
        max_event_dte=60,
        require_neighbors=False
    )
    
    if not tradeable_events:
        print("   No tradeable events found (no valid option expiries)")
        return
    
    print(f"   Found {len(tradeable_events)} tradeable events")
    print()
    
    # Step 3: Compute signals for each event
    print("3. Computing signals...")
    print()
    
    signals_list = []
    
    for i, event in enumerate(tradeable_events, 1):
        symbol = event["symbol"]
        event_date = event["expiries"]["event"]
        earnings_date = event["earnings_date"]
        
        print(f"   [{i}/{len(tradeable_events)}] {symbol}")
        print(f"       Earnings: {earnings_date}")
        print(f"       Event expiry: {event_date}")
        
        try:
            # Get option chains
            chains = {}
            
            # Event expiry
            if event["expiries"]["event"]:
                chains["event"] = get_chain_snapshot(
                    symbol,
                    event["expiries"]["event"],
                    event["expiries"]["event"]
                )
            else:
                chains["event"] = []
            
            # Prev expiry
            if event["expiries"]["prev"]:
                chains["prev"] = get_chain_snapshot(
                    symbol,
                    event["expiries"]["prev"],
                    event["expiries"]["prev"]
                )
            else:
                chains["prev"] = []
            
            # Next expiry
            if event["expiries"]["next"]:
                chains["next"] = get_chain_snapshot(
                    symbol,
                    event["expiries"]["next"],
                    event["expiries"]["next"]
                )
            else:
                chains["next"] = []
            
            total_contracts = len(chains["event"]) + len(chains["prev"]) + len(chains["next"])
            print(f"       Fetched {total_contracts} contracts")
            
            if not chains["event"]:
                print(f"       ✗ No event contracts, skipping")
                print()
                continue
            
            # Compute med20 volumes (simplified - use heuristic)
            # In production, this would query historical data
            med20_volumes = {
                "call_med20": 10000,
                "put_med20": 8000
            }
            
            # Compute signals
            signals = compute_all_signals(
                symbol=symbol,
                event_date=event_date,
                event_contracts=chains["event"],
                prev_contracts=chains["prev"] if chains["prev"] else None,
                next_contracts=chains["next"] if chains["next"] else None,
                med20_volumes=med20_volumes,
                lookback_days=3,
                sector_symbol="SPY"
            )
            
            # Add metadata
            signals["symbol"] = symbol
            signals["event_date"] = event_date
            signals["earnings_date"] = earnings_date
            
            signals_list.append(signals)
            print(f"       ✓ Computed signals")
            
        except Exception as e:
            print(f"       ✗ Error: {e}")
        
        print()
    
    if not signals_list:
        print("No signals computed. Exiting.")
        return
    
    # Step 4: Normalize and score
    print(f"4. Normalizing and scoring {len(signals_list)} events...")
    print()
    
    df_scored = compute_scores_batch(pd.DataFrame(signals_list))
    
    if df_scored.empty:
        print("   No scores computed")
        return
    
    print(f"   ✓ Scored {len(df_scored)} events")
    print()
    
    # Step 5: Display results
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()
    
    # Sort by absolute score
    df_scored["abs_score"] = df_scored["score"].abs()
    df_sorted = df_scored.sort_values("abs_score", ascending=False)
    
    # Display summary
    print("Summary:")
    print(f"  Total events analyzed: {len(df_sorted)}")
    print(f"  CALL signals: {len(df_sorted[df_sorted['decision'] == 'CALL'])}")
    print(f"  PUT signals: {len(df_sorted[df_sorted['decision'] == 'PUT'])}")
    print(f"  PASS_OR_SPREAD: {len(df_sorted[df_sorted['decision'] == 'PASS_OR_SPREAD'])}")
    print()
    
    # Display top opportunities
    print("Top Opportunities (sorted by |score|):")
    print()
    
    display_cols = [
        "symbol",
        "score",
        "decision",
        "rr_25d",
        "vol_pcr",
        "notional_pcr",
        "iv_bump",
        "spread_pct_atm",
        "beta_adj_return"
    ]
    
    # Filter to columns that exist
    display_cols = [col for col in display_cols if col in df_sorted.columns]
    
    for i, (idx, row) in enumerate(df_sorted.iterrows(), 1):
        symbol = row["symbol"]
        score = row["score"]
        decision = row["decision"]
        
        print(f"{i}. {symbol} - Score: {score:.3f} - {decision}")
        
        # Display key signals
        if "rr_25d" in row and pd.notna(row["rr_25d"]):
            print(f"   RR 25Δ: {row['rr_25d']:.4f}")
        
        if "vol_pcr" in row and pd.notna(row["vol_pcr"]):
            print(f"   Vol PCR: {row['vol_pcr']:.3f}")
        
        if "notional_pcr" in row and pd.notna(row["notional_pcr"]):
            print(f"   Notional PCR: {row['notional_pcr']:.3f}")
        
        if "iv_bump" in row and pd.notna(row["iv_bump"]):
            print(f"   IV Bump: {row['iv_bump']:.4f}")
        
        if "spread_pct_atm" in row and pd.notna(row["spread_pct_atm"]):
            print(f"   ATM Spread: {row['spread_pct_atm']:.2%}")
        
        if "beta_adj_return" in row and pd.notna(row["beta_adj_return"]):
            print(f"   Beta-Adj Return: {row['beta_adj_return']:.2%}")
        
        print()
    
    # Export to CSV
    output_file = project_root / "out" / f"earnings_scores_{today.strftime('%Y%m%d')}.csv"
    output_file.parent.mkdir(exist_ok=True)
    
    df_export = df_sorted[display_cols].copy()
    df_export.to_csv(output_file, index=False, float_format="%.4f")
    
    print("=" * 70)
    print(f"Results exported to: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()

