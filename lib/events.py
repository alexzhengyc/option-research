"""
Event and expiry selection logic for earnings-based option strategies
"""
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict


def find_event_and_neighbors(
    earnings_ts: datetime,
    expiries: List[date]
) -> Dict[str, Optional[date]]:
    """
    Find the event expiry and its neighbors for an earnings event
    
    The event expiry is the first expiry >= earnings date. This is the key
    expiry that will capture the earnings volatility move.
    
    The prev expiry is the nearest expiry before the event (for comparison).
    The next expiry is the nearest expiry after the event (for spreads/comparison).
    
    Args:
        earnings_ts: Earnings datetime (with time component)
        expiries: List of available option expiration dates (sorted ascending)
    
    Returns:
        Dict with keys:
        {
            "event": date or None,  # First expiry >= earnings date
            "prev": date or None,   # Nearest expiry before event
            "next": date or None    # Nearest expiry after event
        }
    
    Examples:
        >>> from datetime import datetime, date
        >>> earnings = datetime(2025, 10, 26, 16, 0)  # Oct 26 after market close
        >>> expiries = [
        ...     date(2025, 10, 18),
        ...     date(2025, 10, 25),
        ...     date(2025, 11, 1),
        ...     date(2025, 11, 15)
        ... ]
        >>> result = find_event_and_neighbors(earnings, expiries)
        >>> result
        {'event': date(2025, 11, 1), 'prev': date(2025, 10, 25), 'next': date(2025, 11, 15)}
    """
    # Convert earnings timestamp to date for comparison
    earnings_date = earnings_ts.date()

    # If earnings are after the market close, use the next calendar day
    # when identifying the event expiry. Same-day expiries would have
    # already settled before an after-close report, so they should be
    # treated as the "prev" expiry instead of the event.
    market_close = time(16, 0)
    if earnings_ts.time() >= market_close:
        earnings_date = earnings_date + timedelta(days=1)
    
    # Ensure expiries are sorted
    sorted_expiries = sorted(expiries)
    
    # Initialize result
    result = {
        "event": None,
        "prev": None,
        "next": None
    }
    
    # Handle edge cases
    if not sorted_expiries:
        return result
    
    # Find the event expiry: first expiry >= earnings date
    event_idx = None
    for i, expiry in enumerate(sorted_expiries):
        if expiry >= earnings_date:
            result["event"] = expiry
            event_idx = i
            break
    
    # If no event found (earnings after all expiries), return early
    if event_idx is None:
        return result
    
    # Find prev expiry: nearest expiry before event
    if event_idx > 0:
        result["prev"] = sorted_expiries[event_idx - 1]
    
    # Find next expiry: nearest expiry after event
    if event_idx < len(sorted_expiries) - 1:
        result["next"] = sorted_expiries[event_idx + 1]
    
    return result


def validate_event_expiries(
    event: Optional[date],
    prev: Optional[date],
    next: Optional[date],
    earnings_date: date,
    min_prev_dte: int = 0,
    max_event_dte: int = 90,
    min_next_dte: int = 7
) -> Dict[str, bool]:
    """
    Validate that event expiries meet strategy requirements
    
    Args:
        event: Event expiry date
        prev: Previous expiry date
        next: Next expiry date
        earnings_date: Earnings date
        min_prev_dte: Minimum days to expiry for prev (default: 0)
        max_event_dte: Maximum days to expiry for event (default: 90)
        min_next_dte: Minimum days after event for next (default: 7)
    
    Returns:
        Dict with validation results:
        {
            "has_event": bool,
            "has_prev": bool,
            "has_next": bool,
            "event_dte_ok": bool,
            "prev_dte_ok": bool,
            "next_dte_ok": bool,
            "is_valid": bool  # True if all required checks pass
        }
    """
    validation = {
        "has_event": event is not None,
        "has_prev": prev is not None,
        "has_next": next is not None,
        "event_dte_ok": False,
        "prev_dte_ok": False,
        "next_dte_ok": False,
        "is_valid": False
    }
    
    # Check event DTE
    if event:
        event_dte = (event - earnings_date).days
        validation["event_dte_ok"] = 0 <= event_dte <= max_event_dte
    
    # Check prev DTE
    if prev:
        prev_dte = (prev - earnings_date).days
        validation["prev_dte_ok"] = prev_dte >= min_prev_dte
    
    # Check next DTE
    if next and event:
        next_gap = (next - event).days
        validation["next_dte_ok"] = next_gap >= min_next_dte
    
    # Overall validity: must have event and it must be within acceptable DTE
    validation["is_valid"] = validation["has_event"] and validation["event_dte_ok"]
    
    return validation


def get_expiry_ranges(
    event: date,
    prev: Optional[date] = None,
    next: Optional[date] = None
) -> Dict[str, tuple]:
    """
    Get date ranges for each expiry period for data fetching
    
    This helps determine what date ranges to use when fetching historical
    data, options chain snapshots, etc.
    
    Args:
        event: Event expiry date
        prev: Previous expiry date (optional)
        next: Next expiry date (optional)
    
    Returns:
        Dict with date ranges:
        {
            "prev": (start_date, end_date) or None,
            "event": (start_date, end_date),
            "next": (start_date, end_date) or None
        }
        
        Ranges represent the trading period for each expiry.
    """
    ranges = {
        "prev": None,
        "event": None,
        "next": None
    }
    
    # Event range: from prev expiry (or reasonable lookback) to event expiry
    if prev:
        ranges["event"] = (prev, event)
    else:
        # If no prev, use 30 days before event
        from datetime import timedelta
        start = event - timedelta(days=30)
        ranges["event"] = (start, event)
    
    # Prev range: if we have prev, need to determine its start
    if prev:
        from datetime import timedelta
        # Assume ~7-14 days before prev for weekly/bi-weekly cycles
        start = prev - timedelta(days=14)
        ranges["prev"] = (start, prev)
    
    # Next range: from event to next expiry
    if next:
        ranges["next"] = (event, next)
    
    return ranges


def filter_expiries_around_earnings(
    earnings_events: List[Dict[str, any]],
    get_expiries_func,
    max_event_dte: int = 60,
    require_neighbors: bool = False
) -> List[Dict[str, any]]:
    """
    Process multiple earnings events and find valid expiries for each
    
    Args:
        earnings_events: List of earnings events from get_upcoming_earnings()
            Format: [{"symbol": str, "earnings_ts": datetime}, ...]
        get_expiries_func: Function to get expiries for a symbol
            Should have signature: get_expiries_func(symbol) -> List[date]
        max_event_dte: Maximum days to event expiry (default: 60)
        require_neighbors: If True, only include events with prev/next expiries
    
    Returns:
        List of enriched earnings events:
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
                    "event": int,  # Days from earnings to event expiry
                    "prev": int or None,  # Days from earnings to prev
                    "next": int or None   # Days from event to next
                }
            },
            ...
        ]
        
        Only includes events that pass validation.
    """
    processed_events = []
    
    for event in earnings_events:
        symbol = event["symbol"]
        earnings_ts = event["earnings_ts"]
        earnings_date = earnings_ts.date()
        
        try:
            # Get available expiries for this symbol
            expiries = get_expiries_func(symbol)
            
            if not expiries:
                print(f"Warning: No expiries found for {symbol}")
                continue
            
            # Find event and neighbors
            expiry_dates = find_event_and_neighbors(earnings_ts, expiries)
            
            # Validate
            validation = validate_event_expiries(
                expiry_dates["event"],
                expiry_dates["prev"],
                expiry_dates["next"],
                earnings_date,
                max_event_dte=max_event_dte
            )
            
            # Skip if validation fails
            if not validation["is_valid"]:
                continue
            
            # Skip if neighbors required but not available
            if require_neighbors and (not expiry_dates["prev"] or not expiry_dates["next"]):
                continue
            
            # Calculate DTE metrics
            dte = {
                "event": (expiry_dates["event"] - earnings_date).days if expiry_dates["event"] else None,
                "prev": (expiry_dates["prev"] - earnings_date).days if expiry_dates["prev"] else None,
                "next": (expiry_dates["next"] - expiry_dates["event"]).days if expiry_dates["next"] and expiry_dates["event"] else None
            }
            
            # Add enriched event
            processed_events.append({
                "symbol": symbol,
                "earnings_ts": earnings_ts,
                "earnings_date": earnings_date,
                "expiries": expiry_dates,
                "validation": validation,
                "dte": dte
            })
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    return processed_events

