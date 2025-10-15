"""
Option Research Library
Directional scoring model for call vs put trades
"""

__version__ = "0.1.0"

# Export data provider functions
from .finnhub_client import get_upcoming_earnings
from .polygon_client import (
    get_expiries,
    get_chain_snapshot,
    get_underlying_agg,
    get_option_daily_oc
)

# Export event/expiry selection functions
from .events import (
    find_event_and_neighbors,
    validate_event_expiries,
    get_expiry_ranges,
    filter_expiries_around_earnings
)

# Export signal computation functions (Dev Stage 6)
from .signals import (
    interp_iv_at_delta,
    atm_iv,
    compute_rr_25d,
    compute_pcr,
    compute_volume_thrust,
    compute_iv_bump,
    compute_spread_pct_atm,
    compute_mom_betaadj,
    compute_all_signals
)

# Export normalization and scoring functions (Dev Stage 7)
from .scoring import (
    DirectionalScore,
    DirectionalScorer,
    normalize_today,
    compute_dirscore,
    compute_scores_batch
)

__all__ = [
    # Data providers
    "get_upcoming_earnings",
    "get_expiries", 
    "get_chain_snapshot",
    "get_underlying_agg",
    "get_option_daily_oc",
    # Event selection
    "find_event_and_neighbors",
    "validate_event_expiries",
    "get_expiry_ranges",
    "filter_expiries_around_earnings",
    # Signal computation (Dev Stage 6)
    "interp_iv_at_delta",
    "atm_iv",
    "compute_rr_25d",
    "compute_pcr",
    "compute_volume_thrust",
    "compute_iv_bump",
    "compute_spread_pct_atm",
    "compute_mom_betaadj",
    "compute_all_signals",
    # Normalization and scoring (Dev Stage 7)
    "DirectionalScore",
    "DirectionalScorer",
    "normalize_today",
    "compute_dirscore",
    "compute_scores_batch"
]

