"""
Tests for data provider functions
"""
from datetime import date, datetime, timedelta
import pytest
from lib import (
    get_upcoming_earnings,
    get_expiries,
    get_chain_snapshot,
    get_underlying_agg,
    get_option_daily_oc
)


class TestFinnhubProvider:
    """Test Finnhub data provider functions"""
    
    def test_get_upcoming_earnings(self):
        """Test getting upcoming earnings dates"""
        symbols = ["AAPL", "MSFT", "GOOGL"]
        start = date.today()
        end = start + timedelta(days=30)
        
        results = get_upcoming_earnings(symbols, start, end)
        
        # Verify results structure
        assert isinstance(results, list)
        for item in results:
            assert "symbol" in item
            assert "earnings_ts" in item
            assert item["symbol"] in symbols
            assert isinstance(item["earnings_ts"], datetime)
    
    def test_get_upcoming_earnings_empty(self):
        """Test with symbols that have no upcoming earnings"""
        symbols = ["FAKESYM123"]
        start = date.today()
        end = start + timedelta(days=7)
        
        results = get_upcoming_earnings(symbols, start, end)
        assert isinstance(results, list)


class TestPolygonProvider:
    """Test Polygon data provider functions"""
    
    def test_get_expiries(self):
        """Test getting option expiration dates"""
        symbol = "SPY"
        
        expiries = get_expiries(symbol)
        
        # Verify results
        assert isinstance(expiries, list)
        assert len(expiries) > 0
        
        # Verify dates are sorted
        for i in range(len(expiries) - 1):
            assert expiries[i] < expiries[i + 1]
        
        # Verify all are date objects
        for expiry in expiries:
            assert isinstance(expiry, date)
    
    def test_get_chain_snapshot(self):
        """Test getting options chain snapshot"""
        symbol = "SPY"
        start_expiry = date.today()
        end_expiry = start_expiry + timedelta(days=60)
        
        contracts = get_chain_snapshot(symbol, start_expiry, end_expiry)
        
        # Verify results
        assert isinstance(contracts, list)
        
        if len(contracts) > 0:
            # Check structure of first contract
            contract = contracts[0]
            assert "details" in contract or "underlying_ticker" in contract
    
    def test_get_underlying_agg(self):
        """Test getting underlying stock aggregates"""
        symbol = "SPY"
        end = date.today()
        start = end - timedelta(days=30)
        
        bars = get_underlying_agg(symbol, start, end, timespan="day")
        
        # Verify results
        assert isinstance(bars, list)
        assert len(bars) > 0
        
        # Check structure of first bar
        bar = bars[0]
        assert "timestamp" in bar
        assert "open" in bar
        assert "high" in bar
        assert "low" in bar
        assert "close" in bar
        assert "volume" in bar
        
        # Verify data integrity
        assert bar["high"] >= bar["low"]
        assert bar["high"] >= bar["open"]
        assert bar["high"] >= bar["close"]
        assert bar["low"] <= bar["open"]
        assert bar["low"] <= bar["close"]
    
    def test_get_option_daily_oc(self):
        """Test getting daily option open/close data"""
        # Note: This test might fail if the specific option doesn't exist
        # or if the date is a weekend/holiday
        option_ticker = "O:SPY251219C00550000"
        test_date = date(2025, 10, 10)  # Use a specific past date
        
        data = get_option_daily_oc(option_ticker, test_date)
        
        # Data might be None if not available
        if data is not None:
            assert "date" in data
            assert "open" in data
            assert "close" in data
            assert "volume" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

