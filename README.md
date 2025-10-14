# Option Research: Earnings Options Strategy

A systematic framework for generating directional options trade ideas around earnings events. The pipeline analyzes options skew, flow, and sentiment to rank CALL vs PUT setups by conviction level.

## What It Does

- Fetches upcoming earnings calendar (Finnhub API)
- Pulls options chains for event expiries (Polygon API)
- Computes directional signals: skew (risk reversal), net flow, put/call ratios, momentum
- Scores each ticker with a conviction-weighted recommendation (CALL or PUT)
- Outputs ranked watchlist with suggested structures (naked, spreads) and probability estimates

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/option-research.git
cd option-research

# Install dependencies
pip install -e .
```

## API Keys Setup

You'll need API keys from two providers:

**1. Polygon.io (Options Data)**
- Visit [polygon.io](https://polygon.io/) and sign up
- Copy your API key
- Add to `.env` file: `POLYGON_API_KEY=your_key_here`

**2. Finnhub (Earnings Calendar)**
- Visit [finnhub.io/register](https://finnhub.io/register) and sign up
- Copy your API key  
- Add to `.env` file: `FINNHUB_API_KEY=your_key_here`

Create a `.env` file in the project root:
```bash
POLYGON_API_KEY=your_polygon_key
FINNHUB_API_KEY=your_finnhub_key
```

## Quick Start

### 1. Test with Sample Data

Run the pipeline on included sample data:

```bash
python -m option_research data/sample_inputs.csv --trade-date 2024-03-28 --output watchlist.csv
```

This generates a ranked CSV with columns:
- `ticker`, `direction` (CALL/PUT), `conviction`, `DirScore`
- `structure` (e.g., "strong call naked", "medium put spread")
- `p_up`, `p_down` (probability estimates)
- Individual signals: `D1`-`D5`, penalties: `P1`, `P2`

Example output:
```
ticker,direction,DirScore,conviction,structure,p_up,p_down
AAPL,CALL,1.23,1.23,strong call naked,0.77,0.23
TSLA,CALL,0.68,0.68,medium call naked,0.64,0.36
MSFT,PUT,-0.31,0.31,weak put spread,0.44,0.56
```

### 2. Fetch Live Data

Use the included API clients:

**Fetch earnings calendar:**
```bash
python examples/fetch_earnings.py --days 7
```

**Fetch options chain:**
```bash
python examples/fetch_options.py --ticker AAPL --expiry 2024-04-19
```

**Complete pipeline (earnings + options):**
```bash
python examples/full_pipeline_example.py --days 7 --output features.csv
```

### 3. Use in Python

```python
from option_research import PolygonClient, FinnhubClient

# Fetch upcoming earnings
finnhub = FinnhubClient()
earnings = finnhub.get_upcoming_earnings(days_ahead=7)

# Get options data
polygon = PolygonClient()
expiry = PolygonClient.get_earnings_expiry("2024-04-17")  # Returns first Friday after
chain = polygon.get_option_chain(ticker="AAPL", expiry=expiry)

# Compute pipeline features
features = polygon.compute_chain_features(
    ticker="AAPL",
    expiry=expiry,
    spot_price=170.0,
)
```

## How It Works

The pipeline computes a **DirScore** for each ticker using:

- **D1: Skew/Risk Reversal** (25Δ call IV - put IV) — primary direction signal
- **D2: Net Flow Imbalance** (change in call OI vs put OI) — persistent positioning
- **D3: Put/Call Ratio** (PCR) — fast sentiment indicator
- **D4: Price Momentum** (beta-adjusted returns) — trend confirmation
- **D5: Historical Consistency** (how reliable skew has been for this name)

**Penalties:**
- **P1: IV Cost** (how expensive the event IV is)
- **P2: Spread Penalty** (bid-ask width)

**Trade Rules:**
- DirScore ≥ +0.7 → **CALL** setup
- DirScore ≤ -0.7 → **PUT** setup
- |DirScore| < 0.4 → **Skip** (insufficient edge)

## Project Structure

```
option-research/
├── option_research/          # Main package
│   ├── pipeline.py          # Scoring logic
│   ├── polygon_client.py    # Options data API
│   └── finnhub_client.py    # Earnings calendar API
├── examples/                 # Usage examples
├── tests/                    # Tests for API clients
└── data/                     # Sample data
```
