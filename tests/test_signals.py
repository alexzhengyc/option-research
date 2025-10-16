"""
Unit tests for signal computation functions
Dev Stage 6 - Signal Math
"""
import pytest
import numpy as np
import pandas as pd
from datetime import date, timedelta
from lib.signals import (
    interp_iv_at_delta,
    atm_iv,
    compute_rr_25d,
    compute_pcr,
    compute_volume_thrust,
    compute_iv_bump,
    compute_spread_pct_atm,
    compute_all_signals
)


class TestInterpIVAtDelta:
    """Test IV interpolation at target delta"""
    
    def test_basic_interpolation(self):
        """Test basic linear interpolation"""
        contracts = [
            {
                "details": {"contract_type": "call"},
                "greeks": {"delta": 0.20},
                "implied_volatility": 0.30
            },
            {
                "details": {"contract_type": "call"},
                "greeks": {"delta": 0.30},
                "implied_volatility": 0.35
            }
        ]
        
        # Should interpolate to 0.325 at delta=0.25
        result = interp_iv_at_delta(contracts, target_delta=0.25, side="call")
        assert result is not None
        assert 0.30 <= result <= 0.35
        assert abs(result - 0.325) < 0.01
    
    def test_no_contracts(self):
        """Test with no contracts"""
        result = interp_iv_at_delta([], target_delta=0.25, side="call")
        assert result is None
    
    def test_insufficient_data(self):
        """Test with only one data point"""
        contracts = [
            {
                "details": {"contract_type": "call"},
                "greeks": {"delta": 0.25},
                "implied_volatility": 0.30
            }
        ]
        
        result = interp_iv_at_delta(contracts, target_delta=0.25, side="call")
        assert result is None
    
    def test_out_of_range(self):
        """Test extrapolation when target is outside range"""
        contracts = [
            {
                "details": {"contract_type": "call"},
                "greeks": {"delta": 0.30},
                "implied_volatility": 0.30
            },
            {
                "details": {"contract_type": "call"},
                "greeks": {"delta": 0.40},
                "implied_volatility": 0.35
            }
        ]
        
        # Target below range
        result = interp_iv_at_delta(contracts, target_delta=0.10, side="call")
        assert result is not None
        assert result == 0.30  # Should return nearest value


class TestATMIV:
    """Test ATM IV computation"""
    
    def test_basic_atm(self):
        """Test basic ATM IV calculation"""
        contracts = [
            {
                "details": {"contract_type": "call", "strike_price": 148},
                "implied_volatility": 0.30
            },
            {
                "details": {"contract_type": "call", "strike_price": 152},
                "implied_volatility": 0.32
            },
            {
                "details": {"contract_type": "put", "strike_price": 148},
                "implied_volatility": 0.31
            },
            {
                "details": {"contract_type": "put", "strike_price": 152},
                "implied_volatility": 0.33
            }
        ]
        
        result = atm_iv(contracts, spot_price=150.0)
        assert result is not None
        assert 0.30 <= result <= 0.33
    
    def test_no_spot_price(self):
        """Test when spot price must be extracted"""
        contracts = [
            {
                "details": {"contract_type": "call", "strike_price": 150},
                "implied_volatility": 0.30,
                "underlying_asset": {"price": 150.0}
            }
        ]
        
        result = atm_iv(contracts)
        # Should handle extraction or return None gracefully
        assert result is None or isinstance(result, float)

    def test_accepts_legacy_strike_key(self):
        """ATM IV should handle Polygon contracts with 'strike' key"""
        contracts = [
            {
                "details": {"contract_type": "call", "strike": 149},
                "implied_volatility": 0.31
            },
            {
                "details": {"contract_type": "call", "strike": 151},
                "implied_volatility": 0.33
            },
            {
                "details": {"contract_type": "put", "strike": 149},
                "implied_volatility": 0.32
            },
            {
                "details": {"contract_type": "put", "strike": 151},
                "implied_volatility": 0.34
            }
        ]

        result = atm_iv(contracts, spot_price=150.0)
        assert result is not None
        assert 0.31 <= result <= 0.34


class TestComputeRR25D:
    """Test 25-delta risk reversal computation"""
    
    def test_basic_rr(self):
        """Test basic RR calculation"""
        contracts = [
            {
                "details": {"contract_type": "call"},
                "greeks": {"delta": 0.25},
                "implied_volatility": 0.35
            },
            {
                "details": {"contract_type": "call"},
                "greeks": {"delta": 0.30},
                "implied_volatility": 0.36
            },
            {
                "details": {"contract_type": "put"},
                "greeks": {"delta": -0.25},
                "implied_volatility": 0.32
            },
            {
                "details": {"contract_type": "put"},
                "greeks": {"delta": -0.20},
                "implied_volatility": 0.31
            }
        ]
        
        result = compute_rr_25d(contracts)
        assert result is not None
        # RR = IV(25Δ call) - IV(25Δ put)
        # Should be positive (bullish skew) in this case
        assert result > 0
    
    def test_insufficient_data(self):
        """Test with insufficient data"""
        result = compute_rr_25d([])
        assert result is None


class TestComputePCR:
    """Test put-call ratio computation"""
    
    def test_basic_pcr(self):
        """Test basic PCR calculation"""
        contracts = [
            {
                "details": {"contract_type": "call", "strike_price": 150},
                "day": {"volume": 100},
                "last_trade": {"price": 5.0}
            },
            {
                "details": {"contract_type": "put", "strike_price": 150},
                "day": {"volume": 80},
                "last_trade": {"price": 4.5}
            }
        ]
        
        result = compute_pcr(contracts)
        
        assert result['vol_pcr'] is not None
        assert result['notional_pcr'] is not None
        
        # Volume PCR = 80/100 = 0.8
        assert abs(result['vol_pcr'] - 0.8) < 0.01
        
        # Notional PCR = (80*4.5*100) / (100*5.0*100) = 0.72
        assert abs(result['notional_pcr'] - 0.72) < 0.01
    
    def test_no_calls(self):
        """Test with no call volume"""
        contracts = [
            {
                "details": {"contract_type": "put"},
                "day": {"volume": 100},
                "last_trade": {"price": 5.0}
            }
        ]
        
        result = compute_pcr(contracts)
        assert result['vol_pcr'] is None
        assert result['notional_pcr'] is None


class TestComputeVolumeThrust:
    """Test volume thrust computation"""
    
    def test_basic_thrust(self):
        """Test basic thrust calculation"""
        contracts = [
            {
                "details": {"contract_type": "call"},
                "day": {"volume": 150}
            },
            {
                "details": {"contract_type": "put"},
                "day": {"volume": 90}
            }
        ]
        
        med20 = {
            "call_med20": 100,
            "put_med20": 100
        }
        
        result = compute_volume_thrust(contracts, med20)
        
        assert result['call_thrust'] is not None
        assert result['put_thrust'] is not None
        assert result['net_thrust'] is not None
        
        # Call thrust = (150-100)/100 = 0.50
        assert abs(result['call_thrust'] - 0.50) < 0.01
        
        # Put thrust = (90-100)/100 = -0.10
        assert abs(result['put_thrust'] - (-0.10)) < 0.01
        
        # Net thrust = 0.50 - (-0.10) = 0.60
        assert abs(result['net_thrust'] - 0.60) < 0.01


class TestComputeIVBump:
    """Test IV bump computation"""
    
    def test_basic_bump(self):
        """Test basic IV bump calculation"""
        result = compute_iv_bump(
            atm_event=0.35,
            atm_prev=0.25,
            atm_next=0.28
        )
        
        # Bump = 0.35 - avg(0.25, 0.28) = 0.35 - 0.265 = 0.085
        assert result is not None
        assert abs(result - 0.085) < 0.001
    
    def test_one_neighbor(self):
        """Test with only one neighbor"""
        result = compute_iv_bump(
            atm_event=0.35,
            atm_prev=0.25,
            atm_next=None
        )
        
        # Bump = 0.35 - 0.25 = 0.10
        assert result is not None
        assert abs(result - 0.10) < 0.001
    
    def test_no_neighbors(self):
        """Test with no neighbors"""
        result = compute_iv_bump(
            atm_event=0.35,
            atm_prev=None,
            atm_next=None
        )
        
        assert result is None


class TestComputeSpreadPctATM:
    """Test ATM spread computation"""
    
    def test_basic_spread(self):
        """Test basic spread calculation"""
        contracts = [
            {
                "details": {"strike_price": 150},
                "last_quote": {"bid": 4.80, "ask": 5.20},
                "underlying_asset": {"price": 150.0}
            },
            {
                "details": {"strike_price": 151},
                "last_quote": {"bid": 4.90, "ask": 5.10},
                "underlying_asset": {"price": 150.0}
            }
        ]
        
        result = compute_spread_pct_atm(contracts, spot_price=150.0)
        
        assert result is not None
        # First contract: (5.20-4.80)/5.00 * 100 = 8%
        # Second contract: (5.10-4.90)/5.00 * 100 = 4%
        # Average ≈ 6%
        assert 4.0 <= result <= 10.0
    
    def test_no_atm_contracts(self):
        """Test with no ATM contracts"""
        contracts = [
            {
                "details": {"strike_price": 200},  # Far from ATM
                "last_quote": {"bid": 1.0, "ask": 1.1},
                "underlying_asset": {"price": 150.0}
            }
        ]
        
        result = compute_spread_pct_atm(contracts, spot_price=150.0)
        assert result is None

    def test_spread_legacy_strike_key(self):
        """Spread computation should handle 'strike' fallback"""
        contracts = [
            {
                "details": {"strike": 149},
                "last_quote": {"bid": 4.8, "ask": 5.2},
                "underlying_asset": {"price": 150.0}
            },
            {
                "details": {"strike": 151},
                "last_quote": {"bid": 4.9, "ask": 5.1},
                "underlying_asset": {"price": 150.0}
            }
        ]

        result = compute_spread_pct_atm(contracts, spot_price=150.0)
        assert result is not None
        assert 4.0 <= result <= 10.0


class TestComputeAllSignals:
    """Test comprehensive signal computation"""
    
    def test_all_signals_basic(self):
        """Test computing all signals together"""
        event_contracts = [
            {
                "details": {"contract_type": "call", "strike_price": 150},
                "greeks": {"delta": 0.25},
                "implied_volatility": 0.35,
                "day": {"volume": 100},
                "last_trade": {"price": 5.0},
                "last_quote": {"bid": 4.80, "ask": 5.20},
                "underlying_asset": {"price": 150.0}
            },
            {
                "details": {"contract_type": "put", "strike_price": 150},
                "greeks": {"delta": -0.25},
                "implied_volatility": 0.32,
                "day": {"volume": 80},
                "last_trade": {"price": 4.5},
                "last_quote": {"bid": 4.30, "ask": 4.70},
                "underlying_asset": {"price": 150.0}
            }
        ]
        
        med20 = {"call_med20": 50, "put_med20": 50}
        
        signals = compute_all_signals(
            symbol="TEST",
            event_date=date.today(),
            event_contracts=event_contracts,
            med20_volumes=med20
        )
        
        # Check that key signals are computed
        assert 'rr_25d' in signals
        assert 'vol_pcr' in signals
        assert 'call_thrust' in signals
        assert 'atm_iv_event' in signals
        
        # Check that values are reasonable
        if signals['rr_25d'] is not None:
            assert -1.0 <= signals['rr_25d'] <= 1.0
        
        if signals['vol_pcr'] is not None:
            assert signals['vol_pcr'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
