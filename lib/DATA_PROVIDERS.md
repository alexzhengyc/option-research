# Data Provider Functions

This document describes the data provider functions for fetching earnings and options data from Finnhub and Polygon.io.

## Installation

Ensure you have the required API keys set in your environment:

```bash
export FINNHUB_API_KEY="your_finnhub_key"
export POLYGON_API_KEY="your_polygon_key"
```

## Finnhub Provider (`lib.finnhub`)

### `get_upcoming_earnings(symbols, start, end)`

Get upcoming earnings dates for a list of symbols.

**Parameters:**
- `symbols` (List[str]): List of stock ticker symbols
- `start` (date): Start date for earnings search
- `end` (date): End date for earnings search

**Returns:**
List of dicts with format:
```python
[
    {
        "symbol": "AAPL",
        "earnings_ts": datetime(2025, 10, 26, 16, 30)  # earnings datetime
    },
    ...
]
```

**Example:**
```python
from datetime import date, timedelta
from lib import get_upcoming_earnings

symbols = ["AAPL", "MSFT", "GOOGL"]
start = date.today()
end = start + timedelta(days=30)

earnings = get_upcoming_earnings(symbols, start, end)
for event in earnings:
    print(f"{event['symbol']}: {event['earnings_ts']}")
```

## Polygon Provider (`lib.polygon`)

### `get_expiries(symbol)`

Get all available expiration dates for a symbol's options.

**Parameters:**
- `symbol` (str): Stock ticker symbol

**Returns:**
List of expiration dates (sorted ascending)

**Example:**
```python
from lib import get_expiries

expiries = get_expiries("SPY")
print(f"Found {len(expiries)} expiration dates")
print(f"Next expiry: {expiries[0]}")
```

### `get_chain_snapshot(symbol, start_expiry, end_expiry)`

Get options chain snapshot filtered to event + neighboring expiries.

**Parameters:**
- `symbol` (str): Stock ticker symbol
- `start_expiry` (date): Earliest expiration date to include
- `end_expiry` (date): Latest expiration date to include

**Returns:**
List of option contracts with current market data. Each dict contains:
```python
{
    "ticker": "O:SPY251219C00550000",
    "underlying_ticker": "SPY",
    "details": {
        "strike": 550.0,
        "expiration_date": "2025-12-19",
        "contract_type": "call",
        ...
    },
    "last_quote": {...},
    "last_trade": {...},
    "greeks": {...},
    "implied_volatility": 0.25,
    "open_interest": 1000,
    "volume": 250,
    ...
}
```

**Example:**
```python
from datetime import date, timedelta
from lib import get_chain_snapshot

symbol = "SPY"
start_expiry = date.today()
end_expiry = start_expiry + timedelta(days=60)

contracts = get_chain_snapshot(symbol, start_expiry, end_expiry)
print(f"Found {len(contracts)} contracts")

# Filter to high IV contracts
high_iv = [c for c in contracts if c.get("implied_volatility", 0) > 0.30]
print(f"High IV contracts: {len(high_iv)}")
```

### `get_underlying_agg(symbol, start, end, timespan="day")`

Get aggregated bars for the underlying stock.

**Parameters:**
- `symbol` (str): Stock ticker symbol
- `start` (date): Start date
- `end` (date): End date
- `timespan` (str): Bar timespan - "minute", "hour", "day", "week", "month" (default: "day")

**Returns:**
List of OHLCV bars:
```python
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
```

**Example:**
```python
from datetime import date, timedelta
from lib import get_underlying_agg

symbol = "SPY"
end = date.today()
start = end - timedelta(days=30)

bars = get_underlying_agg(symbol, start, end, timespan="day")

# Calculate 20-day moving average
closes = [bar["close"] for bar in bars]
ma20 = sum(closes[-20:]) / 20
print(f"20-day MA: ${ma20:.2f}")
```

### `get_option_daily_oc(option_ticker, date)` [Optional]

Get daily open/close data for an option contract (for 20-day volume baselines).

**Parameters:**
- `option_ticker` (str): Option ticker (e.g., "O:SPY251219C00550000")
- `date` (date): Date to get data for

**Returns:**
Dict with daily OHLCV data or None if not available:
```python
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
```

**Example:**
```python
from datetime import date, timedelta
from lib import get_option_daily_oc

option_ticker = "O:SPY251219C00550000"

# Get 20 days of volume data
volumes = []
for i in range(20):
    target_date = date.today() - timedelta(days=i)
    data = get_option_daily_oc(option_ticker, target_date)
    if data and data["volume"]:
        volumes.append(data["volume"])

if volumes:
    avg_volume = sum(volumes) / len(volumes)
    print(f"20-day avg volume: {avg_volume:.0f}")
```

## Full Pipeline Example

```python
from datetime import date, timedelta
from lib import (
    get_upcoming_earnings,
    get_expiries,
    get_chain_snapshot,
    get_underlying_agg
)

# 1. Find earnings events
symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]
start = date.today()
end = start + timedelta(days=14)

earnings = get_upcoming_earnings(symbols, start, end)
print(f"Found {len(earnings)} earnings events")

# 2. For each earnings event, find neighboring expiries
for event in earnings:
    symbol = event["symbol"]
    earnings_date = event["earnings_ts"].date()
    
    # Get available expiries
    expiries = get_expiries(symbol)
    
    # Filter to expiries around earnings
    before = [e for e in expiries if e < earnings_date]
    after = [e for e in expiries if e >= earnings_date]
    
    if not before or not after:
        continue
    
    closest_before = before[-1]  # Last expiry before earnings
    closest_after = after[0]      # First expiry after earnings
    
    print(f"\n{symbol} earnings on {earnings_date}")
    print(f"  Expiry before: {closest_before}")
    print(f"  Expiry after: {closest_after}")
    
    # 3. Get options chain for these expiries
    start_expiry = closest_before
    end_expiry = after[1] if len(after) > 1 else closest_after
    
    contracts = get_chain_snapshot(symbol, start_expiry, end_expiry)
    print(f"  Found {len(contracts)} option contracts")
    
    # 4. Get underlying price data for context
    hist_start = earnings_date - timedelta(days=30)
    bars = get_underlying_agg(symbol, hist_start, earnings_date)
    
    if bars:
        current_price = bars[-1]["close"]
        print(f"  Current price: ${current_price:.2f}")
        
        # Filter to near-the-money options
        atm_contracts = [
            c for c in contracts 
            if abs(c.get("details", {}).get("strike", 0) - current_price) / current_price < 0.10
        ]
        print(f"  ATM contracts (±10%): {len(atm_contracts)}")
```

## Error Handling

All functions handle API errors gracefully:

- Missing data returns empty lists or None
- Invalid dates are skipped with warnings
- API errors are caught and logged

For production use, consider adding retries and rate limiting.

