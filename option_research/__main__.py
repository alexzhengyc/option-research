"""Command line interface for the Direction-First model."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .pipeline import ScoreConfig, compute_directional_scores


DEFAULTS = ScoreConfig()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="CSV file with historical feature data")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional CSV file to save the ranked table. Prints to stdout otherwise.",
    )
    parser.add_argument(
        "--trade-date",
        type=str,
        default=None,
        help="Target trade date (YYYY-MM-DD). Defaults to the most recent as_of in the input.",
    )
    parser.add_argument(
        "--min-liquidity",
        type=float,
        default=DEFAULTS.min_liquidity,
        help="Minimum total notional volume required for inclusion (default: %(default)s)",
    )
    parser.add_argument(
        "--max-spread-penalty",
        type=float,
        default=DEFAULTS.max_spread_penalty,
        help="Maximum spread penalty allowed (default: %(default)s)",
    )
    parser.add_argument(
        "--strong-threshold",
        type=float,
        default=DEFAULTS.score_thresholds[0],
        help="Strong conviction threshold (default: %(default)s)",
    )
    parser.add_argument(
        "--medium-threshold",
        type=float,
        default=DEFAULTS.score_thresholds[1],
        help="Medium conviction threshold (default: %(default)s)",
    )
    return parser.parse_args()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        headers: list[str] = []
    else:
        headers = list(rows[0].keys())
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: value if not hasattr(value, "isoformat") else value.isoformat() for key, value in row.items()})


def main() -> None:
    args = parse_args()

    rows = _read_csv(args.input)
    config = ScoreConfig(
        min_liquidity=args.min_liquidity,
        max_spread_penalty=args.max_spread_penalty,
        score_thresholds=(args.strong_threshold, args.medium_threshold),
    )

    ranked = compute_directional_scores(rows, config=config, trade_date=args.trade_date)

    if args.output:
        _write_csv(args.output, ranked)
    else:
        _write_csv(Path("/dev/stdout"), ranked)


if __name__ == "__main__":
    main()
