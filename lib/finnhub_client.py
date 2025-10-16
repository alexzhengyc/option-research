"""
Finnhub API client for earnings dates and company data
"""
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

import finnhub
import pandas as pd
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

from .supa import SUPA, upsert_rows

# Load environment variables
load_dotenv()

PACIFIC_TZ = ZoneInfo("America/Los_Angeles")


def _localize_series_to_pacific(series: pd.Series) -> pd.Series:
    """Ensure a datetime Series is expressed in Pacific time."""

    if series.dt.tz is None:
        return series.dt.tz_localize(PACIFIC_TZ)
    return series.dt.tz_convert(PACIFIC_TZ)


def _calendar_time_to_pacific(base_dt: datetime, hour_field: Optional[str]) -> datetime:
    """Map Finnhub hour codes into Pacific timestamps."""

    if not hour_field:
        return base_dt.replace(hour=16, minute=0)

    label = hour_field.lower()
    if label == "bmo":
        return base_dt.replace(hour=6, minute=0)
    if label == "amc":
        return base_dt.replace(hour=16, minute=0)

    try:
        parts = label.split(":")
        if len(parts) >= 2:
            return base_dt.replace(
                hour=int(parts[0]),
                minute=int(parts[1]),
            )
    except ValueError:
        pass

    return base_dt.replace(hour=16, minute=0)


def _calendar_to_frame(records: List[Dict]) -> pd.DataFrame:
    """Convert Finnhub earnings calendar records into a normalized DataFrame."""

    if not records:
        return pd.DataFrame(columns=["symbol", "earnings_ts", "earnings_date", "session"])

    rows = []
    for event in records:
        symbol = event.get("symbol")
        date_str = event.get("date")
        if not symbol or not date_str:
            continue

        try:
            base_dt = datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            continue

        hour_field = event.get("hour")
        session = (hour_field or "amc").lower()
        if session not in {"bmo", "amc"}:
            session = "custom"

        earnings_ts = _calendar_time_to_pacific(base_dt, hour_field).replace(tzinfo=PACIFIC_TZ)
        rows.append(
            {
                "symbol": symbol,
                "earnings_ts": earnings_ts,
                "earnings_date": earnings_ts.date(),
                "session": session,
            }
        )

    return pd.DataFrame(rows, columns=["symbol", "earnings_ts", "earnings_date", "session"])


def _normalize_db_events(data: List[Dict]) -> pd.DataFrame:
    """Normalize Supabase earnings responses into a standard DataFrame."""

    if not data:
        return pd.DataFrame(columns=["symbol", "earnings_ts", "earnings_date"])

    df = pd.DataFrame(data)
    df["earnings_ts"] = pd.to_datetime(df["earnings_ts"], errors="coerce")
    df = df.dropna(subset=["earnings_ts"])
    if df.empty:
        return df

    df["earnings_ts"] = _localize_series_to_pacific(df["earnings_ts"])
    df["earnings_date"] = df["earnings_ts"].dt.date
    return df[["symbol", "earnings_ts", "earnings_date"]]


def _events_to_symbol_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Return symbol, timestamp, and date for unique earnings events."""

    if df.empty:
        return pd.DataFrame(columns=["symbol", "earnings_ts", "earnings_date"])

    frame = df.copy()

    if "earnings_ts" in frame.columns:
        frame["earnings_ts"] = pd.to_datetime(frame["earnings_ts"], errors="coerce")
        frame = frame.dropna(subset=["earnings_ts"])
        if frame.empty:
            return pd.DataFrame(columns=["symbol", "earnings_ts", "earnings_date"])
        if frame["earnings_ts"].dt.tz is None:
            frame["earnings_ts"] = frame["earnings_ts"].dt.tz_localize(PACIFIC_TZ)
        else:
            frame["earnings_ts"] = frame["earnings_ts"].dt.tz_convert(PACIFIC_TZ)
    else:
        frame["earnings_ts"] = pd.to_datetime(frame["earnings_date"], errors="coerce")
        frame = frame.dropna(subset=["earnings_ts"])
        if frame.empty:
            return pd.DataFrame(columns=["symbol", "earnings_ts", "earnings_date"])
        frame["earnings_ts"] = frame["earnings_ts"].dt.tz_localize(PACIFIC_TZ)

    frame["earnings_date"] = frame["earnings_ts"].dt.date

    return (
        frame.sort_values("earnings_ts")[["symbol", "earnings_ts", "earnings_date"]]
        .drop_duplicates(subset=["symbol"])
        .reset_index(drop=True)
    )


def _pacific_datetime(day: date, hour: int, minute: int = 0) -> datetime:
    """Helper to construct Pacific-aware datetimes."""

    return datetime.combine(day, datetime.min.time()).replace(
        hour=hour,
        minute=minute,
        tzinfo=PACIFIC_TZ,
    )


def load_earnings_events_from_db(start_ts: datetime, end_ts: datetime) -> pd.DataFrame:
    """Retrieve earnings events between two timestamps from Supabase."""

    response = (
        SUPA.schema("public")
        .table("earnings_events")
        .select("symbol,earnings_ts")
        .gte("earnings_ts", start_ts.isoformat())
        .lt("earnings_ts", end_ts.isoformat())
        .execute()
    )
    data = response.data or []
    return _normalize_db_events(data)


def fetch_and_store_earnings(target_date: date) -> pd.DataFrame:
    """Fetch earnings for a date from Finnhub and upsert them into Supabase."""

    client = FinnhubClient()
    records = client.get_earnings_calendar(start_date=target_date, end_date=target_date)
    frame = _calendar_to_frame(records)
    if frame.empty:
        return frame

    rows_to_save = [
        {
            "symbol": row.symbol,
            "earnings_ts": row.earnings_ts.replace(tzinfo=None).isoformat(),
        }
        for row in frame.itertuples(index=False)
    ]

    upsert_rows(
        table="public.earnings_events",
        rows=rows_to_save,
        on_conflict="symbol,earnings_ts",
    )
    return frame


def get_earnings_events(trade_date: date) -> pd.DataFrame:
    """
    Load earnings relevant for the intraday job (today AMC + tomorrow BMO).

    Returns:
        DataFrame with columns ``symbol`` and ``earnings_date``.
    """

    tomorrow = trade_date + timedelta(days=1)

    # Today's after-close window: [1:00 PM PT, midnight)
    today_after_close = load_earnings_events_from_db(
        _pacific_datetime(trade_date, 13, 0),
        _pacific_datetime(tomorrow, 0, 0),
    )

    # Tomorrow's before-open window: [midnight, 6:30 AM PT)
    tomorrow_pre_open = load_earnings_events_from_db(
        _pacific_datetime(tomorrow, 0, 0),
        _pacific_datetime(tomorrow, 6, 30),
    )

    if today_after_close.empty:
        fallback_today = fetch_and_store_earnings(trade_date)
        if not fallback_today.empty:
            today_after_close = fallback_today[fallback_today["session"] == "amc"]

    if tomorrow_pre_open.empty:
        fallback_tomorrow = fetch_and_store_earnings(tomorrow)
        if not fallback_tomorrow.empty:
            tomorrow_pre_open = fallback_tomorrow[fallback_tomorrow["session"] == "bmo"]

    combined = pd.concat(
        [today_after_close, tomorrow_pre_open],
        ignore_index=True,
    )

    return _events_to_symbol_dates(combined)


class FinnhubClient:
    """Client for fetching earnings dates and company fundamentals from Finnhub"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Finnhub client
        
        Args:
            api_key: Finnhub API key (defaults to FINNHUB_API_KEY env var)
        """
        api_key = api_key or os.getenv("FINNHUB_API_KEY")
        if not api_key:
            raise ValueError("FINNHUB_API_KEY must be provided or set in environment")
        
        self.client = finnhub.Client(api_key=api_key)
    
    def get_earnings_calendar(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        symbol: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get earnings calendar
        
        Args:
            start_date: Start date for earnings (defaults to today)
            end_date: End date for earnings (defaults to 30 days from start)
            symbol: Filter by specific symbol
            
        Returns:
            List of earnings events
        """
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = start_date + timedelta(days=30)
        
        # Note: Using '_from' as the API parameter name
        from_date = start_date.isoformat()
        to_date = end_date.isoformat()
        
        # Finnhub API requires symbol parameter - use empty string for all earnings
        symbol_param = symbol if symbol else ""
        result = self.client.earnings_calendar(_from=from_date, to=to_date, symbol=symbol_param)
        return result.get("earningsCalendar", [])
    
    def get_company_profile(self, symbol: str) -> Dict:
        """
        Get company profile
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Company profile data
        """
        return self.client.company_profile2(symbol=symbol)
    
    def get_basic_financials(self, symbol: str) -> Dict:
        """
        Get basic financial metrics
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Financial metrics
        """
        return self.client.company_basic_financials(symbol, "all")


def get_upcoming_earnings(
    symbols: List[str], 
    start: date, 
    end: date
) -> List[Dict[str, any]]:
    """
    Get upcoming earnings dates for a list of symbols
    
    Args:
        symbols: List of stock ticker symbols
        start: Start date for earnings search
        end: End date for earnings search
    
    Returns:
        List of dicts with format:
        [
            {
                "symbol": "AAPL",
                "earnings_ts": datetime(2025, 10, 26, 16, 30)  # earnings datetime
            },
            ...
        ]
    """
    client = FinnhubClient()
    earnings_calendar = client.get_earnings_calendar(
        start_date=start,
        end_date=end,
    )

    frame = _calendar_to_frame(earnings_calendar)
    if frame.empty:
        return []

    symbol_set = set(symbols)
    filtered = frame[frame["symbol"].isin(symbol_set)]

    return [
        {
            "symbol": row.symbol,
            "earnings_ts": row.earnings_ts,
        }
        for row in filtered.itertuples(index=False)
    ]
