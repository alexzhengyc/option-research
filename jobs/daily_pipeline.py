"""
Daily pipeline for computing directional scores and generating watchlists
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from typing import List, Dict, Optional

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))

from finnhub_client import FinnhubClient
from polygon_client import PolygonClient
from supabase_client import SupabaseClient
from scoring import DirectionalScorer, DirectionalScore
import config


class DailyPipeline:
    """Daily pipeline for options research"""
    
    def __init__(self):
        """Initialize pipeline with API clients"""
        self.finnhub = FinnhubClient()
        self.polygon = PolygonClient()
        self.supabase = SupabaseClient()
        self.scorer = DirectionalScorer()
        
    def get_upcoming_earnings(
        self,
        days_ahead: int = 7
    ) -> pd.DataFrame:
        """
        Get tickers with earnings in the next N days
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            DataFrame with ticker, date, and time
        """
        start_date = date.today()
        end_date = start_date + timedelta(days=days_ahead)
        
        earnings = self.finnhub.get_earnings_calendar(
            start_date=start_date,
            end_date=end_date
        )
        
        if not earnings:
            return pd.DataFrame()
        
        df = pd.DataFrame(earnings)
        df = df[['symbol', 'date', 'hour']].rename(columns={'symbol': 'ticker'})
        
        return df
    
    def compute_ticker_score(
        self,
        ticker: str,
        earnings_date: date
    ) -> Optional[DirectionalScore]:
        """
        Compute directional score for a single ticker
        
        Args:
            ticker: Stock ticker symbol
            earnings_date: Date of earnings announcement
            
        Returns:
            DirectionalScore or None if insufficient data
        """
        try:
            # TODO: Implement actual data fetching and signal computation
            # This is a placeholder that returns mock scores
            
            # In real implementation:
            # 1. Fetch options chain from Polygon
            # 2. Compute RR, PCR, OI changes, volume changes
            # 3. Fetch price data and compute momentum
            # 4. Get historical data for z-scores and percentiles
            # 5. Compute each signal component (D1-D5, P1-P2)
            
            # Mock signals for now
            d1 = np.random.randn()
            d2 = np.random.randn()
            d3 = np.random.randn()
            d4 = np.random.randn()
            d5 = np.random.uniform(-2, 2)
            p1 = np.random.uniform(0, 2)
            p2 = np.random.uniform(0, 2)
            
            score = self.scorer.compute_score(
                ticker=ticker,
                d1=d1,
                d2=d2,
                d3=d3,
                d4=d4,
                d5=d5,
                p1=p1,
                p2=p2,
            )
            
            return score
            
        except Exception as e:
            print(f"Error computing score for {ticker}: {e}")
            return None
    
    def generate_watchlist(
        self,
        scores: List[DirectionalScore],
        min_conviction: str = 'MEDIUM'
    ) -> pd.DataFrame:
        """
        Generate watchlist from scores
        
        Args:
            scores: List of DirectionalScore objects
            min_conviction: Minimum conviction level ('HIGH', 'MEDIUM', 'LOW')
            
        Returns:
            DataFrame with ranked opportunities
        """
        # Convert to DataFrame
        data = []
        for s in scores:
            if s.structure == 'SKIP':
                continue
            
            # Filter by conviction
            if min_conviction == 'HIGH' and s.conviction != 'HIGH':
                continue
            elif min_conviction == 'MEDIUM' and s.conviction == 'LOW':
                continue
            
            data.append({
                'ticker': s.ticker,
                'dir_score': s.dir_score,
                'direction': s.direction,
                'conviction': s.conviction,
                'structure': s.structure,
                'd1_skew': s.d1_skew,
                'd2_flow': s.d2_flow,
                'd3_pcr': s.d3_pcr,
                'd4_momentum': s.d4_momentum,
                'd5_consistency': s.d5_consistency,
                'p1_iv_cost': s.p1_iv_cost,
                'p2_spread': s.p2_spread,
            })
        
        df = pd.DataFrame(data)
        
        if df.empty:
            return df
        
        # Sort by absolute score (highest conviction first)
        df['abs_score'] = df['dir_score'].abs()
        df = df.sort_values('abs_score', ascending=False)
        df = df.drop('abs_score', axis=1)
        
        return df
    
    def run(self, output_file: Optional[str] = None) -> pd.DataFrame:
        """
        Run the daily pipeline
        
        Args:
            output_file: Optional path to save CSV output
            
        Returns:
            DataFrame with watchlist
        """
        print("Starting daily pipeline...")
        print(f"Date: {date.today()}")
        
        # Get upcoming earnings
        print("\n1. Fetching upcoming earnings...")
        earnings_df = self.get_upcoming_earnings(days_ahead=7)
        
        if earnings_df.empty:
            print("No earnings found in the next 7 days")
            return pd.DataFrame()
        
        print(f"Found {len(earnings_df)} earnings announcements")
        
        # Compute scores for each ticker
        print("\n2. Computing directional scores...")
        scores = []
        
        for _, row in earnings_df.iterrows():
            ticker = row['ticker']
            earnings_date = pd.to_datetime(row['date']).date()
            
            print(f"  Processing {ticker} (earnings: {earnings_date})...")
            score = self.compute_ticker_score(ticker, earnings_date)
            
            if score:
                scores.append(score)
        
        print(f"Computed scores for {len(scores)} tickers")
        
        # Generate watchlist
        print("\n3. Generating watchlist...")
        watchlist = self.generate_watchlist(scores, min_conviction='MEDIUM')
        
        if watchlist.empty:
            print("No tradeable opportunities found")
            return watchlist
        
        print(f"\nWatchlist Summary:")
        print(f"  Total opportunities: {len(watchlist)}")
        print(f"  Calls: {len(watchlist[watchlist['direction'] == 'CALL'])}")
        print(f"  Puts: {len(watchlist[watchlist['direction'] == 'PUT'])}")
        print(f"  High conviction: {len(watchlist[watchlist['conviction'] == 'HIGH'])}")
        
        # Save to file
        if output_file is None:
            output_file = config.OUT_DIR / f"watchlist_{date.today().strftime('%Y%m%d')}.csv"
        
        watchlist.to_csv(output_file, index=False)
        print(f"\nWatchlist saved to: {output_file}")
        
        return watchlist


def main():
    """Main entry point"""
    pipeline = DailyPipeline()
    watchlist = pipeline.run()
    
    if not watchlist.empty:
        print("\nTop 10 Opportunities:")
        print(watchlist.head(10).to_string(index=False))


if __name__ == "__main__":
    main()

