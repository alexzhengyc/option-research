"""
Dev Stage 9 - Pre-market job

Run after Polygon posts official open interest (typically pre-market the
morning after the post-close run).

Responsibilities:
1. Pull the prior trade day's `eds.daily_signals`
2. Re-snapshot the event expiry chains for each symbol
3. Compute ΔOI within ATM ±2 strikes and persist to `eds.oi_deltas`
4. Re-run scoring with the new ΔOI inputs and refresh `eds.daily_signals`
"""
import sys
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Allow direct imports from lib/
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "lib"))
sys.path.insert(0, str(project_root / "config"))

from lib.polygon_client import get_chain_snapshot  # noqa: E402
from lib.supa import SUPA, upsert_rows  # noqa: E402
from lib.scoring import normalize_today, compute_dirscore  # noqa: E402
import config  # noqa: E402  # pylint: disable=unused-import


@dataclass
class OIDeltaResult:
    """Container for ΔOI calculations."""

    symbol: str
    event_expiry: date
    delta_oi_calls: Optional[int]
    delta_oi_puts: Optional[int]
    detail: str = ""


class PreMarketJob:
    """Pre-market job for delta open interest and score refresh."""

    def __init__(
        self,
        run_date: Optional[date] = None,
        trade_date: Optional[date] = None,
        recompute_scores: bool = True,
    ) -> None:
        """
        Initialize the job.

        Args:
            run_date: Calendar date the job is executed (defaults to today).
            trade_date: Market date whose signals should be updated
                (defaults to run_date - 1 business day).
            recompute_scores: When True, recompute DirScore with ΔOI inputs.
        """
        self.run_date: date = run_date or date.today()
        default_trade_date = self.run_date - timedelta(days=1)
        self.trade_date: date = trade_date or default_trade_date
        self.recompute_scores: bool = recompute_scores
        self.asof_ts: datetime = datetime.now()

        print("=" * 70)
        print("PRE-MARKET JOB - Dev Stage 9")
        print("=" * 70)
        print(f"Run date:   {self.run_date}")
        print(f"Trade date: {self.trade_date}")
        print(f"Snapshot:   {self.asof_ts.isoformat()}")

    # ------------------------------------------------------------------ #
    # Data acquisition helpers
    # ------------------------------------------------------------------ #
    def load_daily_signals(self) -> pd.DataFrame:
        """
        Fetch the prior day's daily signals from Supabase.

        Returns:
            DataFrame with one row per symbol.
        """
        print("\n1. Loading prior daily signals...")
        response = (
            SUPA.schema("eds")
            .table("daily_signals")
            .select("*")
            .eq("trade_date", self.trade_date.isoformat())
            .execute()
        )
        data = response.data or []

        if not data:
            print("   ✗ No daily signals found for trade date")
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # Normalize column types (Supabase returns strings for dates/numerics)
        for col in [
            "rr_25d",
            "pcr_volume",
            "pcr_notional",
            "vol_thrust_calls",
            "vol_thrust_puts",
            "atm_iv_event",
            "atm_iv_prev",
            "atm_iv_next",
            "iv_bump",
            "spread_pct_atm",
            "mom_3d_betaadj",
            "dirscore",
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "event_expiry" in df.columns:
            df["event_expiry"] = pd.to_datetime(
                df["event_expiry"], errors="coerce"
            ).dt.date

        print(f"   ✓ Loaded {len(df)} signals")
        return df

    def snapshot_event_contracts(
        self,
        symbol: str,
        event_expiry: date,
    ) -> List[Dict]:
        """
        Snapshot Polygon contracts for the event expiry.

        Args:
            symbol: Underlying ticker.
            event_expiry: Event option expiry.
        """
        try:
            contracts = get_chain_snapshot(symbol, event_expiry, event_expiry)
            if contracts:
                print(f"      Snapshot fetched ({len(contracts)} contracts)")
            else:
                print("      Snapshot empty")
            return contracts
        except Exception as exc:  # pragma: no cover - network/api call
            print(f"      ✗ Snapshot failed: {exc}")
            return []

    # ------------------------------------------------------------------ #
    # ΔOI computation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_spot_price(contracts: List[Dict]) -> Optional[float]:
        """Return first available underlying price from snapshot."""
        for contract in contracts:
            price = contract.get("underlying_asset", {}).get("price")
            if price is not None:
                return price
        return None

    @staticmethod
    def _atm_window_strikes(
        contracts: List[Dict],
        spot_price: float,
    ) -> List[float]:
        """
        Determine strike universe around ATM (±2 strikes).

        Returns:
            Sorted list of strikes to include.
        """
        strikes = sorted(
            {
                float(contract.get("details", {}).get("strike_price"))
                for contract in contracts
                if contract.get("details", {}).get("strike_price") is not None
            }
        )

        if not strikes:
            return []

        closest_idx = min(
            range(len(strikes)),
            key=lambda idx: abs(strikes[idx] - spot_price),
        )

        start_idx = max(0, closest_idx - 2)
        end_idx = min(len(strikes) - 1, closest_idx + 2)

        return strikes[start_idx : end_idx + 1]

    def _analyze_contracts(
        self,
        contracts: List[Dict],
        target_strikes: List[float],
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Split snapshot contracts into call/put slices within strike window.

        Returns:
            (call_contracts, put_contracts)
        """
        if not target_strikes:
            return [], []

        strike_set = set(target_strikes)
        call_contracts: List[Dict] = []
        put_contracts: List[Dict] = []

        for contract in contracts:
            details = contract.get("details", {})
            strike = details.get("strike_price")
            contract_type = details.get("contract_type", "").lower()
            if strike is None or float(strike) not in strike_set:
                continue

            if contract_type == "call":
                call_contracts.append(contract)
            elif contract_type == "put":
                put_contracts.append(contract)

        return call_contracts, put_contracts

    def _current_oi_totals(self, contracts: List[Dict]) -> int:
        """Sum OI for selected contracts."""
        total = 0
        for contract in contracts:
            oi = contract.get("open_interest")
            if oi is None:
                oi = contract.get("day", {}).get("open_interest")
            if oi is None:
                continue
            total += int(oi)
        return total

    def _latest_snapshot_oi(
        self,
        option_symbols: List[str],
    ) -> Dict[str, int]:
        """
        Fetch most recent stored OI for each contract.

        Args:
            option_symbols: List of Polygon option tickers.
        """
        if not option_symbols:
            return {}

        response = (
            SUPA.schema("eds")
            .table("option_snapshots")
            .select("option_symbol,oi,asof_ts")
            .in_("option_symbol", option_symbols)
            .order("asof_ts", desc=True)
            .execute()
        )

        latest: Dict[str, int] = {}
        for row in response.data or []:
            option_symbol = row.get("option_symbol")
            if not option_symbol or option_symbol in latest:
                continue
            oi_value = row.get("oi")
            if oi_value is None:
                continue
            latest[option_symbol] = int(oi_value)

        return latest

    def _prepare_snapshot_rows(
        self,
        contracts: List[Dict],
    ) -> List[Dict]:
        """
        Format contracts as rows for eds.option_snapshots.

        Returns:
            List of dict rows ready for Supabase insert.
        """
        rows: List[Dict] = []
        for contract in contracts:
            option_symbol = contract.get("ticker")
            if not option_symbol:
                continue

            rows.append(
                {
                    "asof_ts": self.asof_ts.isoformat(),
                    "option_symbol": option_symbol,
                    "underlying_px": contract.get("underlying_asset", {}).get(
                        "price"
                    ),
                    "bid": contract.get("last_quote", {}).get("bid"),
                    "ask": contract.get("last_quote", {}).get("ask"),
                    "last": contract.get("last_trade", {}).get("price"),
                    "iv": contract.get("implied_volatility"),
                    "delta": contract.get("greeks", {}).get("delta"),
                    "gamma": contract.get("greeks", {}).get("gamma"),
                    "theta": contract.get("greeks", {}).get("theta"),
                    "vega": contract.get("greeks", {}).get("vega"),
                    "volume": contract.get("day", {}).get("volume"),
                    "oi": contract.get("open_interest"),
                }
            )
        return rows

    def compute_delta_for_symbol(
        self,
        symbol: str,
        event_expiry: date,
    ) -> OIDeltaResult:
        """
        Compute ΔOI for a single symbol/event pair.
        """
        print(f"\n   Processing {symbol} (event expiry {event_expiry})")

        if event_expiry is None:
            return OIDeltaResult(
                symbol=symbol,
                event_expiry=self.trade_date,
                delta_oi_calls=None,
                delta_oi_puts=None,
                detail="missing_event_expiry",
            )

        contracts = self.snapshot_event_contracts(symbol, event_expiry)
        if not contracts:
            return OIDeltaResult(
                symbol=symbol,
                event_expiry=event_expiry,
                delta_oi_calls=None,
                delta_oi_puts=None,
                detail="empty_snapshot",
            )

        spot_price = self._extract_spot_price(contracts)
        if spot_price is None:
            return OIDeltaResult(
                symbol=symbol,
                event_expiry=event_expiry,
                delta_oi_calls=None,
                delta_oi_puts=None,
                detail="missing_spot",
            )

        target_strikes = self._atm_window_strikes(contracts, spot_price)
        call_contracts, put_contracts = self._analyze_contracts(
            contracts,
            target_strikes,
        )

        if not call_contracts and not put_contracts:
            return OIDeltaResult(
                symbol=symbol,
                event_expiry=event_expiry,
                delta_oi_calls=None,
                delta_oi_puts=None,
                detail="no_contracts_in_window",
            )

        option_symbols = [
            contract.get("ticker")
            for contract in call_contracts + put_contracts
            if contract.get("ticker")
        ]
        previous_oi = self._latest_snapshot_oi(option_symbols)

        current_calls = self._current_oi_totals(call_contracts)
        current_puts = self._current_oi_totals(put_contracts)

        previous_calls = sum(
            previous_oi.get(contract.get("ticker"), 0) for contract in call_contracts
        )
        previous_puts = sum(
            previous_oi.get(contract.get("ticker"), 0) for contract in put_contracts
        )

        delta_calls = current_calls - previous_calls
        delta_puts = current_puts - previous_puts

        print(
            f"      ΔOI calls: {delta_calls:+}, puts: {delta_puts:+} "
            f"(current {current_calls}/{current_puts})"
        )

        # Store new snapshot rows for continuity
        snapshot_rows = self._prepare_snapshot_rows(call_contracts + put_contracts)
        if snapshot_rows:
            try:
                upsert_rows("eds.option_snapshots", snapshot_rows)
            except Exception as exc:  # pragma: no cover - supabase write
                print(f"      Warning: snapshot insert failed ({exc})")

        return OIDeltaResult(
            symbol=symbol,
            event_expiry=event_expiry,
            delta_oi_calls=int(delta_calls),
            delta_oi_puts=int(delta_puts),
        )

    # ------------------------------------------------------------------ #
    # DirScore refresh
    # ------------------------------------------------------------------ #
    def recompute_dirscores(
        self,
        signals_df: pd.DataFrame,
        delta_results: List[OIDeltaResult],
    ) -> pd.DataFrame:
        """
        Refresh DirScore using ΔOI-enhanced flow component.
        """
        if signals_df.empty or not delta_results:
            print("\n   Skipping DirScore recompute (insufficient data)")
            return signals_df

        delta_frame = pd.DataFrame(
            [
                {
                    "symbol": item.symbol,
                    "delta_oi_calls": item.delta_oi_calls,
                    "delta_oi_puts": item.delta_oi_puts,
                }
                for item in delta_results
                if item.delta_oi_calls is not None and item.delta_oi_puts is not None
            ]
        )

        if delta_frame.empty:
            print("\n   Skipping DirScore recompute (no valid ΔOI)")
            return signals_df

        df = signals_df.merge(delta_frame, on="symbol", how="left")
        df["delta_oi_calls"] = df["delta_oi_calls"].fillna(0).astype(int)
        df["delta_oi_puts"] = df["delta_oi_puts"].fillna(0).astype(int)
        df["delta_oi_net"] = df["delta_oi_calls"] - df["delta_oi_puts"]
        df["net_thrust"] = (
            df["vol_thrust_calls"].fillna(0.0) - df["vol_thrust_puts"].fillna(0.0)
        )
        if "pcr_volume" in df.columns:
            df["vol_pcr"] = pd.to_numeric(df["pcr_volume"], errors="coerce")
        if "mom_3d_betaadj" in df.columns:
            df["beta_adj_return"] = pd.to_numeric(
                df["mom_3d_betaadj"], errors="coerce"
            )

        signal_columns = [
            "rr_25d",
            "vol_pcr",
            "net_thrust",
            "beta_adj_return",
            "iv_bump",
            "spread_pct_atm",
            "delta_oi_net",
        ]

        df_norm = normalize_today(df, signal_columns=signal_columns)
        score_and_decision = df_norm.apply(
            lambda row: pd.Series(compute_dirscore(row)), axis=1
        )
        df_norm["dirscore"] = score_and_decision[0]
        df_norm["decision"] = score_and_decision[1]

        # Persist the refreshed scores
        rows = []
        for _, row in df_norm.iterrows():
            rows.append(
                {
                    "trade_date": self.trade_date.isoformat(),
                    "symbol": row["symbol"],
                    "event_expiry": (
                        row["event_expiry"].isoformat()
                        if isinstance(row["event_expiry"], (date, datetime))
                        else row["event_expiry"]
                    ),
                    "rr_25d": row.get("rr_25d"),
                    "pcr_volume": row.get("pcr_volume"),
                    "pcr_notional": row.get("pcr_notional"),
                    "vol_thrust_calls": row.get("vol_thrust_calls"),
                    "vol_thrust_puts": row.get("vol_thrust_puts"),
                    "atm_iv_event": row.get("atm_iv_event"),
                    "atm_iv_prev": row.get("atm_iv_prev"),
                    "atm_iv_next": row.get("atm_iv_next"),
                    "iv_bump": row.get("iv_bump"),
                    "spread_pct_atm": row.get("spread_pct_atm"),
                    "mom_3d_betaadj": row.get("mom_3d_betaadj"),
                    "dirscore": float(row.get("dirscore"))
                    if not pd.isna(row.get("dirscore"))
                    else None,
                    "decision": row.get("decision"),
                }
            )

        try:
            upsert_rows("eds.daily_signals", rows, on_conflict="trade_date,symbol")
            print(f"\n   ✓ Updated DirScore for {len(rows)} rows")
        except Exception as exc:  # pragma: no cover - supabase write
            print(f"\n   ✗ Failed to update daily_signals: {exc}")

        return df_norm

    # ------------------------------------------------------------------ #
    # Main orchestration
    # ------------------------------------------------------------------ #
    def run(self) -> List[OIDeltaResult]:
        """Execute the pre-market workflow."""
        signals_df = self.load_daily_signals()
        if signals_df.empty:
            return []

        delta_results: List[OIDeltaResult] = []

        print("\n2. Computing ΔOI by symbol...")
        for _, row in signals_df.iterrows():
            result = self.compute_delta_for_symbol(
                symbol=row["symbol"],
                event_expiry=row.get("event_expiry"),
            )
            delta_results.append(result)

        successful = [
            item for item in delta_results if item.delta_oi_calls is not None
        ]
        if successful:
            rows = [
                {
                    "trade_date": self.trade_date.isoformat(),
                    "symbol": item.symbol,
                    "event_expiry": item.event_expiry.isoformat()
                    if isinstance(item.event_expiry, date)
                    else item.event_expiry,
                    "d_oi_calls": item.delta_oi_calls,
                    "d_oi_puts": item.delta_oi_puts,
                }
                for item in successful
            ]
            try:
                upsert_rows("eds.oi_deltas", rows, on_conflict="trade_date,symbol")
                print(f"\n3. ✓ Wrote {len(rows)} ΔOI rows to eds.oi_deltas")
            except Exception as exc:  # pragma: no cover - supabase write
                print(f"\n3. ✗ Failed to write ΔOI rows: {exc}")
        else:
            print("\n3. No ΔOI rows to persist")

        if self.recompute_scores:
            print("\n4. Refreshing DirScore with ΔOI...")
            self.recompute_dirscores(signals_df, delta_results)

        print("\n" + "=" * 70)
        print("PRE-MARKET JOB COMPLETE")
        print("=" * 70)

        return delta_results


def main() -> None:
    """Command line entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Pre-market ΔOI refresh job")
    parser.add_argument(
        "--run-date",
        type=str,
        help="Calendar date the job is executed (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--trade-date",
        type=str,
        help="Market trade date to update (YYYY-MM-DD). Defaults to run_date - 1.",
    )
    parser.add_argument(
        "--skip-recompute",
        action="store_true",
        help="Skip DirScore recompute step.",
    )

    args = parser.parse_args()

    run_date = (
        datetime.strptime(args.run_date, "%Y-%m-%d").date()
        if args.run_date
        else None
    )
    trade_date = (
        datetime.strptime(args.trade_date, "%Y-%m-%d").date()
        if args.trade_date
        else None
    )

    job = PreMarketJob(
        run_date=run_date,
        trade_date=trade_date,
        recompute_scores=not args.skip_recompute,
    )
    job.run()


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
