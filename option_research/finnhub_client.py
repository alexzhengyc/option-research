"""Finnhub API client for fetching earnings calendar and related data.

This module provides utilities for:
- Fetching upcoming earnings announcements
- Finding the appropriate options expiry after earnings
- Filtering tickers by market cap, exchange, etc.

Usage:
    from option_research.finnhub_client import FinnhubClient
    
    client = FinnhubClient(api_key="your_key_here")
    earnings = client.get_upcoming_earnings(days_ahead=7)
    
    for event in earnings:
        print(f"{event['ticker']}: {event['earnings_date']}, expiry: {event['event_expiry']}")
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import finnhub
from dotenv import load_dotenv


@dataclass(slots=True)
class EarningsEvent:
    """Represents a single earnings announcement."""

    ticker: str
    earnings_date: str  # ISO format YYYY-MM-DD
    event_expiry: str  # ISO format YYYY-MM-DD (first Friday after earnings)
    eps_estimate: float | None = None
    revenue_estimate: float | None = None
    quarter: int | None = None
    year: int | None = None


class FinnhubClient:
    """Client for interacting with Finnhub API."""

    def __init__(self, api_key: str | None = None, auto_load_env: bool = True):
        """Initialize Finnhub client.
        
        Args:
            api_key: Finnhub API key. If not provided, attempts to read from
                     FINNHUB_API_KEY environment variable or .env file.
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
            api_key = os.environ.get("FINNHUB_API_KEY")
        
        if not api_key:
            raise ValueError(
                "Finnhub API key required. Pass as argument or set FINNHUB_API_KEY "
                "environment variable or create a .env file with:\n"
                "FINNHUB_API_KEY=your_key_here"
            )
        
        self.client = finnhub.Client(api_key=api_key)
        self.api_key = api_key

    def get_upcoming_earnings(
        self,
        days_ahead: int = 7,
        min_market_cap: float | None = None,
        exchanges: list[str] | None = None,
    ) -> list[EarningsEvent]:
        """Fetch upcoming earnings announcements.
        
        Args:
            days_ahead: Number of days to look ahead for earnings.
            min_market_cap: Optional minimum market cap filter (in dollars).
            exchanges: Optional list of exchanges to filter by (e.g., ["US", "NYSE"]).
        
        Returns:
            List of EarningsEvent objects with ticker, date, and suggested expiry.
        """
        from_date = datetime.now().strftime("%Y-%m-%d")
        to_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        try:
            response = self.client.earnings_calendar(
                _from=from_date,
                to=to_date,
                symbol="",  # Empty = all symbols
                international=False,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to fetch earnings calendar: {e}")
        
        raw_events = response.get("earningsCalendar", [])
        
        events: list[EarningsEvent] = []
        for event in raw_events:
            ticker = event.get("symbol")
            earnings_date = event.get("date")
            
            if not ticker or not earnings_date:
                continue
            
            # Skip if exchange filter is provided and doesn't match
            # (Finnhub doesn't provide exchange in calendar, so we skip this for now)
            
            # Compute event expiry (first Friday after earnings)
            event_expiry = self._get_earnings_expiry(earnings_date)
            
            events.append(
                EarningsEvent(
                    ticker=ticker,
                    earnings_date=earnings_date,
                    event_expiry=event_expiry,
                    eps_estimate=event.get("epsEstimate"),
                    revenue_estimate=event.get("revenueEstimate"),
                    quarter=event.get("quarter"),
                    year=event.get("year"),
                )
            )
        
        # Apply market cap filter if requested
        if min_market_cap is not None:
            events = self._filter_by_market_cap(events, min_market_cap)
        
        return events

    def get_earnings_for_ticker(self, ticker: str, days_ahead: int = 30) -> EarningsEvent | None:
        """Get next earnings date for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol.
            days_ahead: How far to look ahead.
        
        Returns:
            EarningsEvent if found, None otherwise.
        """
        events = self.get_upcoming_earnings(days_ahead=days_ahead)
        for event in events:
            if event.ticker.upper() == ticker.upper():
                return event
        return None

    def get_company_profile(self, ticker: str) -> dict[str, Any]:
        """Fetch company profile (market cap, industry, etc).
        
        Args:
            ticker: Stock ticker symbol.
        
        Returns:
            Dictionary with company details from Finnhub.
        """
        try:
            profile = self.client.company_profile2(symbol=ticker)
            return profile
        except Exception as e:
            raise RuntimeError(f"Failed to fetch profile for {ticker}: {e}")

    @staticmethod
    def _get_earnings_expiry(earnings_date: str) -> str:
        """Find first Friday after earnings date.
        
        Args:
            earnings_date: Earnings date in ISO format (YYYY-MM-DD).
        
        Returns:
            ISO date string of the first Friday on or after earnings date.
        """
        earn_dt = datetime.fromisoformat(earnings_date)
        
        # Friday is weekday 4 (Monday=0)
        days_until_friday = (4 - earn_dt.weekday()) % 7
        
        # If earnings is on Friday, go to next Friday
        if days_until_friday == 0:
            days_until_friday = 7
        
        friday = earn_dt + timedelta(days=days_until_friday)
        return friday.strftime("%Y-%m-%d")

    def _filter_by_market_cap(
        self, events: list[EarningsEvent], min_market_cap: float
    ) -> list[EarningsEvent]:
        """Filter events by minimum market cap.
        
        Note: This makes additional API calls per ticker, so use sparingly.
        
        Args:
            events: List of earnings events.
            min_market_cap: Minimum market cap in dollars.
        
        Returns:
            Filtered list of events.
        """
        filtered: list[EarningsEvent] = []
        
        for event in events:
            try:
                profile = self.get_company_profile(event.ticker)
                market_cap = profile.get("marketCapitalization", 0) * 1e6  # Finnhub returns in millions
                
                if market_cap >= min_market_cap:
                    filtered.append(event)
            except Exception:
                # If we can't fetch profile, skip this ticker
                continue
        
        return filtered

    def get_earnings_surprises(self, ticker: str, limit: int = 4) -> list[dict[str, Any]]:
        """Fetch historical earnings surprises for a ticker.
        
        Useful for computing D5 (historical consistency).
        
        Args:
            ticker: Stock ticker symbol.
            limit: Number of past earnings to fetch.
        
        Returns:
            List of dictionaries with actual/estimate EPS and dates.
        """
        try:
            surprises = self.client.company_earnings(symbol=ticker, limit=limit)
            return surprises
        except Exception as e:
            raise RuntimeError(f"Failed to fetch earnings history for {ticker}: {e}")


__all__ = ["FinnhubClient", "EarningsEvent"]

