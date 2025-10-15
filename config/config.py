"""
Configuration settings for option research
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DB_DIR = PROJECT_ROOT / "db"
OUT_DIR = PROJECT_ROOT / "out"
JOBS_DIR = PROJECT_ROOT / "jobs"
LIB_DIR = PROJECT_ROOT / "lib"

# Ensure directories exist
DB_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)

# API Keys
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Timezone
TIMEZONE = os.getenv("TZ", "America/Los_Angeles")

# Scoring thresholds
SCORE_THRESHOLDS = {
    "high_conviction": 0.7,
    "medium_conviction": 0.4,
    "iv_percentile_naked": 60,
    "iv_percentile_vertical": 85,
}

# Risk parameters
RISK_PER_TRADE_PCT = 0.01  # 1% of equity per trade

# Data lookback periods (in trading days)
LOOKBACK_PERIODS = {
    "zscore_window": 252,  # 1 year for z-score calculations
    "momentum_days": 5,    # 3-5 day momentum
    "volume_median_days": 20,
    "min_earnings_history": 4,  # Minimum earnings events for D5
}

