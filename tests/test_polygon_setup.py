"""Tests for Polygon.io API client setup and basic functionality.

Run with:
    pytest tests/test_polygon_setup.py -v
    
Or without pytest:
    python tests/test_polygon_setup.py
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from option_research.polygon_client import PolygonClient, OptionContract


def test_client_initialization_with_key():
    """Test that client initializes with explicit API key."""
    # Use a dummy key for initialization test
    client = PolygonClient(api_key="test_key_12345", auto_load_env=False)
    assert client.api_key == "test_key_12345"


def test_client_initialization_from_env():
    """Test that client reads API key from environment variable."""
    # Set temporary env var
    os.environ["POLYGON_API_KEY"] = "env_test_key"
    
    try:
        client = PolygonClient(auto_load_env=False)
        assert client.api_key == "env_test_key"
    finally:
        # Clean up
        if "POLYGON_API_KEY" in os.environ:
            del os.environ["POLYGON_API_KEY"]


def test_client_raises_without_key():
    """Test that client raises ValueError when no API key is provided."""
    # Clear any existing env var
    old_key = os.environ.get("POLYGON_API_KEY")
    if "POLYGON_API_KEY" in os.environ:
        del os.environ["POLYGON_API_KEY"]
    
    try:
        try:
            PolygonClient(auto_load_env=False)
            assert False, "Expected ValueError but none was raised"
        except ValueError as e:
            assert "API key required" in str(e)
    finally:
        # Restore old key if it existed
        if old_key:
            os.environ["POLYGON_API_KEY"] = old_key


def test_get_earnings_expiry():
    """Test computation of first Friday after earnings."""
    # Test various day-of-week scenarios
    
    # Monday -> Friday (same week)
    assert PolygonClient.get_earnings_expiry("2024-04-15") == "2024-04-19"
    
    # Tuesday -> Friday (same week)
    assert PolygonClient.get_earnings_expiry("2024-04-16") == "2024-04-19"
    
    # Wednesday -> Friday (same week)
    assert PolygonClient.get_earnings_expiry("2024-04-17") == "2024-04-19"
    
    # Thursday -> Friday (next day)
    assert PolygonClient.get_earnings_expiry("2024-04-18") == "2024-04-19"
    
    # Friday -> next Friday (7 days)
    assert PolygonClient.get_earnings_expiry("2024-04-19") == "2024-04-26"
    
    # Saturday -> Friday (next week)
    assert PolygonClient.get_earnings_expiry("2024-04-20") == "2024-04-26"
    
    # Sunday -> Friday (same week)
    assert PolygonClient.get_earnings_expiry("2024-04-21") == "2024-04-26"


def test_option_contract_dataclass():
    """Test OptionContract dataclass creation."""
    contract = OptionContract(
        ticker="AAPL",
        contract_ticker="O:AAPL240419C00170000",
        expiry="2024-04-19",
        strike=170.0,
        option_type="call",
        bid=3.50,
        ask=3.60,
        last=3.55,
        volume=1000,
        open_interest=5000,
        implied_volatility=0.25,
        delta=0.50,
    )
    
    assert contract.ticker == "AAPL"
    assert contract.strike == 170.0
    assert contract.option_type == "call"
    assert contract.delta == 0.50


def test_find_contract_by_delta():
    """Test finding contract closest to target delta."""
    contracts = [
        OptionContract("AAPL", "O:AAPL240419C00160000", "2024-04-19", 160.0, "call", 5.0, 5.1, 5.05, 100, 500, 0.23, 0.65),
        OptionContract("AAPL", "O:AAPL240419C00170000", "2024-04-19", 170.0, "call", 3.5, 3.6, 3.55, 200, 1000, 0.25, 0.50),
        OptionContract("AAPL", "O:AAPL240419C00180000", "2024-04-19", 180.0, "call", 2.0, 2.1, 2.05, 150, 750, 0.27, 0.35),
        OptionContract("AAPL", "O:AAPL240419C00190000", "2024-04-19", 190.0, "call", 1.0, 1.1, 1.05, 100, 500, 0.29, 0.20),
    ]
    
    # Find 25Δ call (should get strike 190, delta 0.20 is closest to 0.25)
    result = PolygonClient._find_contract_by_delta(contracts, target_delta=0.25)
    assert result is not None
    assert result.delta == 0.20  # Closest to 0.25
    
    # Find 50Δ call (should get strike 170, delta 0.50)
    result = PolygonClient._find_contract_by_delta(contracts, target_delta=0.50)
    assert result is not None
    assert result.delta == 0.50


def test_compute_risk_reversal():
    """Test risk-reversal computation."""
    chain = [
        # Calls
        OptionContract("AAPL", "C1", "2024-04-19", 170.0, "call", 5.0, 5.1, 5.05, 100, 500, 0.30, 0.65),
        OptionContract("AAPL", "C2", "2024-04-19", 180.0, "call", 3.5, 3.6, 3.55, 200, 1000, 0.28, 0.50),
        OptionContract("AAPL", "C3", "2024-04-19", 190.0, "call", 2.0, 2.1, 2.05, 150, 750, 0.26, 0.25),
        # Puts
        OptionContract("AAPL", "P1", "2024-04-19", 150.0, "put", 2.0, 2.1, 2.05, 120, 600, 0.32, -0.25),
        OptionContract("AAPL", "P2", "2024-04-19", 160.0, "put", 3.5, 3.6, 3.55, 180, 900, 0.34, -0.50),
        OptionContract("AAPL", "P3", "2024-04-19", 170.0, "put", 5.0, 5.1, 5.05, 150, 800, 0.36, -0.65),
    ]
    
    client = PolygonClient(api_key="test_key", auto_load_env=False)
    rr = client._compute_risk_reversal(chain)
    
    # RR = IV(call_25Δ) - IV(put_25Δ) = 0.26 - 0.32 = -0.06
    assert abs(rr - (-0.06)) < 0.001


# If running directly (not via pytest)
if __name__ == "__main__":
    print("Running Polygon client tests...\n")
    
    tests = [
        ("Client initialization with key", test_client_initialization_with_key),
        ("Client initialization from env", test_client_initialization_from_env),
        ("Client raises without key", test_client_raises_without_key),
        ("Get earnings expiry", test_get_earnings_expiry),
        ("OptionContract dataclass", test_option_contract_dataclass),
        ("Find contract by delta", test_find_contract_by_delta),
        ("Compute risk-reversal", test_compute_risk_reversal),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}")
            passed += 1
        except Exception as e:
            print(f"✗ {name}: {e}")
            failed += 1
    
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)

