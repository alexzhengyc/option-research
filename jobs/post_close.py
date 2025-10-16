"""
Dev Stage 8 - Post-Close Job
Run after market close to:
1. Load universe + earnings today/tomorrow → upsert public.earnings_events
2. For each symbol with future earnings:
   - Pull expiries (event, prev, next)
   - Snapshot chain for these expiries
   - Upsert public.option_contracts
   - Insert batch rows into public.option_snapshots with single asof_ts
   - Aggregate and compute signals
   - Normalize & score
   - Write one row to public.daily_signals (trade_date = today)
3. Export /out/predictions_YYYYMMDD.csv

Usage:
  python jobs/post_close.py                    # Default: today + tomorrow
  python jobs/post_close.py --days-ahead 0     # Today only
  python jobs/post_close.py --days-ahead 1     # Today + tomorrow
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from typing import List, Dict, Optional

# Add lib to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "lib"))
sys.path.insert(0, str(project_root / "config"))

# Import library functions
from lib import (
    get_chain_snapshot,
    compute_all_signals,
    compute_scores_batch,
    get_earnings_events,
    get_expiries,
    find_event_and_neighbors
)
from lib.supa import upsert_rows, insert_rows
from lib.polygon_client import get_underlying_agg
import config


class PostCloseJob:
    """Post-close job for capturing option snapshots and generating predictions"""
    
    def __init__(self, trade_date: Optional[date] = None, days_ahead: int = 1):
        """
        Initialize post-close job
        
        Args:
            trade_date: Trade date to use (defaults to today)
            days_ahead: Days to look ahead for earnings (0=today, 1=tomorrow, default: 1)
        """
        self.trade_date = trade_date or date.today()
        self.asof_ts = datetime.now()
        self.days_ahead = days_ahead
        
        # Universe of symbols to track
        # TODO: Load this from a config file or database
        self.universe = self._load_universe()
        
        print(f"Initialized PostCloseJob for {self.trade_date}")
        print(f"Snapshot timestamp: {self.asof_ts}")
        print(f"Universe size: {len(self.universe)} symbols")
        print(f"Looking ahead: {days_ahead} day(s)")
    
    def _load_universe(self) -> List[str]:
        """
        Load the universe of symbols to track
        
        Returns:
            List of stock ticker symbols
        """
        # Default universe: liquid tech stocks and major indices components
        # In production, this would come from a database or config file
        universe = [
            # Tech majors
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD",
            "NFLX", "INTC", "CRM", "ADBE", "ORCL", "CSCO", "IBM", "QCOM",
            # Financials
            "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW",
            # Consumer
            "WMT", "HD", "MCD", "NKE", "SBUX", "TGT", "COST", "PG",
            # Healthcare
            "JNJ", "UNH", "PFE", "ABBV", "MRK", "TMO", "ABT", "LLY",
            # Energy
            "XOM", "CVX", "COP", "SLB", "EOG", "PSX",
            # Industrial
            "BA", "CAT", "GE", "MMM", "HON", "UPS", "RTX",
            # Other
            "DIS", "V", "MA", "PYPL", "SQ", "UBER", "SPOT"
        ]
        
        return universe
    
    def snapshot_options_chain(self, event: Dict) -> Dict[str, List[Dict]]:
        """
        Snapshot options chain for event, prev, and next expiries
        
        Args:
            event: Event dict with symbol and expiries
        
        Returns:
            Dict with 'event', 'prev', 'next' contract lists
        """
        symbol = event["symbol"]
        expiries = event["expiries"]
        
        chains = {}
        
        # Event expiry
        if expiries["event"]:
            chains["event"] = get_chain_snapshot(
                symbol,
                expiries["event"],
                expiries["event"]
            )
        else:
            chains["event"] = []
        
        # Prev expiry
        if expiries["prev"]:
            chains["prev"] = get_chain_snapshot(
                symbol,
                expiries["prev"],
                expiries["prev"]
            )
        else:
            chains["prev"] = []
        
        # Next expiry
        if expiries["next"]:
            chains["next"] = get_chain_snapshot(
                symbol,
                expiries["next"],
                expiries["next"]
            )
        else:
            chains["next"] = []
        
        return chains
    
    def upsert_contracts_to_db(self, contracts: List[Dict]) -> None:
        """
        Upsert option contracts to public.option_contracts
        
        Args:
            contracts: List of option contracts
        """
        if not contracts:
            return
        
        # Format for database
        rows = []
        seen = set()  # Track unique option symbols
        
        for contract in contracts:
            details = contract.get("details", {})
            option_symbol = contract.get("ticker")
            symbol = details.get("ticker")
            expiry = details.get("expiration_date")
            strike = details.get("strike_price")
            option_type = details.get("contract_type", "").upper()
            
            if not all([option_symbol, symbol, expiry, strike, option_type]):
                continue
            
            # Skip duplicates
            if option_symbol in seen:
                continue
            seen.add(option_symbol)
            
            # Map "CALL"/"PUT" to "C"/"P"
            option_type_code = "C" if option_type == "CALL" else "P"
            
            rows.append({
                "option_symbol": option_symbol,
                "symbol": symbol,
                "expiry": expiry,
                "strike": float(strike),
                "option_type": option_type_code
            })
        
        if rows:
            try:
                upsert_rows(
                    table="public.option_contracts",
                    rows=rows,
                    on_conflict="option_symbol"
                )
            except Exception as e:
                print(f"      Warning: Error upserting contracts: {e}")
    
    def insert_snapshots_to_db(self, contracts: List[Dict]) -> None:
        """
        Insert option snapshots to public.option_snapshots
        
        Args:
            contracts: List of option contracts
        """
        if not contracts:
            return
        
        # Format for database
        rows = []
        
        for contract in contracts:
            option_symbol = contract.get("ticker")
            
            # Extract market data
            underlying_price = contract.get("underlying_asset", {}).get("price")
            
            last_quote = contract.get("last_quote", {})
            bid = last_quote.get("bid")
            ask = last_quote.get("ask")
            
            last_trade = contract.get("last_trade", {})
            last = last_trade.get("price")
            
            iv = contract.get("implied_volatility")
            
            greeks = contract.get("greeks", {})
            delta = greeks.get("delta")
            gamma = greeks.get("gamma")
            theta = greeks.get("theta")
            vega = greeks.get("vega")
            
            day_data = contract.get("day", {})
            volume = day_data.get("volume")
            oi = contract.get("open_interest")
            
            if not option_symbol:
                continue
            
            rows.append({
                "asof_ts": self.asof_ts.isoformat(),
                "option_symbol": option_symbol,
                "underlying_px": underlying_price,
                "bid": bid,
                "ask": ask,
                "last": last,
                "iv": iv,
                "delta": delta,
                "gamma": gamma,
                "theta": theta,
                "vega": vega,
                "volume": volume,
                "oi": oi
            })
        
        if rows:
            try:
                insert_rows(table="public.option_snapshots", rows=rows)
            except Exception as e:
                print(f"      Warning: Error inserting snapshots: {e}")
    
    def compute_med20_volumes(self, symbol: str, event_date: date) -> Dict[str, float]:
        """
        Compute 20-day median volumes for calls and puts
        
        For simplicity, we'll use a heuristic based on recent market data.
        In production, this would query historical option volume data.
        
        Args:
            symbol: Stock ticker
            event_date: Event expiry date
        
        Returns:
            Dict with 'call_med20' and 'put_med20'
        """
        # TODO: Implement proper 20-day volume baseline from historical data
        # For now, use placeholder values based on underlying volume
        
        try:
            # Get recent price data to estimate volume
            end = self.trade_date
            start = end - timedelta(days=30)
            
            bars = get_underlying_agg(symbol, start, end, timespan="day")
            
            if bars:
                # Use median underlying volume as proxy
                volumes = [bar["volume"] for bar in bars if bar.get("volume")]
                if volumes:
                    median_vol = np.median(volumes)
                    # Rough estimate: option volume is ~5% of underlying volume
                    # Split 60/40 between calls and puts (slightly bullish bias)
                    call_med20 = median_vol * 0.05 * 0.6
                    put_med20 = median_vol * 0.05 * 0.4
                    
                    return {
                        "call_med20": call_med20,
                        "put_med20": put_med20
                    }
        except Exception as e:
            print(f"      Warning: Could not compute med20 volumes for {symbol}: {e}")
        
        # Fallback to default values
        return {
            "call_med20": 10000,
            "put_med20": 8000
        }
    
    def compute_signals_for_event(self, event: Dict, chains: Dict[str, List[Dict]]) -> Optional[Dict]:
        """
        Compute all signals for a single event
        
        Args:
            event: Event dict with symbol and expiry info
            chains: Dict with event/prev/next contract lists
        
        Returns:
            Dict with computed signals, or None if insufficient data
        """
        symbol = event["symbol"]
        event_date = event["expiries"]["event"]
        
        try:
            # Compute 20-day volume baseline
            med20_volumes = self.compute_med20_volumes(symbol, event_date)
            
            # Compute all signals
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
            signals["earnings_date"] = event["earnings_date"]
            
            return signals
            
        except Exception as e:
            print(f"      Error computing signals for {symbol}: {e}")
            return None
    
    def normalize_and_score(self, signals_list: List[Dict]) -> pd.DataFrame:
        """
        Normalize signals and compute scores across all events
        
        Args:
            signals_list: List of signal dicts
        
        Returns:
            DataFrame with normalized signals and scores
        """
        if not signals_list:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(signals_list)
        
        # Compute scores (includes normalization)
        df_scored = compute_scores_batch(df)
        
        return df_scored
    
    def write_signals_to_db(self, df_scored: pd.DataFrame) -> None:
        """
        Write scored signals to public.daily_signals
        
        Args:
            df_scored: DataFrame with scored signals
        """
        if df_scored.empty:
            print("   No signals to write")
            return
        
        print(f"\n5. Writing {len(df_scored)} signals to database...")
        
        # Format for database
        rows = []
        for _, row in df_scored.iterrows():
            rows.append({
                "trade_date": self.trade_date.isoformat(),
                "symbol": row["symbol"],
                "event_expiry": row.get("event_date").isoformat() if pd.notna(row.get("event_date")) else None,
                "rr_25d": float(row["rr_25d"]) if pd.notna(row.get("rr_25d")) else None,
                "pcr_volume": float(row["vol_pcr"]) if pd.notna(row.get("vol_pcr")) else None,
                "pcr_notional": float(row["notional_pcr"]) if pd.notna(row.get("notional_pcr")) else None,
                "vol_thrust_calls": float(row["call_thrust"]) if pd.notna(row.get("call_thrust")) else None,
                "vol_thrust_puts": float(row["put_thrust"]) if pd.notna(row.get("put_thrust")) else None,
                "atm_iv_event": float(row["atm_iv_event"]) if pd.notna(row.get("atm_iv_event")) else None,
                "atm_iv_prev": float(row["atm_iv_prev"]) if pd.notna(row.get("atm_iv_prev")) else None,
                "atm_iv_next": float(row["atm_iv_next"]) if pd.notna(row.get("atm_iv_next")) else None,
                "iv_bump": float(row["iv_bump"]) if pd.notna(row.get("iv_bump")) else None,
                "spread_pct_atm": float(row["spread_pct_atm"]) if pd.notna(row.get("spread_pct_atm")) else None,
                "mom_3d_betaadj": float(row["beta_adj_return"]) if pd.notna(row.get("beta_adj_return")) else None,
                "dirscore": float(row["score"]) if pd.notna(row.get("score")) else None,
                "decision": row.get("decision")
            })
        
        try:
            upsert_rows(
                table="public.daily_signals",
                rows=rows,
                on_conflict="trade_date,symbol"
            )
            print(f"   ✓ Wrote {len(rows)} signals to database")
        except Exception as e:
            print(f"   ✗ Error writing signals: {e}")
            raise
    
    def export_predictions_csv(self, df_scored: pd.DataFrame) -> None:
        """
        Export predictions to /out/predictions_YYYYMMDD.csv
        
        Args:
            df_scored: DataFrame with scored signals
        """
        if df_scored.empty:
            print("   No predictions to export")
            return
        
        print(f"\n6. Exporting predictions to CSV...")
        
        # Select and format columns for export
        export_cols = [
            "symbol",
            "earnings_date",
            "event_date",
            "score",
            "decision",
            "rr_25d",
            "vol_pcr",
            "notional_pcr",
            "net_thrust",
            "iv_bump",
            "spread_pct_atm",
            "beta_adj_return",
            "atm_iv_event"
        ]
        
        # Filter to columns that exist
        export_cols = [col for col in export_cols if col in df_scored.columns]
        
        df_export = df_scored[export_cols].copy()
        
        # Sort by absolute score
        df_export["abs_score"] = df_export["score"].abs()
        df_export = df_export.sort_values("abs_score", ascending=False)
        df_export = df_export.drop("abs_score", axis=1)
        
        # Generate filename
        filename = config.OUT_DIR / f"predictions_{self.trade_date.strftime('%Y%m%d')}.csv"
        
        # Save to CSV
        df_export.to_csv(filename, index=False, float_format="%.4f")
        
        print(f"   ✓ Exported to: {filename}")
        
        # Print summary
        print(f"\n   Summary:")
        print(f"   - Total predictions: {len(df_export)}")
        print(f"   - CALL signals: {len(df_export[df_export['decision'] == 'CALL'])}")
        print(f"   - PUT signals: {len(df_export[df_export['decision'] == 'PUT'])}")
        print(f"   - PASS_OR_SPREAD: {len(df_export[df_export['decision'] == 'PASS_OR_SPREAD'])}")
    
    def run(self) -> pd.DataFrame:
        """
        Run the complete post-close job
        
        Returns:
            DataFrame with scored predictions
        """
        
        # Step 1: Load earnings events use the same as intraday trading
        print("\n1. Loading earnings events (today after-close + tomorrow)...")
        try:
            earnings_events = get_earnings_events(self.trade_date)
        except Exception as exc:  # pragma: no cover - external API/db
            print(f"   ✗ Failed to load earnings events: {exc}")
            return pd.DataFrame()
        if earnings_events.empty:
            print("   ✗ No earnings events found")
            return pd.DataFrame()
        
        print(f"   ✓ Found {len(earnings_events)} earnings events")
        
        # Step 2: Enrich with expiries
        print("\n2. Enriching events with option expiries...")
        enriched_events = []
        
        for _, row in earnings_events.iterrows():
            symbol = row["symbol"]
            earnings_ts = row["earnings_ts"]
            earnings_date = row["earnings_date"]
            
            try:
                # Get available expiries for this symbol
                expiries = get_expiries(symbol)
                
                if not expiries:
                    print(f"   - {symbol}: No expiries found, skipping")
                    continue
                
                # Find event and neighbor expiries
                expiry_dates = find_event_and_neighbors(earnings_ts, expiries)
                
                if not expiry_dates["event"]:
                    print(f"   - {symbol}: No valid event expiry, skipping")
                    continue
                
                # Build enriched event dict
                event = {
                    "symbol": symbol,
                    "earnings_ts": earnings_ts,
                    "earnings_date": earnings_date,
                    "expiries": expiry_dates
                }
                enriched_events.append(event)
                
            except Exception as e:
                print(f"   - {symbol}: Error getting expiries: {e}")
                continue
        
        if not enriched_events:
            print("   ✗ No events with valid expiries found")
            return pd.DataFrame()
        
        print(f"   ✓ Enriched {len(enriched_events)} events with expiries")
        
        # Step 3: Process each event
        print(f"\n3. Processing {len(enriched_events)} events...")
        
        signals_list = []
        
        for i, event in enumerate(enriched_events, 1):
            symbol = event["symbol"]
            print(f"\n   [{i}/{len(enriched_events)}] Processing {symbol}...")
            
            try:
                # Snapshot options chain
                chains = self.snapshot_options_chain(event)
                
                # Count contracts
                total_contracts = len(chains["event"]) + len(chains["prev"]) + len(chains["next"])
                print(f"      Fetched {total_contracts} contracts")
                
                # Upsert contracts to database
                all_contracts = chains["event"] + chains["prev"] + chains["next"]
                self.upsert_contracts_to_db(all_contracts)
                
                # Insert snapshots to database
                self.insert_snapshots_to_db(all_contracts)
                
                # Compute signals
                signals = self.compute_signals_for_event(event, chains)
                
                if signals:
                    signals_list.append(signals)
                    print(f"      ✓ Computed signals")
                else:
                    print(f"      ✗ Could not compute signals")
                
            except Exception as e:
                print(f"      ✗ Error processing {symbol}: {e}")
                continue
        
        # Step 4: Normalize and score
        print(f"\n4. Normalizing and scoring {len(signals_list)} signals...")
        
        df_scored = self.normalize_and_score(signals_list)
        
        if df_scored.empty:
            print("   No signals to score. Exiting.")
            return df_scored
        
        print(f"   ✓ Scored {len(df_scored)} events")
        
        # Step 5: Write to database
        self.write_signals_to_db(df_scored)
        
        # Step 6: Export predictions CSV
        self.export_predictions_csv(df_scored)
        
        print("\n" + "=" * 70)
        print("POST-CLOSE JOB COMPLETE")
        print("=" * 70)
        
        return df_scored


def main():
    """Main entry point"""
    # Allow specifying trade date as command line argument
    import argparse
    
    parser = argparse.ArgumentParser(description="Post-close job for option research")
    parser.add_argument(
        "--date",
        type=str,
        help="Trade date (YYYY-MM-DD). Defaults to today.",
        default=None
    )
    parser.add_argument(
        "--days-ahead",
        type=int,
        choices=[0, 1],
        help="Days to look ahead for earnings: 0=today only, 1=today+tomorrow (default: 1)",
        default=1
    )
    
    args = parser.parse_args()
    
    # Parse trade date
    trade_date = None
    if args.date:
        try:
            trade_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format: {args.date}")
            print("Expected format: YYYY-MM-DD")
            sys.exit(1)
    
    # Run job
    job = PostCloseJob(trade_date=trade_date, days_ahead=args.days_ahead)
    df_scored = job.run()
    
    # Display top opportunities
    if not df_scored.empty:
        print("\nTop 10 Opportunities:")
        top_10 = df_scored.nlargest(10, "score", keep="all")[
            ["symbol", "score", "decision", "earnings_date", "rr_25d", "vol_pcr", "iv_bump"]
        ]
        print(top_10.to_string(index=False))


if __name__ == "__main__":
    main()
