import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from option_research.pipeline import ScoreConfig, compute_directional_scores


DATA_PATH = Path("data/sample_inputs.csv")


def load_rows():
    with DATA_PATH.open() as fh:
        return list(csv.DictReader(fh))


def test_compute_directional_scores_orders_by_dirscore():
    rows = load_rows()
    config = ScoreConfig(min_liquidity=0, max_spread_penalty=10)

    result = compute_directional_scores(rows, config=config, trade_date="2024-03-28")

    assert result
    dirscores = [row["DirScore"] for row in result]
    assert dirscores == sorted(dirscores, reverse=True)

    for row in result:
        assert abs(row["p_up"] + row["p_down"] - 1.0) < 1e-9
        assert row["direction"].lower() in row["structure"]
