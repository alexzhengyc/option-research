"""
Polygon.io API client for options data
"""
import os
import requests
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class PolygonClient:
    """Client for fetching options data from Polygon.io"""
    
    BASE_URL = "https://api.polygon.io"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Polygon client
        
        Args:
            api_key: Polygon API key (defaults to POLYGON_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("POLYGON_API_KEY")
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY must be provided or set in environment")
        
        self.session = requests.Session()
        self.session.params = {"apiKey": self.api_key}
    
    def get_options_chain(
        self,
        underlying_ticker: str,
        expiration_date: Optional[date] = None,
        strike_price: Optional[float] = None,
        contract_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get options chain for a ticker
        
        Args:
            underlying_ticker: Stock ticker symbol
            expiration_date: Filter by expiration date
            strike_price: Filter by strike price
            contract_type: Filter by contract type ('call' or 'put')
            
        Returns:
            List of option contracts
        """
        url = f"{self.BASE_URL}/v3/reference/options/contracts"
        
        params = {
            "underlying_ticker": underlying_ticker,
            "limit": 1000,
        }
        
        if expiration_date:
            params["expiration_date"] = expiration_date.isoformat()
        if strike_price:
            params["strike_price"] = strike_price
        if contract_type:
            params["contract_type"] = contract_type
            
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        return data.get("results", [])
    
    def get_option_quote(self, option_ticker: str) -> Dict:
        """
        Get real-time quote for an option contract
        
        Args:
            option_ticker: Option ticker symbol (e.g., 'O:SPY251219C00550000')
            
        Returns:
            Option quote data
        """
        url = f"{self.BASE_URL}/v3/quotes/{option_ticker}"
        
        response = self.session.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def get_snapshot(
        self, 
        underlying_ticker: str,
        expiration_date: Optional[date] = None,
        strike_price: Optional[float] = None,
        contract_type: Optional[str] = None,
        limit: int = 250
    ) -> Dict:
        """
        Get options snapshot for a ticker
        
        Args:
            underlying_ticker: Stock ticker symbol
            expiration_date: Filter by expiration date (YYYY-MM-DD)
            strike_price: Filter by strike price
            contract_type: Filter by contract type ('call' or 'put')
            limit: Number of results to return (max 250)
            
        Returns:
            Snapshot data with options chain
        """
        url = f"{self.BASE_URL}/v3/snapshot/options/{underlying_ticker}"
        
        params = {"limit": limit}
        
        if expiration_date:
            params["expiration_date"] = expiration_date.isoformat()
        if strike_price:
            params["strike_price"] = strike_price
        if contract_type:
            params["contract_type"] = contract_type
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_snapshot_paginated(
        self,
        underlying_ticker: str,
        expiration_date: Optional[date] = None,
        strike_price: Optional[float] = None,
        contract_type: Optional[str] = None,
        max_results: int = 1000
    ) -> List[Dict]:
        """
        Get options snapshot with pagination support
        
        Args:
            underlying_ticker: Stock ticker symbol
            expiration_date: Filter by expiration date
            strike_price: Filter by strike price
            contract_type: Filter by contract type ('call' or 'put')
            max_results: Maximum number of total results to fetch
            
        Returns:
            List of all option contracts
        """
        all_results = []
        next_url = None
        
        while len(all_results) < max_results:
            if next_url:
                # Use next_url for pagination
                response = self.session.get(next_url)
                response.raise_for_status()
                data = response.json()
            else:
                # First request
                data = self.get_snapshot(
                    underlying_ticker,
                    expiration_date=expiration_date,
                    strike_price=strike_price,
                    contract_type=contract_type,
                    limit=min(250, max_results - len(all_results))
                )
            
            results = data.get("results", [])
            if not results:
                break
            
            all_results.extend(results)
            
            # Check for next page
            next_url = data.get("next_url")
            if not next_url:
                break
        
        return all_results[:max_results]


def get_expiries(symbol: str) -> List[date]:
    """
    Get all available expiration dates for a symbol's options
    
    Args:
        symbol: Stock ticker symbol
    
    Returns:
        List of expiration dates, sorted ascending
    """
    client = PolygonClient()
    
    # Get all option contracts for this symbol
    contracts = client.get_options_chain(underlying_ticker=symbol)
    
    # Extract unique expiration dates
    expiries = set()
    for contract in contracts:
        exp_date = contract.get("expiration_date")
        if exp_date:
            try:
                # Parse the date string (format: "YYYY-MM-DD")
                expiry = datetime.strptime(exp_date, "%Y-%m-%d").date()
                expiries.add(expiry)
            except (ValueError, TypeError):
                continue
    
    # Return sorted list
    return sorted(list(expiries))


def get_chain_snapshot(
    symbol: str,
    start_expiry: date,
    end_expiry: date
) -> List[Dict]:
    """
    Get options chain snapshot filtered to event + neighboring expiries
    
    Uses Polygon's Option Chain Snapshot API with expiration_date filtering
    to fetch all contracts for specific expiry dates with market data.
    
    Args:
        symbol: Stock ticker symbol
        start_expiry: Earliest expiration date to include
        end_expiry: Latest expiration date to include
    
    Returns:
        List of option contracts with current market data
        Each dict contains contract details and snapshot data:
        {
            "ticker": "O:SPY251219C00550000",
            "underlying_asset": {"ticker": "SPY", "price": 550.0, ...},
            "details": {
                "ticker": "SPY",
                "strike_price": 550.0,
                "expiration_date": "2025-12-19",
                "contract_type": "call",
                ...
            },
            "last_quote": {"bid": 5.0, "ask": 5.1, ...},
            "last_trade": {"price": 5.05, ...},
            "greeks": {"delta": 0.5, "gamma": 0.1, ...},
            "implied_volatility": 0.25,
            "open_interest": 1000,
            "day": {"volume": 250, ...},
            ...
        }
    """
    client = PolygonClient()
    
    # If start and end are the same, fetch single expiry
    if start_expiry == end_expiry:
        try:
            contracts = client.get_snapshot_paginated(
                underlying_ticker=symbol,
                expiration_date=start_expiry,
                max_results=500  # Get more contracts for single expiry
            )
            return contracts
        except Exception as e:
            print(f"      Warning: Could not fetch contracts for {symbol} expiry {start_expiry}: {e}")
            return []
    
    # For multiple expiries, fetch each separately and combine
    all_contracts = []
    
    # Build list of unique expiry dates to fetch
    expiries_to_fetch = set()
    expiries_to_fetch.add(start_expiry)
    expiries_to_fetch.add(end_expiry)
    
    # Also check for any Friday dates in between (weekly options)
    current = start_expiry
    while current <= end_expiry:
        if current.weekday() == 4:  # Friday
            expiries_to_fetch.add(current)
        current += timedelta(days=1)
    
    # Fetch contracts for each unique expiry
    for expiry in sorted(expiries_to_fetch):
        try:
            contracts = client.get_snapshot_paginated(
                underlying_ticker=symbol,
                expiration_date=expiry,
                max_results=500  # Limit per expiry
            )
            
            if contracts:
                print(f"      Fetched {len(contracts)} contracts for {expiry}")
                all_contracts.extend(contracts)
            
        except Exception as e:
            print(f"      Warning: Could not fetch contracts for {symbol} expiry {expiry}: {e}")
            continue
    
    return all_contracts


def get_underlying_agg(
    symbol: str,
    start: date,
    end: date,
    timespan: str = "day"
) -> List[Dict]:
    """
    Get aggregated bars for the underlying stock
    
    Args:
        symbol: Stock ticker symbol
        start: Start date
        end: End date
        timespan: Bar timespan ("minute", "hour", "day", "week", "month")
    
    Returns:
        List of OHLCV bars:
        [
            {
                "timestamp": 1634169600000,  # Unix ms
                "open": 150.0,
                "high": 152.0,
                "low": 149.5,
                "close": 151.5,
                "volume": 1000000,
                "vwap": 151.0,
                "transactions": 5000
            },
            ...
        ]
    """
    client = PolygonClient()
    
    # Convert dates to required format
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    
    # Build the URL for aggregates endpoint
    url = f"{client.BASE_URL}/v2/aggs/ticker/{symbol}/range/1/{timespan}/{start_str}/{end_str}"
    
    # Make the request
    response = client.session.get(url, params={"adjusted": "true", "sort": "asc"})
    response.raise_for_status()
    
    data = response.json()
    results = data.get("results", [])
    
    # Format the results
    bars = []
    for bar in results:
        bars.append({
            "timestamp": bar.get("t"),  # Unix timestamp in milliseconds
            "open": bar.get("o"),
            "high": bar.get("h"),
            "low": bar.get("l"),
            "close": bar.get("c"),
            "volume": bar.get("v"),
            "vwap": bar.get("vw"),
            "transactions": bar.get("n")
        })
    
    return bars


def get_option_daily_oc(
    option_ticker: str,
    date: date
) -> Optional[Dict]:
    """
    Get daily open/close data for an option contract (for 20-day volume baselines)
    
    Args:
        option_ticker: Option ticker (e.g., "O:SPY251219C00550000")
        date: Date to get data for
    
    Returns:
        Dict with daily OHLCV data or None if not available:
        {
            "date": "2025-10-15",
            "open": 5.50,
            "high": 5.75,
            "low": 5.40,
            "close": 5.65,
            "volume": 1250,
            "open_interest": 5000,
            "implied_volatility": 0.25
        }
    """
    client = PolygonClient()
    
    # Build URL for daily open/close endpoint
    date_str = date.strftime("%Y-%m-%d")
    url = f"{client.BASE_URL}/v1/open-close/{option_ticker}/{date_str}"
    
    try:
        response = client.session.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if we got valid data
        if data.get("status") != "OK":
            return None
        
        return {
            "date": date_str,
            "open": data.get("open"),
            "high": data.get("high"),
            "low": data.get("low"),
            "close": data.get("close"),
            "volume": data.get("volume"),
            "open_interest": data.get("openInterest"),
            "implied_volatility": data.get("impliedVolatility")
        }
    except Exception as e:
        # Return None if data is not available
        print(f"Warning: Could not fetch daily data for {option_ticker} on {date_str}: {e}")
        return None

