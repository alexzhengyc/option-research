"""
Finnhub API client for earnings dates and company data
"""
import os
import finnhub
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class FinnhubClient:
    """Client for fetching earnings dates and company fundamentals from Finnhub"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Finnhub client
        
        Args:
            api_key: Finnhub API key (defaults to FINNHUB_API_KEY env var)
        """
        api_key = api_key or os.getenv("FINNHUB_API_KEY")
        if not api_key:
            raise ValueError("FINNHUB_API_KEY must be provided or set in environment")
        
        self.client = finnhub.Client(api_key=api_key)
    
    def get_earnings_calendar(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        symbol: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get earnings calendar
        
        Args:
            start_date: Start date for earnings (defaults to today)
            end_date: End date for earnings (defaults to 30 days from start)
            symbol: Filter by specific symbol
            
        Returns:
            List of earnings events
        """
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = start_date + timedelta(days=30)
        
        # Note: Using '_from' as the API parameter name
        from_date = start_date.isoformat()
        to_date = end_date.isoformat()
        
        # Finnhub API requires symbol parameter - use empty string for all earnings
        symbol_param = symbol if symbol else ""
        result = self.client.earnings_calendar(_from=from_date, to=to_date, symbol=symbol_param)
        return result.get("earningsCalendar", [])
    
    def get_company_profile(self, symbol: str) -> Dict:
        """
        Get company profile
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Company profile data
        """
        return self.client.company_profile2(symbol=symbol)
    
    def get_basic_financials(self, symbol: str) -> Dict:
        """
        Get basic financial metrics
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Financial metrics
        """
        return self.client.company_basic_financials(symbol, "all")


def get_upcoming_earnings(
    symbols: List[str], 
    start: date, 
    end: date
) -> List[Dict[str, any]]:
    """
    Get upcoming earnings dates for a list of symbols
    
    Args:
        symbols: List of stock ticker symbols
        start: Start date for earnings search
        end: End date for earnings search
    
    Returns:
        List of dicts with format:
        [
            {
                "symbol": "AAPL",
                "earnings_ts": datetime(2025, 10, 26, 16, 30)  # earnings datetime
            },
            ...
        ]
    """
    client = FinnhubClient()
    
    # Get earnings calendar for the date range
    earnings_calendar = client.get_earnings_calendar(
        start_date=start,
        end_date=end
    )
    
    # Filter to requested symbols and format output
    results = []
    symbol_set = set(symbols)
    
    for event in earnings_calendar:
        symbol = event.get("symbol")
        if symbol not in symbol_set:
            continue
        
        # Get earnings date and time
        earnings_date = event.get("date")  # Format: "YYYY-MM-DD"
        earnings_time = event.get("hour")  # Format: "bmo", "amc", or specific time
        
        if not earnings_date:
            continue
        
        # Parse the date
        try:
            dt = datetime.strptime(earnings_date, "%Y-%m-%d")
            
            # Adjust time based on hour field
            if earnings_time == "bmo":  # Before market open
                dt = dt.replace(hour=9, minute=0)
            elif earnings_time == "amc":  # After market close
                dt = dt.replace(hour=16, minute=0)
            elif earnings_time:
                # Try to parse specific time if provided
                try:
                    # Format could be "16:00" or similar
                    time_parts = earnings_time.split(":")
                    if len(time_parts) >= 2:
                        dt = dt.replace(
                            hour=int(time_parts[0]),
                            minute=int(time_parts[1])
                        )
                except (ValueError, AttributeError):
                    # Default to after market close if parsing fails
                    dt = dt.replace(hour=16, minute=0)
            else:
                # Default to after market close
                dt = dt.replace(hour=16, minute=0)
            
            results.append({
                "symbol": symbol,
                "earnings_ts": dt
            })
        except (ValueError, TypeError) as e:
            # Skip events with invalid dates
            print(f"Warning: Could not parse earnings date for {symbol}: {earnings_date} - {e}")
            continue
    
    return results

