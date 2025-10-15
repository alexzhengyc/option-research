# Jobs

This directory contains scheduled jobs and pipeline scripts.

## Scripts

### ⭐ `post_close.py` - Production Pipeline (Stage 8)

**Recommended** - Complete post-close job with database persistence:

1. Fetches upcoming earnings for universe (14 days ahead)
2. Snapshots options chains to database (`eds.option_contracts`, `eds.option_snapshots`)
3. Computes 8 core signals per event
4. Normalizes and scores across all events
5. Stores results to `eds.daily_signals`
6. Exports predictions to `out/predictions_YYYYMMDD.csv`

**Features:**
- ✅ Point-in-time snapshots (single `asof_ts`)
- ✅ Database persistence for backtesting
- ✅ Idempotent (safe to re-run)
- ✅ Comprehensive error handling
- ✅ Production-ready

### ⭐ `pre_market.py` - Pre-Market Job (Stage 9)

**New** - Captures open interest deltas after OI posts (~8-9 AM ET):

1. Fetches yesterday's earnings events from `eds.daily_signals`
2. Re-snapshots same option contracts (now with fresh OI data)
3. Computes ΔOI (Delta Open Interest) for calls/puts within ATM ±2 strikes
4. Inserts ΔOI data into `eds.oi_deltas` table
5. Optionally recomputes DirScore with ΔOI folded into flow signals

**Features:**
- ✅ Captures overnight open interest changes
- ✅ Focuses on ATM ±2 strikes for relevance
- ✅ Optional score updates with enhanced flow signals
- ✅ Complements post-close analysis
- ✅ Production-ready

**Why Pre-Market?**
- Open Interest data updates overnight (after settlement)
- Available by 8-9 AM ET next trading day
- Captures institutional positioning changes
- ΔOI is a strong directional signal

### `daily_pipeline.py` - Legacy Pipeline

Original daily pipeline (deprecated in favor of `post_close.py`):
- Fetches upcoming earnings from Finnhub
- Computes directional scores for each ticker
- Generates ranked watchlist
- Saves to `out/watchlist_YYYYMMDD.csv`

**Note:** This script has placeholder signal computation and should be replaced by `post_close.py` for production use.

## Usage

### Production (Recommended)

```bash
# Run post-close job (after market close, ~4:30 PM ET)
python jobs/post_close.py

# Run for specific date
python jobs/post_close.py --date 2025-10-15

# Run pre-market job (after OI posts, ~8-9 AM ET next day)
python jobs/pre_market.py

# Run pre-market job with score updates
python jobs/pre_market.py --update-scores

# Run pre-market job for specific date (processes that date's events)
python jobs/pre_market.py --date 2025-10-15
```

### Legacy

```bash
# Run legacy pipeline
python jobs/daily_pipeline.py
```

## Scheduling

### Production (Cron)

Schedule both jobs to run daily:

```cron
# /etc/crontab or crontab -e

# Post-close job: Run at 4:30 PM ET (30 min after market close)
30 16 * * 1-5 cd /path/to/option-research && /path/to/venv/bin/python jobs/post_close.py >> /var/log/option-research-post-close.log 2>&1

# Pre-market job: Run at 8:30 AM ET (after OI posts)
30 8 * * 1-5 cd /path/to/option-research && /path/to/venv/bin/python jobs/pre_market.py --update-scores >> /var/log/option-research-pre-market.log 2>&1
```

**Timing Rationale:**
- **Post-Close (4:30 PM ET):** Market closes at 4:00 PM; 30 min buffer for settlement and greeks calculation
- **Pre-Market (8:30 AM ET):** Open Interest data posts overnight; available by 8-9 AM ET

### Alternative Scheduling

**Systemd Timer** (Linux):

Create `/etc/systemd/system/option-research-post-close.service`:
```ini
[Unit]
Description=Option Research Post-Close Job
After=network.target

[Service]
Type=oneshot
User=your_user
WorkingDirectory=/path/to/option-research
Environment="PATH=/path/to/venv/bin:/usr/bin"
ExecStart=/path/to/venv/bin/python jobs/post_close.py
StandardOutput=append:/var/log/option-research-post-close.log
StandardError=append:/var/log/option-research-post-close.log
```

Create `/etc/systemd/system/option-research-post-close.timer`:
```ini
[Unit]
Description=Option Research Post-Close Timer
Requires=option-research-post-close.service

[Timer]
OnCalendar=Mon-Fri 16:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

Create `/etc/systemd/system/option-research-pre-market.service`:
```ini
[Unit]
Description=Option Research Pre-Market Job
After=network.target

[Service]
Type=oneshot
User=your_user
WorkingDirectory=/path/to/option-research
Environment="PATH=/path/to/venv/bin:/usr/bin"
ExecStart=/path/to/venv/bin/python jobs/pre_market.py --update-scores
StandardOutput=append:/var/log/option-research-pre-market.log
StandardError=append:/var/log/option-research-pre-market.log
```

Create `/etc/systemd/system/option-research-pre-market.timer`:
```ini
[Unit]
Description=Option Research Pre-Market Timer
Requires=option-research-pre-market.service

[Timer]
OnCalendar=Mon-Fri 08:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl enable option-research-post-close.timer
sudo systemctl start option-research-post-close.timer
sudo systemctl enable option-research-pre-market.timer
sudo systemctl start option-research-pre-market.timer
```

**Airflow DAG** (if using Airflow):

```python
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'trading',
    'depends_on_past': False,
    'start_date': datetime(2025, 10, 15),
    'email_on_failure': True,
    'email': ['alerts@example.com'],
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Post-close DAG
post_close_dag = DAG(
    'option_research_post_close',
    default_args=default_args,
    description='Daily post-close option signal generation',
    schedule_interval='30 16 * * 1-5',  # 4:30 PM ET weekdays
    catchup=False,
)

post_close_task = BashOperator(
    task_id='run_post_close',
    bash_command='cd /path/to/option-research && /path/to/venv/bin/python jobs/post_close.py',
    dag=post_close_dag,
)

# Pre-market DAG
pre_market_dag = DAG(
    'option_research_pre_market',
    default_args=default_args,
    description='Pre-market ΔOI capture and score updates',
    schedule_interval='30 8 * * 1-5',  # 8:30 AM ET weekdays
    catchup=False,
)

pre_market_task = BashOperator(
    task_id='run_pre_market',
    bash_command='cd /path/to/option-research && /path/to/venv/bin/python jobs/pre_market.py --update-scores',
    dag=pre_market_dag,
)
```

## Monitoring

### Success Metrics

**Post-Close Job:**
```python
from lib.supa import SUPA
from datetime import date

result = SUPA.schema("eds").table("daily_signals") \
    .select("*", count="exact") \
    .eq("trade_date", date.today().isoformat()) \
    .execute()

print(f"Signals generated: {result.count}")
```

**Pre-Market Job:**
```python
from lib.supa import SUPA
from datetime import date, timedelta

yesterday = date.today() - timedelta(days=1)

result = SUPA.schema("eds").table("oi_deltas") \
    .select("*", count="exact") \
    .eq("trade_date", yesterday.isoformat()) \
    .execute()

print(f"ΔOI records generated: {result.count}")
```

### Alert Conditions

**Post-Close Job:**
- **No signals generated**: Possible API or data issue
- **Signal count < 5**: Insufficient earnings events
- **All decisions = PASS**: Normalization or scoring issue
- **Runtime > 30 min**: Performance degradation
- **Database write errors**: Connection or schema issue

**Pre-Market Job:**
- **No ΔOI records**: Yesterday had no earnings or API issue
- **All ΔOI = 0**: Open interest data not updating properly
- **Runtime > 15 min**: Performance degradation
- **Database write errors**: Connection or schema issue

### Example Alert Script

```python
#!/usr/bin/env python
"""
Send alert if jobs failed
"""
from lib.supa import SUPA
from datetime import date, timedelta
import smtplib
from email.message import EmailMessage

def check_post_close_health():
    """Check post-close job health"""
    today = date.today()
    
    result = SUPA.schema("eds").table("daily_signals") \
        .select("*", count="exact") \
        .eq("trade_date", today.isoformat()) \
        .execute()
    
    if result.count == 0:
        send_alert(f"Post-close job failed for {today}: No signals generated")
    elif result.count < 5:
        send_alert(f"Post-close job warning for {today}: Only {result.count} signals")
    else:
        print(f"✓ Post-close job healthy: {result.count} signals generated")

def check_pre_market_health():
    """Check pre-market job health"""
    yesterday = date.today() - timedelta(days=1)
    
    result = SUPA.schema("eds").table("oi_deltas") \
        .select("*", count="exact") \
        .eq("trade_date", yesterday.isoformat()) \
        .execute()
    
    if result.count == 0:
        send_alert(f"Pre-market job warning for {yesterday}: No ΔOI records generated")
    else:
        print(f"✓ Pre-market job healthy: {result.count} ΔOI records generated")

def send_alert(message):
    msg = EmailMessage()
    msg['Subject'] = 'Option Research Alert'
    msg['From'] = 'alerts@example.com'
    msg['To'] = 'team@example.com'
    msg.set_content(message)
    
    with smtplib.SMTP('smtp.example.com') as s:
        s.send_message(msg)
    
    print(f"✗ Alert sent: {message}")

if __name__ == '__main__':
    check_post_close_health()
    check_pre_market_health()
```

Run health checks after each job:
```bash
# In crontab
# Check post-close job 15 minutes after it runs
45 16 * * 1-5 cd /path/to/option-research && python scripts/check_health.py

# Check pre-market job 15 minutes after it runs
45 8 * * 1-5 cd /path/to/option-research && python scripts/check_health.py
```

## Troubleshooting

### Common Issues

**Issue**: No earnings events found
```bash
Solution: Check Finnhub API key and date range
Verify: curl "https://finnhub.io/api/v1/calendar/earnings?from=2025-10-15&to=2025-10-29&token=YOUR_KEY"
```

**Issue**: Database connection errors
```bash
Solution: Verify SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
Test: python -c "from lib.supa import SUPA; print(SUPA.table('eds.earnings_events').select('*').limit(1).execute())"
```

**Issue**: All signals are None
```bash
Solution: Check that contracts have greeks and IV data
Debug: Enable debug logging in post_close.py
```

## Output

### Database Tables

**`eds.earnings_events`**
```
symbol | earnings_ts
AAPL   | 2025-10-26 16:00:00-07
```

**`eds.option_contracts`**
```
option_symbol          | symbol | expiry     | strike | option_type
O:AAPL251031C00150000  | AAPL   | 2025-10-31 | 150.00 | C
```

**`eds.option_snapshots`**
```
asof_ts              | option_symbol         | underlying_px | bid  | ask  | iv    | volume
2025-10-15 16:30:00  | O:AAPL251031C00150000 | 148.50        | 5.20 | 5.40 | 0.321 | 1250
```

**`eds.daily_signals`**
```
trade_date | symbol | event_expiry | rr_25d  | dirscore | decision
2025-10-15 | AAPL   | 2025-10-31   | 0.0823  | 1.2543   | CALL
```

**`eds.oi_deltas`** (from pre-market job)
```
trade_date | symbol | event_expiry | d_oi_calls | d_oi_puts
2025-10-15 | AAPL   | 2025-10-31   | 1250       | -800
2025-10-15 | NVDA   | 2025-10-25   | 2100       | 500
```

### CSV Export

`out/predictions_20251015.csv`:
```csv
symbol,earnings_date,event_date,score,decision,rr_25d,vol_pcr,...
NVDA,2025-10-18,2025-10-25,1.2543,CALL,0.0823,-0.89,...
TSLA,2025-10-19,2025-10-25,-0.9832,PUT,-0.0654,1.45,...
```

## See Also

- **[STAGE8_COMPLETE.md](../STAGE8_COMPLETE.md)** - Detailed Stage 8 documentation
- **[DEV_STAGE_8_SUMMARY.md](../DEV_STAGE_8_SUMMARY.md)** - Stage 8 summary
- **[verify_stage8.py](../verify_stage8.py)** - Verification script

