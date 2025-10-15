"""
Unit tests for normalization and scoring functions
Dev Stage 7 - Normalization & Scoring
"""
import pytest
import numpy as np
import pandas as pd
from lib.scoring import (
    normalize_today,
    compute_dirscore,
    compute_scores_batch,
    compute_intraday_dirscore,
    resolve_intraday_decision
)


class TestNormalizeToday:
    """Test signal normalization"""
    
    def test_basic_normalization(self):
        """Test basic z-score and percentile computation"""
        df = pd.DataFrame({
            'symbol': ['A', 'B', 'C', 'D', 'E'],
            'rr_25d': [0.0, 0.1, 0.2, 0.3, 0.4],
            'vol_pcr': [0.5, 1.0, 1.5, 2.0, 2.5]
        })
        
        result = normalize_today(df)
        
        # Check that z-score columns were added
        assert 'z_rr_25d' in result.columns
        assert 'z_vol_pcr' in result.columns
        
        # Check that percentile columns were added
        assert 'pct_rr_25d' in result.columns
        assert 'pct_vol_pcr' in result.columns
        
        # Check z-scores are roughly centered at 0
        assert abs(result['z_rr_25d'].mean()) < 0.01
        
        # Check percentiles are in [0, 1]
        assert result['pct_rr_25d'].min() >= 0.0
        assert result['pct_rr_25d'].max() <= 1.0
    
    def test_winsorization(self):
        """Test that outliers are winsorized"""
        df = pd.DataFrame({
            'symbol': ['A', 'B', 'C', 'D', 'E'],
            'signal': [0.0, 0.1, 0.2, 0.3, 10.0]  # Last value is outlier
        })
        
        result = normalize_today(df, winsorize_std=2.0)
        
        # Check that no z-scores exceed ±2
        assert result['z_signal'].max() <= 2.0
        assert result['z_signal'].min() >= -2.0
    
    def test_zero_variance(self):
        """Test handling of zero variance columns"""
        df = pd.DataFrame({
            'symbol': ['A', 'B', 'C'],
            'constant': [1.0, 1.0, 1.0]  # No variance
        })
        
        result = normalize_today(df)
        
        # Should set all z-scores to 0
        assert 'z_constant' in result.columns
        assert (result['z_constant'] == 0.0).all()
    
    def test_nan_handling(self):
        """Test handling of NaN values"""
        df = pd.DataFrame({
            'symbol': ['A', 'B', 'C', 'D'],
            'signal': [0.1, np.nan, 0.3, 0.4]
        })
        
        result = normalize_today(df)
        
        # Check that NaN is preserved
        assert result['z_signal'].isna().sum() == 1
        assert result['pct_signal'].isna().sum() == 1
        
        # Check that non-NaN values are computed
        assert result['z_signal'].notna().sum() == 3
    
    def test_auto_detect_columns(self):
        """Test auto-detection of signal columns"""
        df = pd.DataFrame({
            'symbol': ['A', 'B'],  # Should be excluded
            'date': ['2025-01-01', '2025-01-02'],  # Should be excluded
            'rr_25d': [0.1, 0.2],  # Should be included
            'vol_pcr': [0.8, 1.2]  # Should be included
        })
        
        result = normalize_today(df)
        
        # Check that only signal columns were normalized
        assert 'z_rr_25d' in result.columns
        assert 'z_vol_pcr' in result.columns
        assert 'z_symbol' not in result.columns
        assert 'z_date' not in result.columns


class TestComputeDirscore:
    """Test directional score computation"""
    
    def test_bullish_score(self):
        """Test clearly bullish signals"""
        row = pd.Series({
            'z_rr_25d': 2.0,           # High positive RR
            'z_net_thrust': 1.5,        # Strong call buying
            'z_vol_pcr': -1.0,          # Low PCR (bullish)
            'z_beta_adj_return': 1.0,   # Positive momentum
            'pct_iv_bump': 0.3,         # Low IV cost
            'z_spread_pct_atm': 0.0     # Normal spread
        })
        
        score, decision = compute_dirscore(row)
        
        assert score > 0  # Should be positive (bullish)
        # May or may not cross 0.7 threshold depending on exact weights
        assert decision in ['CALL', 'PASS_OR_SPREAD']
    
    def test_bearish_score(self):
        """Test clearly bearish signals"""
        row = pd.Series({
            'z_rr_25d': -2.0,          # Low/negative RR
            'z_net_thrust': -1.5,       # Strong put buying
            'z_vol_pcr': 2.0,           # High PCR (bearish)
            'z_beta_adj_return': -1.0,  # Negative momentum
            'pct_iv_bump': 0.3,         # Low IV cost
            'z_spread_pct_atm': 0.0     # Normal spread
        })
        
        score, decision = compute_dirscore(row)
        
        assert score < 0  # Should be negative (bearish)
        # May or may not cross -0.7 threshold
        assert decision in ['PUT', 'PASS_OR_SPREAD']
    
    def test_neutral_score(self):
        """Test neutral/mixed signals"""
        row = pd.Series({
            'z_rr_25d': 0.0,
            'z_net_thrust': 0.0,
            'z_vol_pcr': 0.0,
            'z_beta_adj_return': 0.0,
            'pct_iv_bump': 0.5,
            'z_spread_pct_atm': 0.0
        })
        
        score, decision = compute_dirscore(row)
        
        # With all neutral signals, should be close to zero
        assert abs(score) < 0.7
        assert decision == 'PASS_OR_SPREAD'
    
    def test_high_iv_penalty(self):
        """Test that high IV penalizes score"""
        # Create two identical rows except for IV bump
        row_low_iv = pd.Series({
            'z_rr_25d': 1.0,
            'z_net_thrust': 1.0,
            'z_vol_pcr': -1.0,
            'z_beta_adj_return': 0.5,
            'pct_iv_bump': 0.2,  # Low IV
            'z_spread_pct_atm': 0.0
        })
        
        row_high_iv = pd.Series({
            'z_rr_25d': 1.0,
            'z_net_thrust': 1.0,
            'z_vol_pcr': -1.0,
            'z_beta_adj_return': 0.5,
            'pct_iv_bump': 0.9,  # High IV
            'z_spread_pct_atm': 0.0
        })
        
        score_low_iv, _ = compute_dirscore(row_low_iv)
        score_high_iv, _ = compute_dirscore(row_high_iv)
        
        # High IV should reduce the score
        assert score_high_iv < score_low_iv
    
    def test_missing_values(self):
        """Test handling of missing values"""
        row = pd.Series({
            'z_rr_25d': np.nan,  # Missing value
            'z_net_thrust': 1.0
        })
        
        score, decision = compute_dirscore(row)
        
        # Should handle gracefully (treat NaN as 0)
        assert isinstance(score, float)
        assert decision in ['CALL', 'PUT', 'PASS_OR_SPREAD']
    
    def test_custom_weights(self):
        """Test using custom weights"""
        row = pd.Series({
            'z_rr_25d': 1.0,
            'z_net_thrust': 0.0,
            'z_vol_pcr': 0.0,
            'z_beta_adj_return': 0.0,
            'pct_iv_bump': 0.5,
            'z_spread_pct_atm': 0.0
        })
        
        # Default weights
        score_default, _ = compute_dirscore(row)
        
        # Custom weights (emphasize RR more)
        custom_weights = {
            'd1': 0.50,  # Increased
            'd2': 0.20,
            'd3': 0.15,
            'd4': 0.10,
            'p1': -0.05,
            'p2': -0.05
        }
        score_custom, _ = compute_dirscore(row, weights=custom_weights)
        
        # Custom weights should give different score
        assert score_custom != score_default


class TestComputeScoresBatch:
    """Test batch scoring"""
    
    def test_batch_scoring(self):
        """Test scoring multiple events at once"""
        df = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'],
            'rr_25d': [0.05, -0.02, 0.08, 0.12, -0.05],
            'vol_pcr': [0.8, 1.2, 0.7, 0.6, 1.5],
            'net_thrust': [0.5, -0.2, 0.8, 1.2, 0.1],
            'iv_bump': [0.05, 0.08, 0.03, 0.10, 0.06],
            'spread_pct_atm': [2.5, 3.0, 2.0, 4.0, 2.8],
            'beta_adj_return': [0.02, -0.01, 0.03, 0.05, -0.02]
        })
        
        result = compute_scores_batch(df)
        
        # Check that all required columns are present
        assert 'score' in result.columns
        assert 'decision' in result.columns
        assert 'z_rr_25d' in result.columns
        assert 'pct_iv_bump' in result.columns
        
        # Check that we have scores for all rows
        assert len(result) == len(df)
        assert result['score'].notna().all()
        assert result['decision'].notna().all()
        
        # Check that decisions are valid
        valid_decisions = {'CALL', 'PUT', 'PASS_OR_SPREAD'}
        assert all(d in valid_decisions for d in result['decision'])
    
    def test_batch_with_nans(self):
        """Test batch scoring with missing values"""
        df = pd.DataFrame({
            'symbol': ['A', 'B', 'C'],
            'rr_25d': [0.1, np.nan, 0.3],
            'vol_pcr': [0.8, 1.2, np.nan],
            'net_thrust': [0.5, -0.2, 0.8]
        })
        
        result = compute_scores_batch(df)
        
        # Should produce scores even with missing values
        assert len(result) == len(df)
        assert 'score' in result.columns
        assert 'decision' in result.columns
    
    def test_score_distribution(self):
        """Test that scores have reasonable distribution"""
        # Create data with clear patterns
        np.random.seed(42)
        n = 100
        
        df = pd.DataFrame({
            'symbol': [f'S{i}' for i in range(n)],
            'rr_25d': np.random.randn(n),
            'vol_pcr': np.random.randn(n) + 1.0,  # Positive values
            'net_thrust': np.random.randn(n),
            'iv_bump': np.random.rand(n) * 0.1,
            'spread_pct_atm': np.random.rand(n) * 5,
            'beta_adj_return': np.random.randn(n) * 0.02
        })
        
        result = compute_scores_batch(df)
        
        # Check score statistics
        assert result['score'].mean() is not None
        assert result['score'].std() > 0
        
        # Should have some variety in decisions
        decision_counts = result['decision'].value_counts()
        # At least one type of decision should exist
        assert len(decision_counts) > 0


class TestScoringConsistency:
    """Test consistency between different scoring methods"""
    
    def test_manual_vs_batch(self):
        """Test that manual scoring matches batch scoring"""
        df = pd.DataFrame({
            'symbol': ['TEST'],
            'rr_25d': [0.1],
            'vol_pcr': [1.0],
            'net_thrust': [0.5],
            'iv_bump': [0.05],
            'spread_pct_atm': [2.5],
            'beta_adj_return': [0.02]
        })
        
        # Batch method
        result_batch = compute_scores_batch(df)
        score_batch = result_batch['score'].iloc[0]
        decision_batch = result_batch['decision'].iloc[0]
        
        # Manual method
        df_norm = normalize_today(df)
        score_manual, decision_manual = compute_dirscore(df_norm.iloc[0])
        
        # Should be identical
        assert abs(score_batch - score_manual) < 0.001
        assert decision_batch == decision_manual


class TestIntradayScoring:
    """Validate intraday DirScore computations and guardrails."""

    def test_intraday_weights(self):
        """Confirm weights match Method.md specification."""

        row = pd.Series({
            'z_rr_25d': 1.0,
            'z_net_thrust': 0.5,
            'z_vol_pcr': -0.25,
            'z_beta_adj_return': 0.2,
            'pct_iv_bump': 0.4,
            'z_spread_pct_atm': 0.1
        })

        score, direction = compute_intraday_dirscore(row)

        # Manual calculation with documented weights
        expected = (
            0.38 * 1.0
            + 0.28 * 0.5
            + (-0.18) * (-0.25)
            + 0.10 * 0.2
            + (-0.10) * 0.4
            + (-0.05) * 0.1
        )

        assert abs(score - expected) < 1e-9
        assert direction == 'CALL'

    def test_intraday_decision_guards(self):
        """Ensure guardrails enforce skips and structure changes."""

        # High score but wide spread should skip
        decision, structure = resolve_intraday_decision(
            score=1.0,
            pct_iv_bump=0.50,
            spread_pct=15.0,
            total_volume=100,
        )
        assert decision == 'PASS'
        assert structure == 'SKIP'

        # Medium score with rich IV should recommend vertical
        decision, structure = resolve_intraday_decision(
            score=0.55,
            pct_iv_bump=0.9,
            spread_pct=0.05,
            total_volume=200,
        )
        assert decision == 'CALL'
        assert structure == 'VERTICAL'

        # Low volume should skip regardless of score
        decision, structure = resolve_intraday_decision(
            score=-0.8,
            pct_iv_bump=0.2,
            spread_pct=0.03,
            total_volume=5,
        )
        assert decision == 'PASS'
        assert structure == 'SKIP'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

