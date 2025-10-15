"""
Tests for event and expiry selection logic
"""
from datetime import datetime, date, timedelta
import pytest
from lib.events import (
    find_event_and_neighbors,
    validate_event_expiries,
    get_expiry_ranges,
    filter_expiries_around_earnings
)


class TestFindEventAndNeighbors:
    """Test find_event_and_neighbors function"""
    
    def test_basic_event_selection(self):
        """Test basic event expiry selection"""
        earnings = datetime(2025, 10, 26, 16, 0)  # Oct 26 after market close
        expiries = [
            date(2025, 10, 18),
            date(2025, 10, 25),
            date(2025, 11, 1),
            date(2025, 11, 15)
        ]
        
        result = find_event_and_neighbors(earnings, expiries)
        
        assert result["event"] == date(2025, 11, 1)
        assert result["prev"] == date(2025, 10, 25)
        assert result["next"] == date(2025, 11, 15)
    
    def test_earnings_on_expiry_date(self):
        """Test when earnings falls exactly on an expiry date"""
        earnings = datetime(2025, 11, 1, 16, 0)
        expiries = [
            date(2025, 10, 25),
            date(2025, 11, 1),
            date(2025, 11, 8)
        ]
        
        result = find_event_and_neighbors(earnings, expiries)
        
        # Event should be the same-day expiry
        assert result["event"] == date(2025, 11, 1)
        assert result["prev"] == date(2025, 10, 25)
        assert result["next"] == date(2025, 11, 8)
    
    def test_no_prev_expiry(self):
        """Test when there's no expiry before earnings"""
        earnings = datetime(2025, 10, 15, 16, 0)
        expiries = [
            date(2025, 10, 18),
            date(2025, 10, 25),
            date(2025, 11, 1)
        ]
        
        result = find_event_and_neighbors(earnings, expiries)
        
        assert result["event"] == date(2025, 10, 18)
        assert result["prev"] is None
        assert result["next"] == date(2025, 10, 25)
    
    def test_no_next_expiry(self):
        """Test when there's no expiry after event"""
        earnings = datetime(2025, 10, 26, 16, 0)
        expiries = [
            date(2025, 10, 18),
            date(2025, 10, 25),
            date(2025, 11, 1)
        ]
        
        result = find_event_and_neighbors(earnings, expiries)
        
        assert result["event"] == date(2025, 11, 1)
        assert result["prev"] == date(2025, 10, 25)
        assert result["next"] is None
    
    def test_earnings_after_all_expiries(self):
        """Test when earnings is after all available expiries"""
        earnings = datetime(2025, 12, 1, 16, 0)
        expiries = [
            date(2025, 10, 18),
            date(2025, 10, 25),
            date(2025, 11, 1)
        ]
        
        result = find_event_and_neighbors(earnings, expiries)
        
        assert result["event"] is None
        assert result["prev"] is None
        assert result["next"] is None
    
    def test_empty_expiries_list(self):
        """Test with empty expiries list"""
        earnings = datetime(2025, 10, 26, 16, 0)
        expiries = []
        
        result = find_event_and_neighbors(earnings, expiries)
        
        assert result["event"] is None
        assert result["prev"] is None
        assert result["next"] is None
    
    def test_unsorted_expiries(self):
        """Test that function handles unsorted expiries"""
        earnings = datetime(2025, 10, 26, 16, 0)
        expiries = [
            date(2025, 11, 15),
            date(2025, 10, 18),
            date(2025, 11, 1),
            date(2025, 10, 25)
        ]
        
        result = find_event_and_neighbors(earnings, expiries)
        
        # Should still find correct expiries even if input is unsorted
        assert result["event"] == date(2025, 11, 1)
        assert result["prev"] == date(2025, 10, 25)
        assert result["next"] == date(2025, 11, 15)
    
    def test_morning_earnings(self):
        """Test with before-market-open earnings"""
        earnings = datetime(2025, 10, 26, 9, 0)  # Morning earnings
        expiries = [
            date(2025, 10, 25),
            date(2025, 10, 26),
            date(2025, 11, 1)
        ]
        
        result = find_event_and_neighbors(earnings, expiries)
        
        # Same-day expiry should be the event
        assert result["event"] == date(2025, 10, 26)
        assert result["prev"] == date(2025, 10, 25)
        assert result["next"] == date(2025, 11, 1)


class TestValidateEventExpiries:
    """Test validate_event_expiries function"""
    
    def test_valid_expiries(self):
        """Test validation with valid expiries"""
        earnings_date = date(2025, 10, 26)
        event = date(2025, 11, 1)  # 6 days after
        prev = date(2025, 10, 25)  # 1 day before
        next_exp = date(2025, 11, 8)  # 7 days after event
        
        validation = validate_event_expiries(event, prev, next_exp, earnings_date)
        
        assert validation["has_event"] is True
        assert validation["has_prev"] is True
        assert validation["has_next"] is True
        assert validation["event_dte_ok"] is True
        assert validation["is_valid"] is True
    
    def test_missing_event(self):
        """Test validation with missing event expiry"""
        earnings_date = date(2025, 10, 26)
        
        validation = validate_event_expiries(None, None, None, earnings_date)
        
        assert validation["has_event"] is False
        assert validation["is_valid"] is False
    
    def test_event_too_far_out(self):
        """Test validation when event expiry is too far from earnings"""
        earnings_date = date(2025, 10, 26)
        event = date(2026, 1, 1)  # 67 days after (too far)
        
        validation = validate_event_expiries(
            event, None, None, earnings_date, max_event_dte=60
        )
        
        assert validation["has_event"] is True
        assert validation["event_dte_ok"] is False
        assert validation["is_valid"] is False
    
    def test_event_within_limits(self):
        """Test validation when event is within acceptable DTE"""
        earnings_date = date(2025, 10, 26)
        event = date(2025, 11, 1)  # 6 days after
        
        validation = validate_event_expiries(
            event, None, None, earnings_date, max_event_dte=60
        )
        
        assert validation["event_dte_ok"] is True
        assert validation["is_valid"] is True


class TestGetExpiryRanges:
    """Test get_expiry_ranges function"""
    
    def test_all_expiries_present(self):
        """Test date ranges with all expiries"""
        event = date(2025, 11, 1)
        prev = date(2025, 10, 25)
        next_exp = date(2025, 11, 8)
        
        ranges = get_expiry_ranges(event, prev, next_exp)
        
        assert ranges["event"] == (prev, event)
        assert ranges["next"] == (event, next_exp)
        assert ranges["prev"] is not None
    
    def test_missing_prev(self):
        """Test date ranges with missing prev expiry"""
        event = date(2025, 11, 1)
        next_exp = date(2025, 11, 8)
        
        ranges = get_expiry_ranges(event, None, next_exp)
        
        # Should use default lookback
        assert ranges["event"][1] == event
        assert ranges["event"][0] < event
        assert ranges["next"] == (event, next_exp)
        assert ranges["prev"] is None
    
    def test_missing_next(self):
        """Test date ranges with missing next expiry"""
        event = date(2025, 11, 1)
        prev = date(2025, 10, 25)
        
        ranges = get_expiry_ranges(event, prev, None)
        
        assert ranges["event"] == (prev, event)
        assert ranges["prev"] is not None
        assert ranges["next"] is None


class TestFilterExpiriesAroundEarnings:
    """Test filter_expiries_around_earnings function"""
    
    def test_basic_filtering(self):
        """Test basic filtering with mock get_expiries function"""
        earnings_events = [
            {
                "symbol": "AAPL",
                "earnings_ts": datetime(2025, 10, 26, 16, 0)
            }
        ]
        
        # Mock function that returns expiries
        def mock_get_expiries(symbol):
            return [
                date(2025, 10, 18),
                date(2025, 10, 25),
                date(2025, 11, 1),
                date(2025, 11, 15)
            ]
        
        results = filter_expiries_around_earnings(
            earnings_events,
            mock_get_expiries
        )
        
        assert len(results) == 1
        result = results[0]
        
        assert result["symbol"] == "AAPL"
        assert result["expiries"]["event"] == date(2025, 11, 1)
        assert result["expiries"]["prev"] == date(2025, 10, 25)
        assert result["expiries"]["next"] == date(2025, 11, 15)
        assert result["validation"]["is_valid"] is True
    
    def test_filter_invalid_events(self):
        """Test that invalid events are filtered out"""
        earnings_events = [
            {
                "symbol": "AAPL",
                "earnings_ts": datetime(2025, 12, 1, 16, 0)  # After all expiries
            }
        ]
        
        def mock_get_expiries(symbol):
            return [
                date(2025, 10, 18),
                date(2025, 10, 25),
                date(2025, 11, 1)
            ]
        
        results = filter_expiries_around_earnings(
            earnings_events,
            mock_get_expiries
        )
        
        # Should be filtered out because no valid event expiry
        assert len(results) == 0
    
    def test_require_neighbors(self):
        """Test filtering with require_neighbors=True"""
        earnings_events = [
            {
                "symbol": "AAPL",
                "earnings_ts": datetime(2025, 10, 20, 16, 0)
            }
        ]
        
        def mock_get_expiries(symbol):
            # Only has event and next, no prev
            return [
                date(2025, 10, 25),
                date(2025, 11, 1)
            ]
        
        results = filter_expiries_around_earnings(
            earnings_events,
            mock_get_expiries,
            require_neighbors=True
        )
        
        # Should be filtered out because no prev expiry
        assert len(results) == 0
    
    def test_dte_calculation(self):
        """Test that DTE is calculated correctly"""
        earnings_events = [
            {
                "symbol": "AAPL",
                "earnings_ts": datetime(2025, 10, 26, 16, 0)
            }
        ]
        
        def mock_get_expiries(symbol):
            return [
                date(2025, 10, 25),
                date(2025, 11, 1),
                date(2025, 11, 15)
            ]
        
        results = filter_expiries_around_earnings(
            earnings_events,
            mock_get_expiries
        )
        
        assert len(results) == 1
        result = results[0]
        
        # Event is 6 days after earnings (Nov 1 - Oct 26)
        assert result["dte"]["event"] == 6
        # Prev is 1 day before earnings
        assert result["dte"]["prev"] == -1
        # Next is 14 days after event (Nov 15 - Nov 1)
        assert result["dte"]["next"] == 14


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

