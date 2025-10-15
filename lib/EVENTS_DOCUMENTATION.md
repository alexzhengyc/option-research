# Event and Expiry Selection Documentation

This module provides functions for selecting option expiration dates around earnings events.

## Core Concept

For earnings-based option strategies, we need to identify three key expiries:

1. **Event Expiry** - The first expiry >= earnings date (captures the event)
2. **Prev Expiry** - The expiry immediately before the event (for comparison/baseline)
3. **Next Expiry** - The expiry immediately after the event (for spreads/roll strategies)

## Functions

### `find_event_and_neighbors(earnings_ts, expiries)`

Find the event expiry and its neighbors for an earnings event.

**Parameters:**
- `earnings_ts` (datetime): Earnings datetime with time component
- `expiries` (List[date]): List of available option expiration dates

**Returns:**
```python
{
    "event": date or None,  # First expiry >= earnings date
    "prev": date or None,   # Nearest expiry before event
    "next": date or None    # Nearest expiry after event
}
```

**Example:**
```python
from datetime import datetime, date
from lib import find_event_and_neighbors

earnings = datetime(2025, 10, 26, 16, 0)  # Oct 26 after market close
expiries = [
    date(2025, 10, 18),
    date(2025, 10, 25),
    date(2025, 11, 1),
    date(2025, 11, 15)
]

result = find_event_and_neighbors(earnings, expiries)
# Result:
# {
#     "event": date(2025, 11, 1),   # First expiry after earnings
#     "prev": date(2025, 10, 25),   # Expiry before earnings
#     "next": date(2025, 11, 15)    # Expiry after event
# }
```

---

### `validate_event_expiries(event, prev, next, earnings_date, ...)`

Validate that selected expiries meet strategy requirements.

**Parameters:**
- `event` (date | None): Event expiry date
- `prev` (date | None): Previous expiry date
- `next` (date | None): Next expiry date
- `earnings_date` (date): Earnings date
- `min_prev_dte` (int): Minimum days to expiry for prev (default: 0)
- `max_event_dte` (int): Maximum days to expiry for event (default: 90)
- `min_next_dte` (int): Minimum days after event for next (default: 7)

**Returns:**
```python
{
    "has_event": bool,      # Event expiry exists
    "has_prev": bool,       # Prev expiry exists
    "has_next": bool,       # Next expiry exists
    "event_dte_ok": bool,   # Event DTE within limits
    "prev_dte_ok": bool,    # Prev DTE within limits
    "next_dte_ok": bool,    # Next gap within limits
    "is_valid": bool        # Overall validity (has event + event_dte_ok)
}
```

**Example:**
```python
from datetime import date
from lib import validate_event_expiries

earnings_date = date(2025, 10, 26)
event = date(2025, 11, 1)      # 6 days after
prev = date(2025, 10, 25)      # 1 day before
next_exp = date(2025, 11, 8)   # 7 days after event

validation = validate_event_expiries(
    event, prev, next_exp, earnings_date,
    max_event_dte=60  # Event must be within 60 days
)

if validation["is_valid"]:
    print("✓ Valid for trading")
    if validation["has_prev"] and validation["has_next"]:
        print("✓ Can use calendar spreads")
```

---

### `get_expiry_ranges(event, prev, next)`

Get date ranges for each expiry period for data fetching.

**Parameters:**
- `event` (date): Event expiry date
- `prev` (date | None): Previous expiry date (optional)
- `next` (date | None): Next expiry date (optional)

**Returns:**
```python
{
    "prev": (start_date, end_date) or None,
    "event": (start_date, end_date),
    "next": (start_date, end_date) or None
}
```

These ranges represent the trading periods for each expiry and help determine what historical data to fetch.

**Example:**
```python
from datetime import date
from lib import get_expiry_ranges, get_underlying_agg

event = date(2025, 11, 1)
prev = date(2025, 10, 25)
next_exp = date(2025, 11, 8)

ranges = get_expiry_ranges(event, prev, next_exp)

# Fetch price data for event period
event_start, event_end = ranges["event"]
bars = get_underlying_agg("AAPL", event_start, event_end)
```

---

### `filter_expiries_around_earnings(earnings_events, get_expiries_func, ...)`

Process multiple earnings events and find valid expiries for each.

This is a high-level convenience function that:
1. Gets expiries for each symbol
2. Finds event and neighbors
3. Validates the selection
4. Filters to only valid events
5. Calculates DTE metrics

**Parameters:**
- `earnings_events` (List[Dict]): List from `get_upcoming_earnings()`
- `get_expiries_func` (Callable): Function to get expiries (e.g., `get_expiries`)
- `max_event_dte` (int): Maximum days to event expiry (default: 60)
- `require_neighbors` (bool): Filter out events without prev/next (default: False)

**Returns:**
```python
[
    {
        "symbol": str,
        "earnings_ts": datetime,
        "earnings_date": date,
        "expiries": {
            "event": date,
            "prev": date or None,
            "next": date or None
        },
        "validation": {
            "has_event": bool,
            "has_prev": bool,
            "has_next": bool,
            "is_valid": bool
        },
        "dte": {
            "event": int,           # Days from earnings to event
            "prev": int or None,    # Days from earnings to prev
            "next": int or None     # Days from event to next
        }
    },
    ...
]
```

**Example:**
```python
from datetime import date, timedelta
from lib import (
    get_upcoming_earnings,
    get_expiries,
    filter_expiries_around_earnings
)

# Find earnings
symbols = ["AAPL", "MSFT", "GOOGL"]
start = date.today()
end = start + timedelta(days=30)
earnings = get_upcoming_earnings(symbols, start, end)

# Process all earnings events at once
valid_events = filter_expiries_around_earnings(
    earnings,
    get_expiries,
    max_event_dte=60,
    require_neighbors=True  # Only events with prev and next
)

print(f"Found {len(valid_events)} tradeable events")

for event in valid_events:
    print(f"\n{event['symbol']}")
    print(f"  Earnings: {event['earnings_date']}")
    print(f"  Event expiry: {event['expiries']['event']} (DTE: {event['dte']['event']})")
    print(f"  Strategy: {'Calendar spreads available' if event['validation']['has_prev'] else 'Naked only'}")
```

---

## Complete Workflow Example

```python
from datetime import date, timedelta
from lib import (
    get_upcoming_earnings,
    get_expiries,
    find_event_and_neighbors,
    validate_event_expiries,
    filter_expiries_around_earnings,
    get_chain_snapshot
)

# Step 1: Find upcoming earnings
symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
start = date.today()
end = start + timedelta(days=30)

earnings = get_upcoming_earnings(symbols, start, end)
print(f"Found {len(earnings)} earnings events")

# Step 2: Filter to valid tradeable events
valid_events = filter_expiries_around_earnings(
    earnings,
    get_expiries,
    max_event_dte=60,
    require_neighbors=True
)

print(f"Found {len(valid_events)} valid trading opportunities")

# Step 3: For each valid event, get options chain
for event in valid_events:
    symbol = event["symbol"]
    expiries = event["expiries"]
    
    # Get options chain for event and next expiry
    contracts = get_chain_snapshot(
        symbol,
        expiries["event"],
        expiries["next"]
    )
    
    print(f"\n{symbol}: {len(contracts)} contracts")
    
    # Filter to event expiry contracts
    event_contracts = [
        c for c in contracts
        if c.get("details", {}).get("expiration_date") == str(expiries["event"])
    ]
    
    print(f"  Event expiry contracts: {len(event_contracts)}")
    
    # Now ready for scoring and strategy selection...
```

---

## Strategy Selection Guide

### Based on Available Expiries

| Has Prev | Has Event | Has Next | Available Strategies |
|----------|-----------|----------|---------------------|
| ✓ | ✓ | ✓ | All strategies: Naked, Calendar, Diagonal |
| ✗ | ✓ | ✓ | Naked, Forward calendar |
| ✓ | ✓ | ✗ | Naked, Reverse calendar |
| ✗ | ✓ | ✗ | Naked only |

### Based on Event DTE

| Event DTE | Recommendation |
|-----------|----------------|
| 0-7 days  | Short-dated, high gamma exposure |
| 7-14 days | Weekly earnings plays |
| 14-30 days | Standard earnings plays |
| 30-60 days | Monthly earnings plays |
| 60+ days  | Consider skipping (too much time decay) |

---

## Edge Cases

### 1. Earnings After Market Close on Expiry Day

```python
earnings = datetime(2025, 10, 31, 16, 0)  # After close
expiries = [date(2025, 10, 31), date(2025, 11, 7)]

result = find_event_and_neighbors(earnings, expiries)
# event = 2025-10-31 (same day is valid)
```

**Recommendation:** Same-day expiry is valid but risky. Consider using next expiry instead.

### 2. Earnings Before Market Open

```python
earnings = datetime(2025, 10, 31, 9, 0)  # Before open
expiries = [date(2025, 10, 31), date(2025, 11, 7)]

result = find_event_and_neighbors(earnings, expiries)
# event = 2025-10-31 (same day, options expire EOD)
```

**Recommendation:** Same-day works, but most earnings movement will happen before open.

### 3. No Expiries After Earnings

```python
earnings = datetime(2025, 12, 1, 16, 0)
expiries = [date(2025, 11, 1), date(2025, 11, 15)]  # All before

result = find_event_and_neighbors(earnings, expiries)
# event = None (no valid expiry)
```

**Recommendation:** Skip this event, can't trade earnings with past expiries.

### 4. Very Long DTE

```python
earnings = datetime(2025, 10, 26, 16, 0)
expiries = [date(2026, 1, 16)]  # LEAPS, 82 days away

validation = validate_event_expiries(
    expiries[0], None, None, earnings.date(),
    max_event_dte=60
)
# is_valid = False (too far out)
```

**Recommendation:** Use `max_event_dte` to filter out overly long dated options.

---

## Best Practices

1. **Always validate expiries** before using them for trading
2. **Check for neighbors** if you need calendar spreads
3. **Set reasonable DTE limits** (typically 0-60 days for earnings)
4. **Handle missing data gracefully** - not all symbols have weekly options
5. **Log filtered events** to understand why opportunities are being skipped

---

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_events.py -v
```

All 19 tests cover:
- Basic event selection
- Edge cases (same-day, no prev/next, after all expiries)
- Validation logic
- Date range calculation
- Batch filtering
- DTE calculations

---

## Performance Notes

- `find_event_and_neighbors()` - O(n) where n = number of expiries (~50-200)
- `filter_expiries_around_earnings()` - O(m × n) where m = events, n = expiries
  - For 10 earnings events, ~0.1-1 second depending on API calls
  - Most time is spent in `get_expiries()` API calls, not the logic

Consider caching expiries if processing large batches.

