"""
Directional scoring model for call vs put trades
Based on the methodology in Method.md

Dev Stage 7 - Normalization & Scoring
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from scipy import stats


@dataclass
class DirectionalScore:
    """Container for directional score and components"""
    ticker: str
    dir_score: float
    direction: str  # 'CALL' or 'PUT'
    conviction: str  # 'HIGH', 'MEDIUM', 'LOW', 'SKIP'
    structure: str  # 'NAKED', 'VERTICAL', 'SKIP'
    
    # Signal components
    d1_skew: float = 0.0
    d2_flow: float = 0.0
    d3_pcr: float = 0.0
    d4_momentum: float = 0.0
    d5_consistency: float = 0.0
    p1_iv_cost: float = 0.0
    p2_spread: float = 0.0


@dataclass
class IntradayScore:
    """Container for intraday directional score snapshots."""

    symbol: str
    asof_ts: datetime
    dir_score_now: float
    dir_score_ewma: float
    decision: str
    structure: str
    direction: str

    z_rr_25d: float = 0.0
    z_net_thrust: float = 0.0
    z_vol_pcr: float = 0.0
    z_beta_adj_return: float = 0.0
    pct_iv_bump: float = 0.5
    z_spread_pct_atm: float = 0.0


class DirectionalScorer:
    """
    Computes directional scores for options trading
    
    Weights:
    - D1 (Skew/RR): 0.32
    - D2 (Net Flow): 0.28
    - D3 (PCR): 0.18
    - D4 (Momentum): 0.12
    - D5 (Consistency): 0.10
    - P1 (IV Cost): -0.10
    - P2 (Spread): -0.05
    """
    
    WEIGHTS = {
        'd1': 0.32,
        'd2': 0.28,
        'd3': 0.18,
        'd4': 0.12,
        'd5': 0.10,
        'p1': -0.10,
        'p2': -0.05,
    }
    
    @staticmethod
    def compute_z_score(value: float, values: np.ndarray) -> float:
        """Compute z-score for a value given a distribution"""
        if len(values) == 0:
            return 0.0
        
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            return 0.0
        
        return (value - mean) / std
    
    @staticmethod
    def compute_percentile(value: float, values: np.ndarray) -> float:
        """Compute percentile rank for a value (0-100)"""
        if len(values) == 0:
            return 50.0
        
        return (np.sum(values <= value) / len(values)) * 100
    
    def compute_d1_skew(self, rr_25delta: float, historical_rr: np.ndarray) -> float:
        """
        D1: Risk reversal (25Δ call IV - 25Δ put IV)
        Higher → bullish tilt
        """
        return self.compute_z_score(rr_25delta, historical_rr)
    
    def compute_d2_net_flow(
        self,
        delta_oi_calls: float,
        delta_oi_puts: float,
        delta_vol_calls: float,
        delta_vol_puts: float,
        historical_oi: np.ndarray,
        historical_vol: np.ndarray,
    ) -> float:
        """
        D2: Net flow imbalance (OI + volume thrust)
        Positive → bullish, negative → bearish
        """
        oi_net = delta_oi_calls - delta_oi_puts
        vol_net = delta_vol_calls - delta_vol_puts
        
        z_oi = self.compute_z_score(oi_net, historical_oi)
        z_vol = self.compute_z_score(vol_net, historical_vol)
        
        return z_oi + 0.5 * z_vol
    
    def compute_d3_pcr(self, pcr: float, historical_pcr: np.ndarray) -> float:
        """
        D3: Put-call ratio (volume-based)
        Lower PCR → bullish, so we negate the z-score
        """
        return -self.compute_z_score(pcr, historical_pcr)
    
    def compute_d4_momentum(
        self,
        stock_return: float,
        sector_return: float,
        beta: float,
        historical_returns: np.ndarray,
    ) -> float:
        """
        D4: Short-term price momentum (beta-adjusted)
        3-5 day return vs sector
        """
        beta_adj_return = stock_return - beta * sector_return
        return self.compute_z_score(beta_adj_return, historical_returns)
    
    def compute_d5_consistency(
        self,
        historical_rr_signs: List[int],
        historical_returns: List[float],
    ) -> float:
        """
        D5: Historical consistency of skew signal
        Correlation between RR sign and next-day returns
        Rescaled to [-2, +2]
        """
        if len(historical_rr_signs) < 4:
            return 0.0
        
        correlation = np.corrcoef(historical_rr_signs, historical_returns)[0, 1]
        
        if np.isnan(correlation):
            return 0.0
        
        return correlation * 2.0
    
    def compute_p1_iv_cost(
        self,
        current_iv_bump: float,
        historical_iv_bumps: np.ndarray,
    ) -> float:
        """
        P1: IV cost penalty (how rich is the event node)
        Higher percentile → higher penalty
        Normalize to 0-2 scale
        """
        percentile = self.compute_percentile(current_iv_bump, historical_iv_bumps)
        return percentile / 50.0  # Scale to ~0-2 range
    
    def compute_p2_spread(
        self,
        bid_ask_spread_pct: float,
        typical_spreads: np.ndarray,
    ) -> float:
        """
        P2: Liquidity/spread penalty
        Wider spreads → higher penalty
        """
        return self.compute_z_score(bid_ask_spread_pct, typical_spreads)
    
    def compute_score(
        self,
        ticker: str,
        d1: float = 0.0,
        d2: float = 0.0,
        d3: float = 0.0,
        d4: float = 0.0,
        d5: float = 0.0,
        p1: float = 0.0,
        p2: float = 0.0,
    ) -> DirectionalScore:
        """
        Compute final directional score
        
        Returns:
            DirectionalScore object with score, direction, and recommendations
        """
        # Compute weighted score
        dir_score = (
            self.WEIGHTS['d1'] * d1 +
            self.WEIGHTS['d2'] * d2 +
            self.WEIGHTS['d3'] * d3 +
            self.WEIGHTS['d4'] * d4 +
            self.WEIGHTS['d5'] * d5 +
            self.WEIGHTS['p1'] * p1 +
            self.WEIGHTS['p2'] * p2
        )
        
        # Determine direction
        direction = 'CALL' if dir_score > 0 else 'PUT'
        
        # Determine conviction
        abs_score = abs(dir_score)
        if abs_score >= 0.6:
            conviction = 'HIGH'
        elif abs_score >= 0.4:
            conviction = 'MEDIUM'
        else:
            conviction = 'LOW'
        
        # Determine structure based on IV cost
        p1_percentile = p1 * 50.0  # Convert back to percentile
        if p1_percentile <= 60:
            structure = 'NAKED'
        elif p1_percentile <= 85:
            structure = 'VERTICAL'
        else:
            structure = 'SKIP'
        
        # Override structure if conviction is too low
        if conviction == 'LOW':
            structure = 'SKIP'
        
        return DirectionalScore(
            ticker=ticker,
            dir_score=dir_score,
            direction=direction,
            conviction=conviction,
            structure=structure,
            d1_skew=d1,
            d2_flow=d2,
            d3_pcr=d3,
            d4_momentum=d4,
            d5_consistency=d5,
            p1_iv_cost=p1,
            p2_spread=p2,
        )


# ============================================================================
# Intraday scoring helpers (Method.md intraday playbook)
# ============================================================================


def compute_intraday_dirscore(
    row: pd.Series,
    weights: Optional[Dict[str, float]] = None,
) -> Tuple[float, str]:
    """Compute intraday directional score using nowcast weights."""

    if weights is None:
        weights = {
            "d1": 0.38,
            "d2": 0.28,
            "d3": -0.18,
            "d4": 0.10,
            "p1": -0.10,
            "p2": -0.05,
        }

    d1 = row.get("z_rr_25d", 0.0)
    d2 = row.get("z_net_thrust", 0.0)
    d3 = row.get("z_vol_pcr", 0.0)
    d4 = row.get("z_beta_adj_return", 0.0)
    p1 = row.get("pct_iv_bump", 0.5)
    p2 = row.get("z_spread_pct_atm", 0.0)

    d1 = 0.0 if pd.isna(d1) else d1
    d2 = 0.0 if pd.isna(d2) else d2
    d3 = 0.0 if pd.isna(d3) else d3
    d4 = 0.0 if pd.isna(d4) else d4
    p1 = 0.5 if pd.isna(p1) else p1
    p2 = 0.0 if pd.isna(p2) else p2

    score = (
        weights["d1"] * d1
        + weights["d2"] * d2
        + weights["d3"] * d3
        + weights["d4"] * d4
        + weights["p1"] * p1
        + weights["p2"] * p2
    )

    direction = "CALL" if score >= 0 else "PUT"
    return score, direction


def resolve_intraday_decision(
    score: float,
    pct_iv_bump: Optional[float],
    spread_pct: Optional[float],
    total_volume: Optional[float],
) -> Tuple[str, str]:
    """Determine decision/structure for intraday scores with guardrails."""

    if total_volume is not None and not pd.isna(total_volume):
        if total_volume < 10:
            return "PASS", "SKIP"

    if spread_pct is not None and not pd.isna(spread_pct):
        if spread_pct > 10:
            return "PASS", "SKIP"

    abs_score = abs(score)
    if abs_score < 0.40:
        return "PASS", "SKIP"

    direction = "CALL" if score >= 0 else "PUT"

    if abs_score < 0.60:
        decision = direction
        structure = "VERTICAL"
    else:
        decision = direction
        structure = "NAKED"

    if pct_iv_bump is not None and not pd.isna(pct_iv_bump):
        if pct_iv_bump >= 0.80:
            structure = "VERTICAL"

    return decision, structure


# ============================================================================
# Dev Stage 7 - Normalization & Scoring Functions
# ============================================================================


def normalize_today(
    df: pd.DataFrame,
    signal_columns: Optional[List[str]] = None,
    winsorize_std: float = 2.0
) -> pd.DataFrame:
    """
    Normalize signals using z-scores and percentiles, winsorize outliers
    
    This function:
    1. Computes z-scores for each signal
    2. Computes percentile ranks (0-1 scale)
    3. Winsorizes z-scores to ±winsorize_std
    
    Args:
        df: DataFrame with raw signals
        signal_columns: List of columns to normalize (if None, auto-detect)
        winsorize_std: Standard deviations to winsorize to (default: 2.0)
    
    Returns:
        DataFrame with additional normalized columns:
        - z_{signal_name} for z-scores
        - pct_{signal_name} for percentiles (0-1)
    
    Example:
        >>> # df has columns: symbol, rr_25d, vol_pcr, net_thrust, etc.
        >>> df_norm = normalize_today(df)
        >>> # Now has z_rr_25d, pct_rr_25d, z_vol_pcr, pct_vol_pcr, etc.
    """
    if signal_columns is None:
        # Auto-detect signal columns (exclude metadata columns)
        exclude_cols = {
            'symbol', 'ticker', 'date', 'earnings_date', 'event_date',
            'expiry', 'expiration_date'
        }
        signal_columns = [
            col for col in df.columns
            if col not in exclude_cols
            and not col.startswith('z_')
            and not col.startswith('pct_')
        ]
    
    df_norm = df.copy()
    
    for col in signal_columns:
        if col not in df.columns:
            continue
        
        # Skip if all NaN
        if df[col].isna().all():
            df_norm[f'z_{col}'] = np.nan
            df_norm[f'pct_{col}'] = np.nan
            continue
        
        # Get non-NaN values
        values = df[col].dropna()
        
        if len(values) == 0:
            df_norm[f'z_{col}'] = np.nan
            df_norm[f'pct_{col}'] = np.nan
            continue
        
        # Compute z-scores
        mean = values.mean()
        std = values.std()
        
        if std == 0 or np.isnan(std):
            # No variance, set all to 0
            df_norm[f'z_{col}'] = 0.0
        else:
            z_scores = (df[col] - mean) / std
            # Winsorize to ±winsorize_std
            z_scores = z_scores.clip(-winsorize_std, winsorize_std)
            df_norm[f'z_{col}'] = z_scores
        
        # Compute percentiles (0-1 scale)
        # Use rank with method='average' to handle ties
        percentiles = df[col].rank(pct=True, method='average')
        df_norm[f'pct_{col}'] = percentiles
    
    return df_norm


def compute_dirscore(
    row: pd.Series,
    weights: Optional[Dict[str, float]] = None
) -> Tuple[float, str]:
    """
    Compute directional score and decision for a single row
    
    Default weights (as specified in Dev Stage 7):
    - D1 (RR 25Δ): 0.32
    - D2 (Vol imbalance): 0.28
    - D3 (PCR): 0.18
    - D4 (Momentum): 0.12
    - P1 (IV bump): -0.10
    - P2 (Spread): -0.05
    
    Decision thresholds:
    - score >= 0.6: CALL
    - score <= -0.6: PUT
    - otherwise: PASS_OR_SPREAD
    
    Args:
        row: Series with normalized signals (z_* and pct_* columns)
        weights: Optional custom weights dict
    
    Returns:
        Tuple of (score, decision)
    
    Example:
        >>> df_norm = normalize_today(df)
        >>> df_norm[['score', 'decision']] = df_norm.apply(
        ...     lambda row: pd.Series(compute_dirscore(row)),
        ...     axis=1
        ... )
    """
    if weights is None:
        weights = {
            'd1': 0.32,   # RR 25Δ
            'd2': 0.28,   # Vol imbalance
            'd3': 0.18,   # PCR (inverted)
            'd4': 0.12,   # Momentum
            'p1': -0.10,  # IV bump
            'p2': -0.05,  # Spread
        }
    
    # Extract components (with defaults to 0 if missing)
    d1 = row.get('z_rr_25d', 0.0) if not pd.isna(row.get('z_rr_25d')) else 0.0
    
    # D2: Flow imbalance combining ΔOI and ΔVol
    z_oi = row.get('z_delta_oi_net', 0.0) if not pd.isna(row.get('z_delta_oi_net')) else 0.0

    if 'z_net_thrust' in row and not pd.isna(row.get('z_net_thrust')):
        z_vol = row['z_net_thrust']
    elif 'z_call_thrust' in row and 'z_put_thrust' in row:
        call_thrust = row.get('z_call_thrust', 0.0) if not pd.isna(row.get('z_call_thrust')) else 0.0
        put_thrust = row.get('z_put_thrust', 0.0) if not pd.isna(row.get('z_put_thrust')) else 0.0
        z_vol = call_thrust - put_thrust
    else:
        z_vol = 0.0

    d2 = z_oi + 0.5 * z_vol
    
    # D3: PCR (lower PCR is bullish, so we negate)
    d3 = -row.get('z_vol_pcr', 0.0) if not pd.isna(row.get('z_vol_pcr')) else 0.0
    
    # D4: Beta-adjusted momentum
    d4 = row.get('z_beta_adj_return', 0.0) if not pd.isna(row.get('z_beta_adj_return')) else 0.0
    
    # P1: IV bump (use percentile, 0-1 scale)
    p1 = row.get('pct_iv_bump', 0.5) if not pd.isna(row.get('pct_iv_bump')) else 0.5
    
    # P2: Spread
    p2 = row.get('z_spread_pct_atm', 0.0) if not pd.isna(row.get('z_spread_pct_atm')) else 0.0
    
    # Compute weighted score
    score = (
        weights['d1'] * d1 +
        weights['d2'] * d2 +
        weights['d3'] * d3 +
        weights['d4'] * d4 +
        weights['p1'] * p1 +
        weights['p2'] * p2
    )
    
    # Determine decision
    if score >= 0.6:
        decision = "CALL"
    elif score <= -0.6:
        decision = "PUT"
    else:
        decision = "PASS_OR_SPREAD"
    
    return score, decision


def compute_scores_batch(
    df: pd.DataFrame,
    signal_columns: Optional[List[str]] = None,
    winsorize_std: float = 2.0,
    weights: Optional[Dict[str, float]] = None
) -> pd.DataFrame:
    """
    Convenience function to normalize and score a batch of events
    
    Combines normalize_today and compute_dirscore in one step
    
    Args:
        df: DataFrame with raw signals
        signal_columns: List of columns to normalize
        winsorize_std: Standard deviations for winsorization
        weights: Optional custom weights for scoring
    
    Returns:
        DataFrame with normalized signals, scores, and decisions
    
    Example:
        >>> # df has: symbol, rr_25d, vol_pcr, net_thrust, iv_bump, etc.
        >>> df_scored = compute_scores_batch(df)
        >>> print(df_scored[['symbol', 'score', 'decision']].head())
    """
    # Normalize
    df_norm = normalize_today(df, signal_columns, winsorize_std)
    
    # Compute scores
    scores_and_decisions = df_norm.apply(
        lambda row: pd.Series(compute_dirscore(row, weights)),
        axis=1
    )
    
    df_norm['score'] = scores_and_decisions[0]
    df_norm['decision'] = scores_and_decisions[1]
    
    return df_norm
