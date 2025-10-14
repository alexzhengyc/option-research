"""Core pipeline for computing the Direction-First score.

The implementation follows the blueprint in :mod:`README.md`.  The pipeline takes a
collection of historical observations and produces a ranked table for a target
trade date with direction, conviction and structure recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import exp
from statistics import mean, pstdev, quantiles
from typing import Iterable, Mapping, MutableMapping, Sequence


@dataclass(slots=True)
class ScoreConfig:
    """Configuration for scoring and filtering."""

    min_liquidity: float = 1e6
    max_spread_penalty: float = 2.0
    score_thresholds: tuple[float, float] = (0.7, 0.4)


def _zscore(values: Sequence[float]) -> list[float]:
    m = mean(values)
    s = pstdev(values)
    if s == 0:
        return [0.0 for _ in values]
    return [(v - m) / s for v in values]


def _compute_spread_penalty(values: Sequence[float]) -> list[float]:
    sorted_vals = sorted(max(v, 0.0) for v in values)
    if not sorted_vals:
        return []

    if len(sorted_vals) < 4:
        low = sorted_vals[0]
        high = sorted_vals[-1] if sorted_vals[-1] != low else low + 1.0
    else:
        q = quantiles(sorted_vals, n=4, method="inclusive")
        low = q[0]
        high = q[2]
        if high == low:
            high = low + 1.0

    penalties: list[float] = []
    for value in values:
        clipped = max(value, 0.0)
        if clipped <= low:
            penalties.append(0.0)
        elif clipped >= high:
            penalties.append(2.0)
        else:
            penalties.append(2.0 * (clipped - low) / (high - low))
    return penalties


def _ensure_columns(records: Sequence[Mapping[str, object]], required: set[str]) -> None:
    for key in required:
        if any(key not in row for row in records):
            raise ValueError(f"Missing required column: {key}")


def _to_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    raise TypeError(f"Cannot convert {value!r} to float")


def _parse_date(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Cannot convert {value!r} to datetime")


def compute_directional_scores(
    rows: Iterable[Mapping[str, object]],
    config: ScoreConfig | None = None,
    trade_date: datetime | str | None = None,
) -> list[dict[str, object]]:
    """Compute the Direction-First score for each ticker."""

    records = list(rows)
    if not records:
        return []

    required_columns = {
        "ticker",
        "as_of",
        "risk_reversal",
        "delta_oi_calls",
        "delta_oi_puts",
        "delta_vol_calls",
        "delta_vol_puts",
        "put_volume_notional",
        "call_volume_notional",
        "beta_adj_return",
        "rr_return_corr",
        "iv_bump_percentile",
        "spread_pct",
        "total_notional_volume",
    }
    _ensure_columns(records, required_columns)

    parsed: list[MutableMapping[str, object]] = []
    for row in records:
        parsed_row: MutableMapping[str, object] = dict(row)
        parsed_row["ticker"] = str(row["ticker"]).upper()
        parsed_row["as_of"] = _parse_date(row["as_of"])
        parsed_row["risk_reversal"] = _to_float(row["risk_reversal"])
        parsed_row["delta_oi_calls"] = _to_float(row["delta_oi_calls"])
        parsed_row["delta_oi_puts"] = _to_float(row["delta_oi_puts"])
        parsed_row["delta_vol_calls"] = _to_float(row["delta_vol_calls"])
        parsed_row["delta_vol_puts"] = _to_float(row["delta_vol_puts"])
        parsed_row["put_volume_notional"] = _to_float(row["put_volume_notional"])
        parsed_row["call_volume_notional"] = max(_to_float(row["call_volume_notional"]), 1e-9)
        parsed_row["beta_adj_return"] = _to_float(row["beta_adj_return"])
        parsed_row["rr_return_corr"] = _to_float(row["rr_return_corr"])
        parsed_row["iv_bump_percentile"] = max(0.0, min(1.0, _to_float(row["iv_bump_percentile"])))
        parsed_row["spread_pct"] = max(0.0, _to_float(row["spread_pct"]))
        parsed_row["total_notional_volume"] = _to_float(row["total_notional_volume"])
        parsed.append(parsed_row)

    if config is None:
        config = ScoreConfig()

    if trade_date is None:
        target_date = max(row["as_of"] for row in parsed)
    else:
        target_date = _parse_date(trade_date)
        if target_date not in {row["as_of"] for row in parsed}:
            raise ValueError(f"trade_date {target_date.date()} not present in data")

    by_ticker: dict[str, list[MutableMapping[str, object]]] = {}
    for row in parsed:
        by_ticker.setdefault(row["ticker"], []).append(row)

    spread_penalties = _compute_spread_penalty([row["spread_pct"] for row in parsed])
    for row, penalty in zip(parsed, spread_penalties):
        row["P2"] = penalty

    for items in by_ticker.values():
        rr_values = [row["risk_reversal"] for row in items]
        d1 = _zscore(rr_values)

        delta_oi_net = [row["delta_oi_calls"] - row["delta_oi_puts"] for row in items]
        delta_vol_net = [row["delta_vol_calls"] - row["delta_vol_puts"] for row in items]
        d2_oi = _zscore(delta_oi_net)
        d2_vol = _zscore(delta_vol_net)
        d2 = [oi + 0.5 * vol for oi, vol in zip(d2_oi, d2_vol)]

        pcr_values = [row["put_volume_notional"] / row["call_volume_notional"] for row in items]
        d3 = [-v for v in _zscore(pcr_values)]

        momentum_values = [row["beta_adj_return"] for row in items]
        d4 = _zscore(momentum_values)

        for idx, row in enumerate(items):
            row["D1"] = d1[idx]
            row["D2"] = d2[idx]
            row["D3"] = d3[idx]
            row["D4"] = d4[idx]
            row["D5"] = max(-2.0, min(2.0, row["rr_return_corr"]))
            row["P1"] = row["iv_bump_percentile"]

    scored_rows: list[dict[str, object]] = []
    for row in parsed:
        dir_score = (
            0.32 * row["D1"]
            + 0.28 * row["D2"]
            + 0.18 * row["D3"]
            + 0.12 * row["D4"]
            + 0.10 * row["D5"]
            - 0.10 * row["P1"]
            - 0.05 * row["P2"]
        )
        direction = "CALL" if dir_score >= 0 else "PUT"
        conviction = abs(dir_score)
        p_up = 1.0 / (1.0 + exp(-0.8 * dir_score))
        p_down = 1.0 - p_up

        strong, medium = config.score_thresholds
        if row["P1"] <= 0.60:
            base = "naked"
        elif row["P1"] <= 0.85:
            base = "debit spread"
        else:
            base = "tight spread / skip"

        if conviction >= strong:
            qualifier = "strong"
        elif conviction >= medium:
            qualifier = "medium"
        else:
            qualifier = "weak"

        scored_rows.append(
            {
                "ticker": row["ticker"],
                "as_of": row["as_of"],
                "DirScore": dir_score,
                "direction": direction,
                "conviction": conviction,
                "p_up": p_up,
                "p_down": p_down,
                "structure": f"{qualifier} {direction.lower()} {base}",
                "D1": row["D1"],
                "D2": row["D2"],
                "D3": row["D3"],
                "D4": row["D4"],
                "D5": row["D5"],
                "P1": row["P1"],
                "P2": row["P2"],
                "total_notional_volume": row["total_notional_volume"],
            }
        )

    filtered = [
        row
        for row in scored_rows
        if row["as_of"] == target_date
        and row["total_notional_volume"] >= config.min_liquidity
        and row["P2"] <= config.max_spread_penalty
    ]

    filtered.sort(key=lambda row: row["DirScore"], reverse=True)
    return filtered


__all__ = ["compute_directional_scores", "ScoreConfig"]
