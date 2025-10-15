"""Tests for the pre-market job logic.

These tests focus on the methodology described in ``Method.md``
for incorporating ΔOI information into the directional score.
"""
from datetime import date
from pathlib import Path
import sys
import os
import types

import pandas as pd
import pytest


class _FakeSupabase:  # pragma: no cover - test helper
    """Minimal stub matching the Supabase client interface used in tests."""

    def schema(self, _):
        return self

    def table(self, _):
        return self

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def upsert(self, *_args, **_kwargs):
        return self

    def insert(self, *_args, **_kwargs):
        return self

    def execute(self):
        return types.SimpleNamespace(data=[], count=0)


fake_supabase_module = types.SimpleNamespace(create_client=lambda *_args, **_kwargs: _FakeSupabase())
sys.modules.setdefault("supabase", fake_supabase_module)
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-key")

# Ensure the project root is importable so we can reach ``jobs.pre_market``
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jobs.pre_market import OIDeltaResult, PreMarketJob


class DummyUpserter:
    """Utility to capture Supabase upserts during tests."""

    def __init__(self) -> None:
        self.calls = []

    def __call__(self, table: str, rows, on_conflict=None):  # pragma: no cover - helper
        self.calls.append({
            "table": table,
            "rows": rows,
            "on_conflict": on_conflict,
        })


@pytest.fixture
def job(monkeypatch):
    """Provide a ``PreMarketJob`` instance with Supabase writes stubbed."""
    stub = DummyUpserter()
    monkeypatch.setattr("jobs.pre_market.upsert_rows", stub)
    inst = PreMarketJob(recompute_scores=True)
    return inst, stub


def test_atm_window_strikes_focuses_on_atm(job):
    job_instance, _ = job
    contracts = [
        {"details": {"strike_price": strike, "contract_type": "call"}}
        for strike in [90, 95, 98, 99, 100, 101, 102, 103, 105]
    ]
    # Include some puts to ensure they do not affect strike discovery
    contracts += [
        {"details": {"strike_price": strike, "contract_type": "put"}}
        for strike in [96, 97, 104, 106]
    ]

    strikes = job_instance._atm_window_strikes(contracts, spot_price=100)

    # Expect the five strikes centred around the ATM level
    assert strikes == [98.0, 99.0, 100.0, 101.0, 102.0]


def test_recompute_dirscores_incorporates_delta_oi(job):
    job_instance, stub = job

    raw_signals = pd.DataFrame(
        [
            {
                "symbol": "AAA",
                "event_expiry": date(2024, 7, 19),
                "rr_25d": 1.5,
                "vol_thrust_calls": 3.0,
                "vol_thrust_puts": 0.5,
                "iv_bump": 10.0,
                "spread_pct_atm": 0.10,
                "mom_3d_betaadj": 0.05,
                "pcr_volume": 0.80,
                "pcr_notional": 0.90,
            },
            {
                "symbol": "BBB",
                "event_expiry": date(2024, 7, 19),
                "rr_25d": -1.5,
                "vol_thrust_calls": 0.5,
                "vol_thrust_puts": 3.0,
                "iv_bump": 40.0,
                "spread_pct_atm": 0.30,
                "mom_3d_betaadj": -0.04,
                "pcr_volume": 1.30,
                "pcr_notional": 1.40,
            },
        ]
    )

    delta_results = [
        OIDeltaResult("AAA", date(2024, 7, 19), delta_oi_calls=500, delta_oi_puts=100),
        OIDeltaResult("BBB", date(2024, 7, 19), delta_oi_calls=50, delta_oi_puts=600),
    ]

    result = job_instance.recompute_dirscores(raw_signals, delta_results)

    assert {"AAA", "BBB"} == set(result["symbol"])

    for _, row in result.iterrows():
        z_rr = row["z_rr_25d"]
        z_delta = row["z_delta_oi_net"]
        z_net = row["z_net_thrust"]
        z_pcr = row["z_vol_pcr"]
        z_mom = row["z_beta_adj_return"]
        p1 = row["pct_iv_bump"]
        z_spread = row["z_spread_pct_atm"]

        expected_d2 = z_delta + 0.5 * z_net
        expected_score = (
            0.32 * z_rr
            + 0.28 * expected_d2
            + 0.18 * (-z_pcr)
            + 0.12 * z_mom
            - 0.10 * p1
            - 0.05 * z_spread
        )

        assert pytest.approx(expected_score, rel=1e-6) == row["dirscore"]

        if row["symbol"] == "AAA":
            assert row["decision"] == "CALL"
        else:
            assert row["decision"] == "PUT"

    # The recompute should persist refreshed scores back to Supabase
    assert stub.calls, "Expected recomputed scores to be upserted"
    last_call = stub.calls[-1]
    assert last_call["table"] == "eds.daily_signals"
    assert last_call["on_conflict"] == "trade_date,symbol"
    stored_symbols = {entry["symbol"] for entry in last_call["rows"]}
    assert stored_symbols == {"AAA", "BBB"}
