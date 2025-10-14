"""Polygon.io API client for fetching options chain and market data.

This module provides utilities for:
- Fetching options chains for specific expiries
- Computing option flow features (OI, volume, Greeks)
- Calculating risk-reversal, PCR, and spread metrics
- Supporting the Direction-First scoring pipeline

Usage:
    from option_research.polygon_client import PolygonClient
    
    client = PolygonClient(api_key="your_key_here")
    chain = client.get_option_chain(ticker="AAPL", expiry="2024-04-19")
    
    # Compute features for pipeline
    features = client.compute_chain_features(
        ticker="AAPL",
        expiry="2024-04-19",
        spot_price=170.0,
    )
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import requests
from dotenv import load_dotenv


@dataclass(slots=True)
class OptionContract:
    """Represents a single option contract."""

    ticker: str  # Underlying ticker
    contract_ticker: str  # Full option ticker (e.g., O:AAPL240419C00170000)
    expiry: str  # ISO format YYYY-MM-DD
    strike: float
    option_type: Literal["call", "put"]
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None


@dataclass(slots=True)
class ChainSnapshot:
    """Snapshot of an options chain for a specific expiry."""

    ticker: str
    expiry: str
    as_of: datetime
    spot_price: float
    contracts: list[OptionContract]


class PolygonClient:
    """Client for interacting with Polygon.io API."""

    BASE_URL = "https://api.polygon.io"

    def __init__(self, api_key: str | None = None, auto_load_env: bool = True):
        """Initialize Polygon client.
        
        Args:
            api_key: Polygon.io API key. If not provided, attempts to read from
                     POLYGON_API_KEY environment variable or .env file.
            auto_load_env: If True, automatically loads .env file from project root.
        
        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        # Automatically load .env file if it exists
        if auto_load_env and api_key is None:
            # Try to find .env file in current directory or parent directories
            current_dir = Path.cwd()
            for parent in [current_dir] + list(current_dir.parents):
                env_file = parent / ".env"
                if env_file.exists():
                    load_dotenv(env_file)
                    break
        
        if api_key is None:
            api_key = os.environ.get("POLYGON_API_KEY")
        
        if not api_key:
            raise ValueError(
                "Polygon API key required. Pass as argument or set POLYGON_API_KEY "
                "environment variable or create a .env file with:\n"
                "POLYGON_API_KEY=your_key_here"
            )
        
        self.api_key = api_key
        self.session = requests.Session()

    def _make_request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make authenticated request to Polygon API.
        
        Args:
            endpoint: API endpoint path (e.g., "/v3/reference/options/contracts").
            params: Query parameters.
        
        Returns:
            JSON response as dictionary.
        
        Raises:
            RuntimeError: If request fails.
        """
        if params is None:
            params = {}
        
        params["apiKey"] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Polygon API request failed: {e}")

    def get_option_contracts(
        self,
        ticker: str,
        expiry: str,
        contract_type: Literal["call", "put", "both"] = "both",
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Fetch option contract metadata for a specific expiry.
        
        Args:
            ticker: Underlying stock ticker (e.g., "AAPL").
            expiry: Expiration date in ISO format (YYYY-MM-DD).
            contract_type: Filter by contract type ("call", "put", or "both").
            limit: Maximum number of contracts to fetch.
        
        Returns:
            List of contract metadata dictionaries.
        """
        params = {
            "underlying_ticker": ticker.upper(),
            "expiration_date": expiry,
            "limit": limit,
        }
        
        if contract_type != "both":
            params["contract_type"] = contract_type
        
        response = self._make_request("/v3/reference/options/contracts", params)
        return response.get("results", [])

    def get_option_quotes(self, contract_ticker: str) -> dict[str, Any]:
        """Fetch current quote (bid/ask/last) for an option contract.
        
        Args:
            contract_ticker: Full option ticker (e.g., "O:AAPL240419C00170000").
        
        Returns:
            Quote data including bid, ask, last, volume.
        """
        endpoint = f"/v3/quotes/{contract_ticker}"
        response = self._make_request(endpoint)
        
        results = response.get("results", [])
        if not results:
            return {}
        
        # Return most recent quote
        return results[0]

    def get_option_snapshot(self, ticker: str) -> dict[str, Any]:
        """Fetch snapshot of all options for underlying ticker.
        
        Args:
            ticker: Underlying stock ticker.
        
        Returns:
            Snapshot data with all active option contracts.
        """
        endpoint = f"/v3/snapshot/options/{ticker.upper()}"
        response = self._make_request(endpoint)
        return response

    def get_option_chain(
        self,
        ticker: str,
        expiry: str,
        include_greeks: bool = True,
    ) -> list[OptionContract]:
        """Fetch complete option chain for a specific expiry.
        
        Args:
            ticker: Underlying stock ticker.
            expiry: Expiration date in ISO format.
            include_greeks: If True, fetch Greeks (delta, gamma, etc).
        
        Returns:
            List of OptionContract objects with full market data.
        """
        # First get contract metadata
        contracts_meta = self.get_option_contracts(ticker, expiry)
        
        if not contracts_meta:
            return []
        
        # Fetch snapshot for all options (more efficient than individual quotes)
        snapshot = self.get_option_snapshot(ticker)
        snapshot_results = snapshot.get("results", [])
        
        # Build lookup for quick access
        snapshot_map = {
            result["details"]["contract_type"] + "_" + str(result["details"]["strike_price"]): result
            for result in snapshot_results
            if result.get("details", {}).get("expiration_date") == expiry
        }
        
        contracts: list[OptionContract] = []
        
        for meta in contracts_meta:
            contract_type = meta.get("contract_type", "").lower()
            strike = float(meta.get("strike_price", 0))
            contract_ticker = meta.get("ticker", "")
            
            # Try to find matching snapshot data
            lookup_key = contract_type + "_" + str(strike)
            snapshot_data = snapshot_map.get(lookup_key, {})
            
            # Extract quote data
            quote = snapshot_data.get("last_quote", {})
            greeks = snapshot_data.get("greeks", {}) if include_greeks else {}
            day_data = snapshot_data.get("day", {})
            
            contracts.append(
                OptionContract(
                    ticker=ticker.upper(),
                    contract_ticker=contract_ticker,
                    expiry=expiry,
                    strike=strike,
                    option_type=contract_type,
                    bid=quote.get("bid", 0.0),
                    ask=quote.get("ask", 0.0),
                    last=snapshot_data.get("last_trade", {}).get("price", 0.0),
                    volume=day_data.get("volume", 0),
                    open_interest=snapshot_data.get("open_interest", 0),
                    implied_volatility=greeks.get("implied_volatility"),
                    delta=greeks.get("delta"),
                    gamma=greeks.get("gamma"),
                    theta=greeks.get("theta"),
                    vega=greeks.get("vega"),
                )
            )
        
        return contracts

    def get_stock_price(self, ticker: str) -> float:
        """Fetch current stock price.
        
        Args:
            ticker: Stock ticker symbol.
        
        Returns:
            Current price.
        """
        endpoint = f"/v2/aggs/ticker/{ticker.upper()}/prev"
        response = self._make_request(endpoint)
        
        results = response.get("results", [])
        if not results:
            raise RuntimeError(f"No price data found for {ticker}")
        
        # Return close price from previous day
        return float(results[0].get("c", 0.0))

    def compute_chain_features(
        self,
        ticker: str,
        expiry: str,
        spot_price: float | None = None,
        atm_window_pct: float = 0.10,
    ) -> dict[str, Any]:
        """Compute pipeline features from option chain.
        
        This computes the features needed for the Direction-First pipeline:
        - D1: Risk-reversal (25Δ)
        - D3: Put-call ratio (notional volume)
        - P1: IV bump percentile
        - P2: Spread penalty
        
        Args:
            ticker: Underlying stock ticker.
            expiry: Expiration date for the event.
            spot_price: Current stock price (fetched if not provided).
            atm_window_pct: Window around ATM for computing features (default 10%).
        
        Returns:
            Dictionary with computed features.
        """
        if spot_price is None:
            spot_price = self.get_stock_price(ticker)
        
        chain = self.get_option_chain(ticker, expiry, include_greeks=True)
        
        if not chain:
            raise RuntimeError(f"No option chain data for {ticker} expiry {expiry}")
        
        # Filter to ATM window
        lower_bound = spot_price * (1 - atm_window_pct)
        upper_bound = spot_price * (1 + atm_window_pct)
        atm_contracts = [c for c in chain if lower_bound <= c.strike <= upper_bound]
        
        calls = [c for c in atm_contracts if c.option_type == "call"]
        puts = [c for c in atm_contracts if c.option_type == "put"]
        
        # D1: Risk Reversal (25Δ)
        risk_reversal = self._compute_risk_reversal(chain)
        
        # D3: Put-Call Ratio (notional volume)
        put_volume_notional = sum(
            p.volume * ((p.bid + p.ask) / 2) * 100 for p in puts if p.bid > 0 and p.ask > 0
        )
        call_volume_notional = sum(
            c.volume * ((c.bid + c.ask) / 2) * 100 for c in calls if c.bid > 0 and c.ask > 0
        )
        
        # P2: Spread penalty (median bid-ask spread %)
        spreads = []
        for contract in atm_contracts:
            if contract.bid > 0 and contract.ask > 0:
                mid = (contract.bid + contract.ask) / 2
                spread_pct = (contract.ask - contract.bid) / mid if mid > 0 else 0
                spreads.append(spread_pct)
        
        spread_pct = sorted(spreads)[len(spreads) // 2] if spreads else 0.0
        
        # Total notional volume (for liquidity filter)
        total_notional_volume = put_volume_notional + call_volume_notional
        
        return {
            "ticker": ticker.upper(),
            "as_of": datetime.now().date().isoformat(),
            "expiry": expiry,
            "spot_price": spot_price,
            "risk_reversal": risk_reversal,
            "put_volume_notional": put_volume_notional,
            "call_volume_notional": max(call_volume_notional, 1e-9),  # Avoid division by zero
            "spread_pct": spread_pct,
            "total_notional_volume": total_notional_volume,
            "num_calls": len(calls),
            "num_puts": len(puts),
        }

    def _compute_risk_reversal(self, chain: list[OptionContract]) -> float:
        """Compute 25Δ risk-reversal (IV_call_25Δ - IV_put_25Δ).
        
        Args:
            chain: List of option contracts.
        
        Returns:
            Risk-reversal value.
        """
        calls = [c for c in chain if c.option_type == "call" and c.delta is not None and c.implied_volatility is not None]
        puts = [c for c in chain if c.option_type == "put" and c.delta is not None and c.implied_volatility is not None]
        
        # Find contracts closest to 25Δ
        call_25d = self._find_contract_by_delta(calls, target_delta=0.25)
        put_25d = self._find_contract_by_delta(puts, target_delta=-0.25)
        
        if call_25d and put_25d and call_25d.implied_volatility and put_25d.implied_volatility:
            return call_25d.implied_volatility - put_25d.implied_volatility
        
        return 0.0

    @staticmethod
    def _find_contract_by_delta(
        contracts: list[OptionContract],
        target_delta: float,
    ) -> OptionContract | None:
        """Find option contract closest to target delta.
        
        Args:
            contracts: List of option contracts.
            target_delta: Target delta value (e.g., 0.25 for calls, -0.25 for puts).
        
        Returns:
            Closest contract or None if no valid contracts.
        """
        if not contracts:
            return None
        
        # Find contract with delta closest to target
        best_contract = min(
            contracts,
            key=lambda c: abs(c.delta - target_delta) if c.delta is not None else float("inf"),
        )
        
        return best_contract if best_contract.delta is not None else None

    @staticmethod
    def get_earnings_expiry(earnings_date: str) -> str:
        """Find first Friday after earnings date.
        
        This is a utility function to compute the event expiry for options trading.
        
        Args:
            earnings_date: Earnings date in ISO format (YYYY-MM-DD).
        
        Returns:
            ISO date string of the first Friday after earnings date.
        """
        earn_dt = datetime.fromisoformat(earnings_date)
        
        # Friday is weekday 4 (Monday=0)
        days_until_friday = (4 - earn_dt.weekday()) % 7
        
        # If earnings is on Friday, go to next Friday
        if days_until_friday == 0:
            days_until_friday = 7
        
        friday = earn_dt + timedelta(days=days_until_friday)
        return friday.strftime("%Y-%m-%d")

    def get_historical_prices(
        self,
        ticker: str,
        start_date: str,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch historical daily OHLC prices.
        
        Args:
            ticker: Stock ticker symbol.
            start_date: Start date in ISO format.
            end_date: End date in ISO format (defaults to today).
        
        Returns:
            List of daily price bars with open, high, low, close, volume.
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        endpoint = f"/v2/aggs/ticker/{ticker.upper()}/range/1/day/{start_date}/{end_date}"
        response = self._make_request(endpoint)
        
        results = response.get("results", [])
        
        # Convert to more readable format
        bars = []
        for bar in results:
            bars.append({
                "timestamp": bar.get("t"),
                "open": bar.get("o"),
                "high": bar.get("h"),
                "low": bar.get("l"),
                "close": bar.get("c"),
                "volume": bar.get("v"),
            })
        
        return bars


__all__ = ["PolygonClient", "OptionContract", "ChainSnapshot"]

