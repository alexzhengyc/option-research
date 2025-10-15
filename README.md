# Options Research - Directional Scoring System

A quantitative framework for scoring and ranking earnings-based options trading opportunities. This system computes signals from options market data and produces directional trading decisions (CALL/PUT/PASS).

## 🎯 Overview

This project implements a comprehensive signal-based scoring model for options trading around earnings events:

1. **Event Selection** - Identify earnings events and find optimal option expiries
2. **Data Collection** - Fetch options chains, greeks, and market data
3. **Signal Computation** - Calculate 8 core signals from options data
4. **Normalization** - Normalize signals using z-scores and percentiles
5. **Scoring** - Produce directional scores and trading decisions
6. **Production Pipeline** - Automated post-close job with database persistence

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/alexzheng/option-research.git
cd option-research

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package in editable mode
pip install -e .
```

### Set Up API Keys

Create a `.env` file:

```bash
# Polygon.io (options data)
POLYGON_API_KEY=your_polygon_key

# Finnhub (earnings calendar)
FINNHUB_API_KEY=your_finnhub_key

# Supabase (optional - for storing results)
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_key
```

### Production Usage (Stages 8 & 9)

**Automated Post-Close Job (Stage 8):**

```bash
# Run after market close (4:30 PM ET recommended)
python jobs/post_close.py

# Or for specific date
python jobs/post_close.py --date 2025-10-15
```

**What it does:**
1. Fetches upcoming earnings for your universe (14 days ahead)
2. Snapshots options chains to database (captures initial OI)
3. Computes signals and scores
4. Stores results to `eds.daily_signals` table
5. Exports predictions to `/out/predictions_YYYYMMDD.csv`

**Automated Pre-Market Job (Stage 9):**

```bash
# Run pre-market (8:30 AM ET recommended, after OI posts overnight)
python jobs/pre_market.py --update-scores

# Or for specific date
python jobs/pre_market.py --date 2025-10-15 --update-scores
```

**What it does:**
1. Re-snapshots yesterday's option contracts (captures updated OI after overnight settlement)
2. Computes ΔOI (Delta Open Interest) for ATM ±2 strikes
3. Stores ΔOI data to `eds.oi_deltas` table
4. Optionally recomputes DirScore with ΔOI folded into flow signals
5. Updates `eds.daily_signals` with enhanced scores

**Schedule Both Jobs:**
```bash
# Cron schedule for complete daily pipeline
# Post-close: 4:30 PM ET weekdays
30 16 * * 1-5 cd /path/to/option-research && python jobs/post_close.py

# Pre-market: 8:30 AM ET weekdays
30 8 * * 1-5 cd /path/to/option-research && python jobs/pre_market.py --update-scores
```

**Output:** `/out/predictions_20251015.csv`
```csv
symbol,earnings_date,event_date,score,decision,rr_25d,vol_pcr,...
NVDA,2025-10-18,2025-10-25,1.2543,CALL,0.0823,-0.89,...
TSLA,2025-10-19,2025-10-25,-0.9832,PUT,-0.0654,1.45,...
```

### Interactive Usage (Library)

```python
from lib import (
    get_upcoming_earnings,
    filter_expiries_around_earnings,
    get_expiries,
    get_chain_snapshot,
    compute_all_signals,
    compute_scores_batch
)
import pandas as pd
from datetime import date, timedelta

# 1. Find earnings events
symbols = ["AAPL", "MSFT", "GOOGL"]
start = date.today()
end = start + timedelta(days=30)

earnings = get_upcoming_earnings(symbols, start, end)

# 2. Filter for tradeable expiries
events = filter_expiries_around_earnings(
    earnings,
    get_expiries,
    max_event_dte=60
)

# 3. Compute signals for each event
signals_list = []
for event in events:
    symbol = event['symbol']
    expiries = event['expiries']
    
    # Get contract data
    event_contracts = get_chain_snapshot(
        symbol, expiries['event'], expiries['event']
    )
    
    # Compute signals
    signals = compute_all_signals(
        symbol=symbol,
        event_date=expiries['event'],
        event_contracts=event_contracts,
        med20_volumes={"call_med20": 5000, "put_med20": 3000}
    )
    signals['symbol'] = symbol
    signals_list.append(signals)

# 4. Score and rank
df = pd.DataFrame(signals_list)
df_scored = compute_scores_batch(df)

# 5. View top opportunities
calls = df_scored[df_scored['decision'] == 'CALL'].sort_values('score', ascending=False)
print("Top CALL opportunities:")
print(calls[['symbol', 'score', 'z_rr_25d', 'z_net_thrust']].head())
```

## 📊 Signal System

### Core Signals (Stage 6)

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| **RR 25Δ** | IV(25Δ call) - IV(25Δ put) | Positive = bullish skew |
| **PCR** | Put volume / Call volume | < 1 = bullish, > 1 = bearish |
| **Volume Thrust** | (Vol - Med20) / Med20 | Unusual call/put activity |
| **IV Bump** | Event IV - Avg(neighbors) | Event premium richness |
| **Spread** | (Ask - Bid) / Mid | Liquidity measure |
| **Beta-Adj Mom** | Return - β × Sector Return | Idiosyncratic momentum |

### Scoring Formula (Stage 7)

```
Score = 0.32×D1 + 0.28×D2 + 0.18×D3 + 0.12×D4 - 0.10×P1 - 0.05×P2
```

**Components:**
- **D1** (32%): Risk Reversal - Skew direction
- **D2** (28%): Net Thrust - Volume imbalance
- **D3** (18%): PCR (inverted) - Put/call ratio
- **D4** (12%): Beta-adj Momentum - Price trend
- **P1** (-10%): IV Bump - Cost penalty
- **P2** (-5%): Spread - Liquidity penalty

**Decisions:**
- `Score ≥ 0.7` → **CALL** (buy calls/spreads)
- `Score ≤ -0.7` → **PUT** (buy puts/spreads)  
- `-0.7 < Score < 0.7` → **PASS** (skip or complex structures)

## 📁 Project Structure

```
option-research/
├── lib/                          # Core library
│   ├── __init__.py              # Package exports
│   ├── events.py                # Event/expiry selection
│   ├── finnhub.py               # Earnings calendar provider
│   ├── finnhub_client.py        # Finnhub API client
│   ├── polygon.py               # Options data provider
│   ├── polygon_client.py        # Polygon API client
│   ├── signals.py               # Signal computation (Stage 6)
│   ├── scoring.py               # Normalization & scoring (Stage 7)
│   ├── supa.py                  # Supabase helpers
│   └── supabase_client.py       # Supabase client
│
├── examples/                     # Usage examples
│   ├── data_provider_example.py # API usage examples
│   ├── event_selection_example.py # Event selection demo
│   └── signals_example.py       # Signal & scoring demo
│
├── tests/                        # Test suite
│   ├── test_setup.py            # Setup validation
│   ├── test_data_providers.py   # API tests
│   ├── test_events.py           # Event selection tests
│   ├── test_signals.py          # Signal computation tests (Stage 6)
│   └── test_scoring.py          # Scoring tests (Stage 7)
│
├── jobs/                         # Scheduled jobs
│   ├── post_close.py            # Post-close pipeline (Stage 8) ⭐
│   ├── pre_market.py            # Pre-market ΔOI job (Stage 9) ⭐
│   └── daily_pipeline.py        # Legacy pipeline
│
├── db/                           # Database schemas
│   ├── 000_init.sql             # SQL schema
│   └── README.md                # Database docs
│
├── config/                       # Configuration
│   └── config.py                # Config management
│
├── out/                          # Output directory
│
├── Method.md                     # Methodology documentation
├── STAGE6_COMPLETE.md           # Stage 6 documentation
├── STAGE7_COMPLETE.md           # Stage 7 documentation
├── STAGE8_COMPLETE.md           # Stage 8 documentation ⭐
├── DEV_STAGE_6_7_SUMMARY.md    # Stages 6-7 summary
├── DEV_STAGE_8_SUMMARY.md      # Stage 8 summary ⭐
├── verify_stage8.py             # Stage 8 verification script
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Package configuration
└── README.md                    # This file
```

## 🧪 Testing

Run the complete test suite:

```bash
# All tests
pytest tests/ -v

# Specific test modules
pytest tests/test_signals.py -v     # Signal computation tests
pytest tests/test_scoring.py -v     # Scoring tests
pytest tests/test_events.py -v      # Event selection tests

# Coverage report
pytest tests/ --cov=lib --cov-report=html

# Verify Stage 8 setup
python verify_stage8.py             # Tests post-close job components
```

**Test Results:**
- ✅ 32 tests in `test_signals.py` and `test_scoring.py`
- ✅ All tests passing
- ✅ 100% coverage for signal and scoring functions
- ✅ Stage 8 verification script validates full pipeline

## 📖 Documentation

### Core Documentation
- **[Method.md](Method.md)** - Theoretical foundation and methodology
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Implementation summary

### API Documentation
- **[lib/DATA_PROVIDERS.md](lib/DATA_PROVIDERS.md)** - Data provider APIs
- **[lib/EVENTS_DOCUMENTATION.md](lib/EVENTS_DOCUMENTATION.md)** - Event selection system
- **[db/README.md](db/README.md)** - Database schema and setup

### Examples
- **[examples/signals_example.py](examples/signals_example.py)** - Signal computation demos
- **[examples/event_selection_example.py](examples/event_selection_example.py)** - Event selection demos
- **[examples/data_provider_example.py](examples/data_provider_example.py)** - Data fetching demos

## 🔧 Development Status

### ✅ Completed Stages

- **Stage 1-3**: Project setup, configuration, API clients
- **Stage 4**: Data providers (Polygon, Finnhub)
- **Stage 5**: Event and expiry selection system
- **Stage 6**: Signal computation (8 core signals)
- **Stage 7**: Normalization and scoring system
- **Stage 8**: Post-close job with database persistence ⭐
- **Stage 9**: Pre-market ΔOI (Delta Open Interest) capture ⭐ **NEW**

### 🎉 Production Ready

The system is now complete and ready for production use:
- ✅ End-to-end automated pipeline (post-close + pre-market)
- ✅ Database-backed persistence
- ✅ Point-in-time snapshots with overnight OI tracking
- ✅ ΔOI (Delta Open Interest) capture for institutional positioning
- ✅ Enhanced directional scores with flow signals
- ✅ Daily predictions export
- ✅ Schedulable with cron (twice daily)
- ✅ Comprehensive error handling

### 📋 Future Enhancements

- Machine learning weight optimization
- Real-time signal updates during trading day
- Greeks-based position sizing
- Multi-leg structure recommendations (spreads, straddles)
- Risk management layer (portfolio heat, correlation)
- Web dashboard for signal monitoring
- Automated order generation
- Performance tracking (P&L attribution)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary. All rights reserved.

## 🙏 Acknowledgments

- Polygon.io for options market data
- Finnhub for earnings calendar data
- Supabase for database infrastructure

## 📞 Contact

For questions or support, please open an issue on GitHub.

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-15  
**Status**: Production Ready ✅

