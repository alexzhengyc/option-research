"""
Signal computation functions for options analysis
Dev Stage 6 - Signal Math
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import date, timedelta
from scipy import interpolate


def interp_iv_at_delta(
    contracts: List[Dict],
    target_delta: float = 0.25,
    side: str = "call"
) -> Optional[float]:
    """
    Interpolate implied volatility at a target delta level
    
    Args:
        contracts: List of option contracts with 'greeks' and 'implied_volatility'
        target_delta: Target delta level (e.g., 0.25 for 25-delta)
        side: "call" or "put"
    
    Returns:
        Interpolated IV at target delta, or None if insufficient data
    
    Example:
        >>> contracts = get_chain_snapshot("AAPL", event_date, event_date)
        >>> iv_25d_call = interp_iv_at_delta(contracts, target_delta=0.25, side="call")
        >>> iv_25d_put = interp_iv_at_delta(contracts, target_delta=0.25, side="put")
    """
    # Filter contracts by side
    side_contracts = [
        c for c in contracts
        if c.get("details", {}).get("contract_type", "").lower() == side.lower()
    ]
    
    if not side_contracts:
        return None
    
    # Extract delta and IV pairs
    delta_iv_pairs = []
    for contract in side_contracts:
        greeks = contract.get("greeks", {})
        delta = greeks.get("delta")
        iv = contract.get("implied_volatility")
        
        if delta is not None and iv is not None and iv > 0:
            # Use absolute delta for comparison
            abs_delta = abs(delta)
            delta_iv_pairs.append((abs_delta, iv))
    
    if len(delta_iv_pairs) < 2:
        return None
    
    # Sort by delta
    delta_iv_pairs.sort(key=lambda x: x[0])
    
    # Extract arrays
    deltas = np.array([d for d, _ in delta_iv_pairs])
    ivs = np.array([iv for _, iv in delta_iv_pairs])
    
    # Check if target_delta is within range
    if target_delta < deltas.min() or target_delta > deltas.max():
        # If target is outside range, use linear extrapolation (carefully)
        # or return nearest value
        if target_delta < deltas.min():
            return ivs[0]
        else:
            return ivs[-1]
    
    # Interpolate using linear interpolation
    interp_func = interpolate.interp1d(deltas, ivs, kind='linear', fill_value='extrapolate')
    return float(interp_func(target_delta))


def atm_iv(contracts: List[Dict], spot_price: Optional[float] = None) -> Optional[float]:
    """
    Interpolate ATM (at-the-money) implied volatility around spot price
    
    Args:
        contracts: List of option contracts
        spot_price: Current spot price of underlying (if None, will be extracted from contracts)
    
    Returns:
        Interpolated ATM IV, or None if insufficient data
    
    Example:
        >>> contracts = get_chain_snapshot("AAPL", event_date, event_date)
        >>> atm_vol = atm_iv(contracts, spot_price=150.0)
    """
    if not contracts:
        return None
    
    # Extract spot price if not provided
    if spot_price is None:
        # Try to get from contract data
        for contract in contracts:
            underlying_price = contract.get("underlying_asset", {}).get("price")
            if underlying_price:
                spot_price = underlying_price
                break
        
        if spot_price is None:
            return None
    
    # Get calls and puts near ATM
    call_strikes = []
    call_ivs = []
    put_strikes = []
    put_ivs = []
    
    for contract in contracts:
        details = contract.get("details", {})
        strike = details.get("strike_price")
        contract_type = details.get("contract_type", "").lower()
        iv = contract.get("implied_volatility")
        
        if strike is None or iv is None or iv <= 0:
            continue
        
        # Only use strikes within ±20% of spot
        if abs(strike - spot_price) / spot_price > 0.2:
            continue
        
        if contract_type == "call":
            call_strikes.append(strike)
            call_ivs.append(iv)
        elif contract_type == "put":
            put_strikes.append(strike)
            put_ivs.append(iv)
    
    # Need at least 2 points for interpolation
    if len(call_strikes) < 2 or len(put_strikes) < 2:
        # Fall back to any available ATM contracts
        all_strikes = call_strikes + put_strikes
        all_ivs = call_ivs + put_ivs
        if not all_strikes:
            return None
        
        # Find closest strike to spot
        closest_idx = np.argmin([abs(s - spot_price) for s in all_strikes])
        return all_ivs[closest_idx]
    
    # Interpolate for calls
    call_strikes = np.array(call_strikes)
    call_ivs = np.array(call_ivs)
    sorted_call_idx = np.argsort(call_strikes)
    call_strikes = call_strikes[sorted_call_idx]
    call_ivs = call_ivs[sorted_call_idx]
    
    # Interpolate for puts
    put_strikes = np.array(put_strikes)
    put_ivs = np.array(put_ivs)
    sorted_put_idx = np.argsort(put_strikes)
    put_strikes = put_strikes[sorted_put_idx]
    put_ivs = put_ivs[sorted_put_idx]
    
    # Interpolate at spot
    call_interp = interpolate.interp1d(call_strikes, call_ivs, kind='linear', fill_value='extrapolate')
    put_interp = interpolate.interp1d(put_strikes, put_ivs, kind='linear', fill_value='extrapolate')
    
    call_atm_iv = float(call_interp(spot_price))
    put_atm_iv = float(put_interp(spot_price))
    
    # Average call and put ATM IV
    return (call_atm_iv + put_atm_iv) / 2.0


def compute_rr_25d(event_contracts: List[Dict]) -> Optional[float]:
    """
    Compute 25-delta risk reversal: IV(25Δ Call) - IV(25Δ Put)
    
    Higher values indicate bullish skew
    
    Args:
        event_contracts: Contracts for the event expiry
    
    Returns:
        Risk reversal value, or None if cannot be computed
    
    Example:
        >>> contracts = get_chain_snapshot("AAPL", event_date, event_date)
        >>> rr = compute_rr_25d(contracts)
        >>> print(f"25Δ RR: {rr:.4f}")  # Positive = bullish skew
    """
    iv_25d_call = interp_iv_at_delta(event_contracts, target_delta=0.25, side="call")
    iv_25d_put = interp_iv_at_delta(event_contracts, target_delta=0.25, side="put")
    
    if iv_25d_call is None or iv_25d_put is None:
        return None
    
    return iv_25d_call - iv_25d_put


def compute_pcr(event_contracts: List[Dict]) -> Dict[str, Optional[float]]:
    """
    Compute put-call ratio (both volume and notional)
    
    PCR_vol = total_put_volume / total_call_volume
    PCR_notional = total_put_notional / total_call_notional
    
    Lower PCR indicates bullish sentiment
    
    Args:
        event_contracts: Contracts for the event expiry
    
    Returns:
        Dict with 'vol_pcr' and 'notional_pcr', or None values if insufficient data
    
    Example:
        >>> contracts = get_chain_snapshot("AAPL", event_date, event_date)
        >>> pcr = compute_pcr(contracts)
        >>> print(f"Volume PCR: {pcr['vol_pcr']:.2f}")
        >>> print(f"Notional PCR: {pcr['notional_pcr']:.2f}")
    """
    call_volume = 0
    put_volume = 0
    call_notional = 0.0
    put_notional = 0.0
    
    for contract in event_contracts:
        details = contract.get("details", {})
        contract_type = details.get("contract_type", "").lower()
        volume = contract.get("day", {}).get("volume", 0) or 0
        
        # Get price for notional calculation
        last_trade = contract.get("last_trade", {})
        price = last_trade.get("price") or contract.get("day", {}).get("close")
        
        if price is None or price <= 0:
            continue
        
        notional = volume * price * 100  # 100 shares per contract
        
        if contract_type == "call":
            call_volume += volume
            call_notional += notional
        elif contract_type == "put":
            put_volume += volume
            put_notional += notional
    
    vol_pcr = None
    notional_pcr = None
    
    if call_volume > 0:
        vol_pcr = put_volume / call_volume
    
    if call_notional > 0:
        notional_pcr = put_notional / call_notional
    
    return {
        "vol_pcr": vol_pcr,
        "notional_pcr": notional_pcr
    }


def compute_volume_thrust(
    event_contracts: List[Dict],
    med20_volumes: Dict[str, float]
) -> Dict[str, Optional[float]]:
    """
    Compute volume thrust: (current_volume - median_20d) / median_20d
    
    Positive thrust indicates unusual activity
    
    Args:
        event_contracts: Contracts for the event expiry
        med20_volumes: Dict with 'call_med20' and 'put_med20' baseline volumes
    
    Returns:
        Dict with 'call_thrust', 'put_thrust', 'net_thrust'
    
    Example:
        >>> contracts = get_chain_snapshot("AAPL", event_date, event_date)
        >>> med20 = {"call_med20": 5000, "put_med20": 3000}
        >>> thrust = compute_volume_thrust(contracts, med20)
        >>> print(f"Call thrust: {thrust['call_thrust']:.2%}")
        >>> print(f"Net thrust: {thrust['net_thrust']:.2%}")
    """
    call_volume = 0
    put_volume = 0
    
    for contract in event_contracts:
        details = contract.get("details", {})
        contract_type = details.get("contract_type", "").lower()
        volume = contract.get("day", {}).get("volume", 0) or 0
        
        if contract_type == "call":
            call_volume += volume
        elif contract_type == "put":
            put_volume += volume
    
    call_thrust = None
    put_thrust = None
    net_thrust = None
    
    call_med20 = med20_volumes.get("call_med20", 0)
    put_med20 = med20_volumes.get("put_med20", 0)
    
    if call_med20 > 0:
        call_thrust = (call_volume - call_med20) / call_med20
    
    if put_med20 > 0:
        put_thrust = (put_volume - put_med20) / put_med20
    
    if call_thrust is not None and put_thrust is not None:
        net_thrust = call_thrust - put_thrust
    
    return {
        "call_thrust": call_thrust,
        "put_thrust": put_thrust,
        "net_thrust": net_thrust
    }


def compute_iv_bump(
    atm_event: float,
    atm_prev: Optional[float],
    atm_next: Optional[float]
) -> Optional[float]:
    """
    Compute IV bump at event node relative to neighboring expiries
    
    IV_bump = atm_event - avg(atm_prev, atm_next)
    
    Higher bump indicates event is priced rich (higher premium)
    
    Args:
        atm_event: ATM IV at event expiry
        atm_prev: ATM IV at previous expiry (can be None)
        atm_next: ATM IV at next expiry (can be None)
    
    Returns:
        IV bump value, or None if insufficient data
    
    Example:
        >>> # Get ATM IVs for each expiry
        >>> event_contracts = get_chain_snapshot("AAPL", event_date, event_date)
        >>> prev_contracts = get_chain_snapshot("AAPL", prev_date, prev_date)
        >>> next_contracts = get_chain_snapshot("AAPL", next_date, next_date)
        >>> 
        >>> atm_event = atm_iv(event_contracts)
        >>> atm_prev = atm_iv(prev_contracts)
        >>> atm_next = atm_iv(next_contracts)
        >>> 
        >>> iv_bump = compute_iv_bump(atm_event, atm_prev, atm_next)
        >>> print(f"IV Bump: {iv_bump:.4f}")
    """
    if atm_event is None:
        return None
    
    neighbor_ivs = []
    if atm_prev is not None:
        neighbor_ivs.append(atm_prev)
    if atm_next is not None:
        neighbor_ivs.append(atm_next)
    
    if not neighbor_ivs:
        return None
    
    avg_neighbor = np.mean(neighbor_ivs)
    return atm_event - avg_neighbor


def compute_spread_pct_atm(
    event_contracts: List[Dict],
    spot_price: Optional[float] = None
) -> Optional[float]:
    """
    Compute bid-ask spread percentage at ATM
    
    spread_pct = (ask - bid) / mid * 100
    
    Lower spread indicates better liquidity
    
    Args:
        event_contracts: Contracts for the event expiry
        spot_price: Current spot price (optional)
    
    Returns:
        Average spread percentage at ATM, or None if insufficient data
    
    Example:
        >>> contracts = get_chain_snapshot("AAPL", event_date, event_date)
        >>> spread = compute_spread_pct_atm(contracts, spot_price=150.0)
        >>> print(f"ATM Spread: {spread:.2f}%")
    """
    if not event_contracts:
        return None
    
    # Extract spot price if not provided
    if spot_price is None:
        for contract in event_contracts:
            underlying_price = contract.get("underlying_asset", {}).get("price")
            if underlying_price:
                spot_price = underlying_price
                break
        
        if spot_price is None:
            return None
    
    # Find ATM contracts (within ±5% of spot)
    spreads = []
    
    for contract in event_contracts:
        details = contract.get("details", {})
        strike = details.get("strike_price")
        
        if strike is None:
            continue
        
        # Check if near ATM
        if abs(strike - spot_price) / spot_price > 0.05:
            continue
        
        # Get bid and ask
        last_quote = contract.get("last_quote", {})
        bid = last_quote.get("bid")
        ask = last_quote.get("ask")
        
        if bid is None or ask is None or bid <= 0 or ask <= 0:
            continue
        
        mid = (bid + ask) / 2.0
        if mid <= 0:
            continue
        
        spread_pct = (ask - bid) / mid * 100
        spreads.append(spread_pct)
    
    if not spreads:
        return None
    
    # Return average spread
    return np.mean(spreads)


def compute_mom_betaadj(
    symbol: str,
    date: date,
    lookback_days: int = 3,
    sector_symbol: str = "SPY",
    get_price_data_func=None
) -> Optional[Dict[str, float]]:
    """
    Compute beta-adjusted momentum
    
    Beta-adjusted return = stock_return - beta * sector_return
    
    Args:
        symbol: Stock ticker
        date: Current date
        lookback_days: Number of days for momentum calculation (default: 3)
        sector_symbol: Sector benchmark (default: "SPY")
        get_price_data_func: Function to get price data (symbol, start, end) -> List[Dict]
    
    Returns:
        Dict with 'stock_return', 'sector_return', 'beta', 'beta_adj_return'
        or None if insufficient data
    
    Example:
        >>> from lib.polygon_client import get_underlying_agg
        >>> mom = compute_mom_betaadj(
        ...     "AAPL",
        ...     date(2025, 10, 15),
        ...     lookback_days=3,
        ...     get_price_data_func=get_underlying_agg
        ... )
        >>> print(f"Beta-adj return: {mom['beta_adj_return']:.2%}")
    """
    if get_price_data_func is None:
        # Import here to avoid circular dependency
        from .polygon_client import get_underlying_agg
        get_price_data_func = get_underlying_agg
    
    # Get date range (need extra days for beta calculation)
    end_date = date
    start_date = date - timedelta(days=lookback_days + 60)  # Extra for beta calc
    
    try:
        # Get price data
        stock_data = get_price_data_func(symbol, start_date, end_date, timespan="day")
        sector_data = get_price_data_func(sector_symbol, start_date, end_date, timespan="day")
        
        if not stock_data or not sector_data:
            return None
        
        # Convert to DataFrames
        stock_df = pd.DataFrame(stock_data)
        sector_df = pd.DataFrame(sector_data)
        
        # Convert timestamp to date
        stock_df['date'] = pd.to_datetime(stock_df['timestamp'], unit='ms').dt.date
        sector_df['date'] = pd.to_datetime(sector_df['timestamp'], unit='ms').dt.date
        
        # Calculate returns
        stock_df['return'] = stock_df['close'].pct_change()
        sector_df['return'] = sector_df['close'].pct_change()
        
        # Merge on date
        merged = pd.merge(
            stock_df[['date', 'return']],
            sector_df[['date', 'return']],
            on='date',
            suffixes=('_stock', '_sector')
        )
        
        if len(merged) < lookback_days + 20:
            return None
        
        # Calculate beta using last 60 days (or available data)
        beta_window = merged.tail(60)
        if len(beta_window) < 20:
            return None
        
        # Beta = Cov(stock, sector) / Var(sector)
        cov_matrix = np.cov(beta_window['return_stock'], beta_window['return_sector'])
        beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 1.0
        
        # Calculate recent returns (last N days)
        recent = merged.tail(lookback_days + 1)  # +1 because first return is NaN
        
        if len(recent) < lookback_days:
            return None
        
        stock_return = (recent['return_stock'].iloc[1:]).sum()  # Compound approximation
        sector_return = (recent['return_sector'].iloc[1:]).sum()
        
        # Beta-adjusted return
        beta_adj_return = stock_return - beta * sector_return
        
        return {
            "stock_return": stock_return,
            "sector_return": sector_return,
            "beta": beta,
            "beta_adj_return": beta_adj_return
        }
    
    except Exception as e:
        print(f"Error computing beta-adjusted momentum for {symbol}: {e}")
        return None


def compute_all_signals(
    symbol: str,
    event_date: date,
    event_contracts: List[Dict],
    prev_contracts: Optional[List[Dict]] = None,
    next_contracts: Optional[List[Dict]] = None,
    med20_volumes: Optional[Dict[str, float]] = None,
    lookback_days: int = 3,
    sector_symbol: str = "SPY"
) -> Dict[str, Optional[float]]:
    """
    Compute all signals for a single event
    
    Convenience function that computes all signals at once
    
    Args:
        symbol: Stock ticker
        event_date: Event expiry date
        event_contracts: Contracts at event expiry
        prev_contracts: Contracts at previous expiry (optional)
        next_contracts: Contracts at next expiry (optional)
        med20_volumes: 20-day median volumes (optional)
        lookback_days: Days for momentum calculation
        sector_symbol: Sector benchmark for beta adjustment
    
    Returns:
        Dict with all computed signals
    
    Example:
        >>> signals = compute_all_signals(
        ...     symbol="AAPL",
        ...     event_date=event_date,
        ...     event_contracts=event_contracts,
        ...     prev_contracts=prev_contracts,
        ...     next_contracts=next_contracts,
        ...     med20_volumes={"call_med20": 5000, "put_med20": 3000}
        ... )
        >>> print(signals)
    """
    signals = {}
    
    # Extract spot price
    spot_price = None
    if event_contracts:
        for contract in event_contracts:
            underlying_price = contract.get("underlying_asset", {}).get("price")
            if underlying_price:
                spot_price = underlying_price
                break
    
    # Compute signals
    signals['rr_25d'] = compute_rr_25d(event_contracts)
    
    pcr = compute_pcr(event_contracts)
    signals['vol_pcr'] = pcr['vol_pcr']
    signals['notional_pcr'] = pcr['notional_pcr']
    
    if med20_volumes:
        thrust = compute_volume_thrust(event_contracts, med20_volumes)
        signals['call_thrust'] = thrust['call_thrust']
        signals['put_thrust'] = thrust['put_thrust']
        signals['net_thrust'] = thrust['net_thrust']
    else:
        signals['call_thrust'] = None
        signals['put_thrust'] = None
        signals['net_thrust'] = None
    
    # ATM IV and bump
    signals['atm_iv_event'] = atm_iv(event_contracts, spot_price)
    
    atm_prev = None
    atm_next = None
    if prev_contracts:
        atm_prev = atm_iv(prev_contracts, spot_price)
        signals['atm_iv_prev'] = atm_prev
    else:
        signals['atm_iv_prev'] = None
    
    if next_contracts:
        atm_next = atm_iv(next_contracts, spot_price)
        signals['atm_iv_next'] = atm_next
    else:
        signals['atm_iv_next'] = None
    
    signals['iv_bump'] = compute_iv_bump(
        signals['atm_iv_event'],
        atm_prev,
        atm_next
    )
    
    # Spread
    signals['spread_pct_atm'] = compute_spread_pct_atm(event_contracts, spot_price)
    
    # Momentum
    mom = compute_mom_betaadj(
        symbol,
        event_date,
        lookback_days=lookback_days,
        sector_symbol=sector_symbol
    )
    
    if mom:
        signals['stock_return'] = mom['stock_return']
        signals['sector_return'] = mom['sector_return']
        signals['beta'] = mom['beta']
        signals['beta_adj_return'] = mom['beta_adj_return']
    else:
        signals['stock_return'] = None
        signals['sector_return'] = None
        signals['beta'] = None
        signals['beta_adj_return'] = None
    
    return signals

