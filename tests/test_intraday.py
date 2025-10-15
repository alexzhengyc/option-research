"""Unit tests for the intraday job universe construction."""

from __future__ import annotations

import os
import sys
import types
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List
from zoneinfo import ZoneInfo

import pandas as pd
import pytest


class _FakeSupabaseClient:  # pragma: no cover - helper
    """Simple Supabase stub returning predefined rows."""

    def __init__(self, rows: Iterable[dict]):
        self._rows = list(rows)

    def schema(self, _name: str) -> "_FakeSupabaseClient":
        return self

    def table(self, _name: str) -> "_FakeSupabaseQuery":
        return _FakeSupabaseQuery(self._rows)


class _FakeSupabaseQuery:  # pragma: no cover - helper
    """Query object that mimics the chained supabase API used in the job."""

    def __init__(self, rows: List[dict]):
        self._rows = rows
        self._filters = []

    def select(self, *_args, **_kwargs) -> "_FakeSupabaseQuery":
        return self

    def gte(self, field: str, value: str) -> "_FakeSupabaseQuery":
        self._filters.append(("gte", field, value))
        return self

    def lt(self, field: str, value: str) -> "_FakeSupabaseQuery":
        self._filters.append(("lt", field, value))
        return self

    def execute(self):
        def _to_datetime(val):
            if isinstance(val, datetime):
                return val
            return datetime.fromisoformat(val)

        records = []
        for row in self._rows:
            include = True
            for op, field, value in self._filters:
                cutoff = _to_datetime(value)
                ts = _to_datetime(row[field])
                if op == "gte" and ts < cutoff:
                    include = False
                    break
                if op == "lt" and ts >= cutoff:
                    include = False
                    break
            if include:
                records.append(dict(row))

        return types.SimpleNamespace(data=records)


fake_supabase_module = types.SimpleNamespace(create_client=lambda *_args, **_kwargs: _FakeSupabaseClient([]))
sys.modules.setdefault("supabase", fake_supabase_module)
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jobs.intraday import IntradayJob


@pytest.fixture
def job(monkeypatch):
    """Provide an ``IntradayJob`` with a configurable Supabase stub."""

    def _factory(rows: Iterable[dict]):
        client = _FakeSupabaseClient(rows)
        monkeypatch.setattr("jobs.intraday.SUPA", client)
        return IntradayJob(
            trade_date=date(2024, 5, 1),
            asof_ts=datetime(2024, 5, 1, 12, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
        )

    return _factory


def test_load_earnings_before_open_filters_after_open(job):
    """Only earnings scheduled before the bell should be included."""

    pacific = ZoneInfo("America/Los_Angeles")
    rows = [
        {"symbol": "EARLY", "earnings_ts": datetime(2024, 5, 2, 6, 0, tzinfo=pacific).isoformat()},
        {"symbol": "LATE", "earnings_ts": datetime(2024, 5, 2, 7, 15, tzinfo=pacific).isoformat()},
    ]
    intraday_job = job(rows)

    df = intraday_job.load_earnings_before_open(date(2024, 5, 2))

    assert list(df["symbol"]) == ["EARLY"]


def test_load_daily_universe_combines_after_close_and_pre_open(job, monkeypatch):
    """The job should merge today's after-close and tomorrow's pre-open earnings."""

    intraday_job = job([])

    pacific = ZoneInfo("America/Los_Angeles")

    today_data = pd.DataFrame(
        [
            {
                "symbol": "TOD1",
                "earnings_ts": pd.Timestamp("2024-05-01T13:15", tz=pacific),
                "earnings_date": date(2024, 5, 1),
            },
            {
                "symbol": "TOD2",
                "earnings_ts": pd.Timestamp("2024-05-01T14:00", tz=pacific),
                "earnings_date": date(2024, 5, 1),
            },
        ]
    )

    tomorrow_data = pd.DataFrame(
        [
            {
                "symbol": "TOM1",
                "earnings_ts": pd.Timestamp("2024-05-02T05:30", tz=pacific),
                "earnings_date": date(2024, 5, 2),
            },
            {
                "symbol": "TOM2",
                "earnings_ts": pd.Timestamp("2024-05-02T06:15", tz=pacific),
                "earnings_date": date(2024, 5, 2),
            },
        ]
    )

    monkeypatch.setattr(
        IntradayJob,
        "load_earnings_after_close_today",
        lambda self: today_data,
    )
    monkeypatch.setattr(
        IntradayJob,
        "load_earnings_before_open",
        lambda self, _date: tomorrow_data,
    )

    universe = intraday_job.load_daily_universe()

    assert set(universe["symbol"]) == {"TOD1", "TOD2", "TOM1", "TOM2"}


def test_load_daily_universe_filters_api_fallback(job, monkeypatch):
    """Fallback earnings fetched from the API should respect the time windows."""

    intraday_job = job([])

    empty_df = pd.DataFrame()
    monkeypatch.setattr(
        IntradayJob,
        "load_earnings_after_close_today",
        lambda self: empty_df,
    )
    monkeypatch.setattr(
        IntradayJob,
        "load_earnings_before_open",
        lambda self, _date: empty_df,
    )

    pacific = ZoneInfo("America/Los_Angeles")

    def _fake_fetch(self, target_date, _universe):
        if target_date == date(2024, 5, 1):
            return pd.DataFrame(
                [
                    {
                        "symbol": "TOD_OK",
                        "earnings_ts": pd.Timestamp("2024-05-01T13:10", tz=pacific),
                        "earnings_date": date(2024, 5, 1),
                    },
                    {
                        "symbol": "TOD_TOO_EARLY",
                        "earnings_ts": pd.Timestamp("2024-05-01T12:30", tz=pacific),
                        "earnings_date": date(2024, 5, 1),
                    },
                ]
            )
        if target_date == date(2024, 5, 2):
            return pd.DataFrame(
                [
                    {
                        "symbol": "TOM_OK",
                        "earnings_ts": pd.Timestamp("2024-05-02T05:55", tz=pacific),
                        "earnings_date": date(2024, 5, 2),
                    },
                    {
                        "symbol": "TOM_TOO_LATE",
                        "earnings_ts": pd.Timestamp("2024-05-02T07:00", tz=pacific),
                        "earnings_date": date(2024, 5, 2),
                    },
                ]
            )
        raise AssertionError("Unexpected date")

    monkeypatch.setattr(IntradayJob, "fetch_and_save_earnings", _fake_fetch)

    universe = intraday_job.load_daily_universe()

    assert set(universe["symbol"]) == {"TOD_OK", "TOM_OK"}
