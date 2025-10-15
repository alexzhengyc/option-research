"""Dev Stage 10 - Intraday nowcast job.

Runs during the 12:00-12:55 PM PT window to refresh directional scores
using only live, intraday inputs (no ΔOI). The job mirrors the playbook in
``Method.md`` by:

1. Pulling the current trade day's ``eds.daily_signals`` universe
2. Re-snapshotting the event expiry chains from Polygon
3. Recomputing the fast signals (RR, PCR, volume thrust, IV bump, spreads,
   beta-adjusted momentum)
4. Cross-sectionally normalising the signals and computing the intraday
   DirScore weights
5. Applying the guardrails/structure logic and storing the results in
   ``eds.intraday_signals`` along with an EWMA-smoothed score
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# Allow direct imports from lib/
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "lib"))
sys.path.insert(0, str(PROJECT_ROOT / "config"))

from lib.polygon_client import get_chain_snapshot, get_underlying_agg  # noqa: E402
from lib.signals import compute_all_signals  # noqa: E402
from lib.scoring import (  # noqa: E402
    normalize_today,
    compute_intraday_dirscore,
    resolve_intraday_decision,
)
from lib.supa import SUPA, insert_rows  # noqa: E402
import config  # noqa: E402  # pylint: disable=unused-import


@dataclass
class IntradaySnapshot:
    """Container for raw intraday signal inputs prior to scoring."""

    symbol: str
    event_date: Optional[date]
    trade_date: date
    asof_ts: datetime
    rr_25d: Optional[float]
    net_thrust: Optional[float]
    vol_pcr: Optional[float]
    beta_adj_return: Optional[float]
    iv_bump: Optional[float]
    spread_pct_atm: Optional[float]
    spot_price: Optional[float]
    call_volume: Optional[float]
    put_volume: Optional[float]
    total_volume: Optional[float]

    def to_dict(self) -> Dict[str, Optional[float]]:
        """Return a dictionary representation for DataFrame construction."""

        return {
            "symbol": self.symbol,
            "event_date": self.event_date,
            "trade_date": self.trade_date,
            "asof_ts": self.asof_ts,
            "rr_25d": self.rr_25d,
            "net_thrust": self.net_thrust,
            "vol_pcr": self.vol_pcr,
            "beta_adj_return": self.beta_adj_return,
            "iv_bump": self.iv_bump,
            "spread_pct_atm": self.spread_pct_atm,
            "spot_price": self.spot_price,
            "call_volume": self.call_volume,
            "put_volume": self.put_volume,
            "total_volume": self.total_volume,
        }


class IntradayJob:
    """Intraday job orchestrator."""

    def __init__(
        self,
        trade_date: Optional[date] = None,
        asof_ts: Optional[datetime] = None,
        ewma_alpha: float = 0.3,
    ) -> None:
        self.trade_date: date = trade_date or date.today()
        self.asof_ts: datetime = asof_ts or datetime.now()
        self.ewma_alpha: float = ewma_alpha

        print("=" * 70)
        print("INTRADAY NOWCAST JOB - Dev Stage 10")
        print("=" * 70)
        print(f"Trade date: {self.trade_date}")
        print(f"Snapshot : {self.asof_ts.isoformat()}")
        print(f"EWMA α   : {self.ewma_alpha:.2f}")

    def load_daily_universe(self) -> pd.DataFrame:
        """Load the symbols/event expiries from today's daily signals."""

        print("\n1. Loading today's daily signals for intraday refresh...")
        response = (
            SUPA.schema("eds")
            .table("daily_signals")
            .select("symbol,event_expiry")
            .eq("trade_date", self.trade_date.isoformat())
            .execute()
        )
        data = response.data or []

        if not data:
            print("   ✗ No daily signals available for trade date")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        if "event_expiry" in df.columns:
            df["event_expiry"] = pd.to_datetime(
                df["event_expiry"], errors="coerce"
            ).dt.date

        print(f"   ✓ Universe size: {len(df)} symbols")
        return df

    def _estimate_med20_volumes(self, symbol: str) -> Dict[str, float]:
        """Estimate 20-day baseline volumes using the Stage 8 heuristic."""

        try:
            end = self.trade_date
            start = end - timedelta(days=30)
            bars = get_underlying_agg(symbol, start, end, timespan="day")
            volumes = [bar.get("volume") for bar in bars if bar.get("volume")]
            if volumes:
                median_vol = float(np.median(volumes))
                call_med20 = median_vol * 0.05 * 0.6
                put_med20 = median_vol * 0.05 * 0.4
                return {
                    "call_med20": call_med20,
                    "put_med20": put_med20,
                }
        except Exception as exc:  # pragma: no cover - external API
            print(f"      Warning: med20 volume heuristic failed for {symbol}: {exc}")

        return {"call_med20": 10000.0, "put_med20": 8000.0}

    @staticmethod
    def _sum_option_volume(contracts: List[Dict], option_type: str) -> float:
        """Aggregate volume across contracts for a given option type."""

        total = 0.0
        for contract in contracts:
            details = contract.get("details", {})
            if details.get("contract_type") != option_type:
                continue
            day_data = contract.get("day", {})
            vol = day_data.get("volume")
            if vol is None:
                continue
            try:
                total += float(vol)
            except (TypeError, ValueError):
                continue
        return total

    @staticmethod
    def _extract_spot(contracts: List[Dict]) -> Optional[float]:
        """Return the first available underlying price from contracts."""

        for contract in contracts:
            price = contract.get("underlying_asset", {}).get("price")
            if price is not None:
                try:
                    return float(price)
                except (TypeError, ValueError):
                    continue
        return None

    def snapshot_event(self, symbol: str, event_expiry: Optional[date]) -> List[Dict]:
        """Snapshot the event expiry chain (if available)."""

        if not event_expiry:
            return []

        try:
            contracts = get_chain_snapshot(symbol, event_expiry, event_expiry)
            if contracts:
                print(f"   - {symbol}: {len(contracts)} contracts snapped")
            else:
                print(f"   - {symbol}: snapshot empty")
            return contracts
        except Exception as exc:  # pragma: no cover - network/api call
            print(f"   - {symbol}: snapshot failed ({exc})")
            return []

    def build_intraday_snapshot(
        self,
        symbol: str,
        event_expiry: Optional[date],
    ) -> Optional[IntradaySnapshot]:
        """Compute raw signals for a single symbol."""

        contracts = self.snapshot_event(symbol, event_expiry)
        if not contracts:
            return None

        med20 = self._estimate_med20_volumes(symbol)

        signals = compute_all_signals(
            symbol=symbol,
            event_date=event_expiry or self.trade_date,
            event_contracts=contracts,
            prev_contracts=None,
            next_contracts=None,
            med20_volumes=med20,
            lookback_days=3,
            sector_symbol="SPY",
        )

        if not signals:
            return None

        call_volume = self._sum_option_volume(contracts, "call")
        put_volume = self._sum_option_volume(contracts, "put")
        total_volume = call_volume + put_volume
        spot_price = self._extract_spot(contracts)

        return IntradaySnapshot(
            symbol=symbol,
            event_date=event_expiry,
            trade_date=self.trade_date,
            asof_ts=self.asof_ts,
            rr_25d=signals.get("rr_25d"),
            net_thrust=signals.get("net_thrust"),
            vol_pcr=signals.get("vol_pcr"),
            beta_adj_return=signals.get("beta_adj_return"),
            iv_bump=signals.get("iv_bump"),
            spread_pct_atm=signals.get("spread_pct_atm"),
            spot_price=spot_price,
            call_volume=call_volume or None,
            put_volume=put_volume or None,
            total_volume=total_volume or None,
        )

    def _fetch_previous_score(self, symbol: str) -> Dict[str, Optional[float]]:
        """Fetch the most recent intraday record for the symbol."""

        response = (
            SUPA.schema("eds")
            .table("intraday_signals")
            .select("dirscore_now,dirscore_ewma,asof_ts")
            .eq("trade_date", self.trade_date.isoformat())
            .eq("symbol", symbol)
            .order("asof_ts", desc=True)
            .limit(1)
            .execute()
        )

        data = response.data or []
        return data[0] if data else {}

    def _compute_ewma(self, current: float, previous: Optional[float]) -> float:
        """Apply EWMA smoothing with configured alpha."""

        if previous is None or pd.isna(previous):
            return current
        return self.ewma_alpha * current + (1 - self.ewma_alpha) * previous

    def score_snapshots(self, snapshots: List[IntradaySnapshot]) -> pd.DataFrame:
        """Normalize and score intraday snapshots."""

        if not snapshots:
            return pd.DataFrame()

        df = pd.DataFrame([snap.to_dict() for snap in snapshots])

        df_norm = normalize_today(
            df,
            signal_columns=[
                "rr_25d",
                "net_thrust",
                "vol_pcr",
                "beta_adj_return",
                "iv_bump",
                "spread_pct_atm",
            ],
            winsorize_std=2.0,
        )

        records: List[Dict] = []

        for _, row in df_norm.iterrows():
            score_now, direction = compute_intraday_dirscore(row)
            pct_iv = row.get("pct_iv_bump")
            spread_pct = row.get("spread_pct_atm")
            total_volume = row.get("total_volume")
            decision, structure = resolve_intraday_decision(
                score_now,
                pct_iv,
                spread_pct,
                total_volume,
            )

            prev = self._fetch_previous_score(row["symbol"])
            prev_ewma = prev.get("dirscore_ewma")
            prev_now = prev.get("dirscore_now")

            score_ewma = self._compute_ewma(score_now, prev_ewma)

            size_reduction = 1.0
            notes = None
            if prev_now is not None and not pd.isna(prev_now):
                if abs(score_now - float(prev_now)) > 0.4:
                    size_reduction = 0.5
                    notes = "WHIPSAW_REDUCE"

            if decision == "PASS":
                direction = "NONE"
                structure = "SKIP"

            records.append({
                "symbol": row["symbol"],
                "event_date": row.get("event_date"),
                "trade_date": row.get("trade_date"),
                "asof_ts": row.get("asof_ts"),
                "spot_price": row.get("spot_price"),
                "rr_25d": row.get("rr_25d"),
                "net_thrust": row.get("net_thrust"),
                "vol_pcr": row.get("vol_pcr"),
                "beta_adj_return": row.get("beta_adj_return"),
                "iv_bump": row.get("iv_bump"),
                "spread_pct_atm": row.get("spread_pct_atm"),
                "z_rr_25d": row.get("z_rr_25d"),
                "z_net_thrust": row.get("z_net_thrust"),
                "z_vol_pcr": row.get("z_vol_pcr"),
                "z_beta_adj_return": row.get("z_beta_adj_return"),
                "pct_iv_bump": row.get("pct_iv_bump"),
                "z_spread_pct_atm": row.get("z_spread_pct_atm"),
                "call_volume": row.get("call_volume"),
                "put_volume": row.get("put_volume"),
                "total_volume": row.get("total_volume"),
                "dirscore_now": score_now,
                "dirscore_ewma": score_ewma,
                "decision": decision,
                "structure": structure,
                "direction": direction,
                "size_reduction": size_reduction,
                "notes": notes,
            })

        return pd.DataFrame(records)

    def persist_scores(self, df: pd.DataFrame) -> None:
        """Write the intraday scores to ``eds.intraday_signals``."""

        if df.empty:
            print("\nNo intraday scores to persist.")
            return

        print(f"\n4. Persisting {len(df)} intraday snapshots...")
        payload: List[Dict] = []

        for _, row in df.iterrows():
            event_date = row.get("event_date")
            if pd.notna(event_date) and not isinstance(event_date, date):
                event_date = pd.to_datetime(event_date).date()

            asof_value = row.get("asof_ts")
            if isinstance(asof_value, datetime):
                asof_str = asof_value.isoformat()
            else:
                asof_str = str(asof_value)

            payload.append({
                "trade_date": self.trade_date.isoformat(),
                "symbol": row["symbol"],
                "event_expiry": event_date.isoformat() if event_date else None,
                "asof_ts": asof_str,
                "spot_price": float(row["spot_price"]) if pd.notna(row.get("spot_price")) else None,
                "rr_25d": float(row["rr_25d"]) if pd.notna(row.get("rr_25d")) else None,
                "net_thrust": float(row["net_thrust"]) if pd.notna(row.get("net_thrust")) else None,
                "vol_pcr": float(row["vol_pcr"]) if pd.notna(row.get("vol_pcr")) else None,
                "beta_adj_return": float(row["beta_adj_return"]) if pd.notna(row.get("beta_adj_return")) else None,
                "iv_bump": float(row["iv_bump"]) if pd.notna(row.get("iv_bump")) else None,
                "spread_pct_atm": float(row["spread_pct_atm"]) if pd.notna(row.get("spread_pct_atm")) else None,
                "z_rr_25d": float(row["z_rr_25d"]) if pd.notna(row.get("z_rr_25d")) else None,
                "z_net_thrust": float(row["z_net_thrust"]) if pd.notna(row.get("z_net_thrust")) else None,
                "z_vol_pcr": float(row["z_vol_pcr"]) if pd.notna(row.get("z_vol_pcr")) else None,
                "z_beta_adj_return": float(row["z_beta_adj_return"]) if pd.notna(row.get("z_beta_adj_return")) else None,
                "pct_iv_bump": float(row["pct_iv_bump"]) if pd.notna(row.get("pct_iv_bump")) else None,
                "z_spread_pct_atm": float(row["z_spread_pct_atm"]) if pd.notna(row.get("z_spread_pct_atm")) else None,
                "dirscore_now": float(row["dirscore_now"]),
                "dirscore_ewma": float(row["dirscore_ewma"]),
                "decision": row.get("decision"),
                "structure": row.get("structure"),
                "direction": row.get("direction"),
                "call_volume": float(row["call_volume"]) if pd.notna(row.get("call_volume")) else None,
                "put_volume": float(row["put_volume"]) if pd.notna(row.get("put_volume")) else None,
                "total_volume": float(row["total_volume"]) if pd.notna(row.get("total_volume")) else None,
                "size_reduction": float(row["size_reduction"]) if pd.notna(row.get("size_reduction")) else None,
                "notes": row.get("notes"),
                "ewma_alpha": float(self.ewma_alpha),
            })

        try:
            insert_rows("eds.intraday_signals", payload)
            print("   ✓ Intraday scores stored")
        except Exception as exc:  # pragma: no cover - network/API
            print(f"   ✗ Error writing intraday scores: {exc}")
            raise

    def run(self) -> pd.DataFrame:
        """Execute the intraday job end-to-end."""

        universe = self.load_daily_universe()
        if universe.empty:
            return pd.DataFrame()

        print("\n2. Re-snapshotting event expiries...")
        snapshots: List[IntradaySnapshot] = []
        for _, row in universe.iterrows():
            symbol = row["symbol"]
            event_expiry = row.get("event_expiry")
            snapshot = self.build_intraday_snapshot(symbol, event_expiry)
            if snapshot is None:
                continue
            snapshots.append(snapshot)

        if not snapshots:
            print("   ✗ No intraday signals computed")
            return pd.DataFrame()

        print("\n3. Normalizing + scoring intraday signals...")
        df_scored = self.score_snapshots(snapshots)

        if df_scored.empty:
            print("   ✗ Scoring produced no rows")
            return df_scored

        self.persist_scores(df_scored)

        print("\nSummary of intraday recommendations:")
        decision_counts = df_scored["decision"].value_counts()
        for decision, count in decision_counts.items():
            print(f"   - {decision}: {count}")

        high_conviction = df_scored["dirscore_now"].abs() >= 0.7
        print(f"   - High conviction (|score|≥0.7): {int(high_conviction.sum())}")

        return df_scored


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(description="Run intraday nowcast job")
    parser.add_argument(
        "--trade-date",
        dest="trade_date",
        type=str,
        help="Trade date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--asof",
        dest="asof_ts",
        type=str,
        help="Explicit snapshot timestamp (ISO). Defaults to now.",
    )
    parser.add_argument(
        "--alpha",
        dest="alpha",
        type=float,
        default=0.3,
        help="EWMA alpha (default 0.3)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    trade_date = date.fromisoformat(args.trade_date) if args.trade_date else None
    asof_ts = datetime.fromisoformat(args.asof_ts) if args.asof_ts else None

    job = IntradayJob(
        trade_date=trade_date,
        asof_ts=asof_ts,
        ewma_alpha=args.alpha,
    )
    job.run()


if __name__ == "__main__":
    main(sys.argv[1:])
