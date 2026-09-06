#!/usr/bin/env python3
"""Draw results/wafer_comparison.webp: biased prior, NANO reconstruction, hidden truth.

The episode is re-run with the benchmark's settings so the figure shows a real
run rather than an illustration.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

from nano import figures
from nano.cli import RESULTS_DIR, add_experiment_args, add_source_args, single_episode, source_warning
from nano.evaluate import mae


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wafer", default="0", help="wafer id, or an index into the evaluation set")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=RESULTS_DIR / "wafer_comparison.webp")
    add_source_args(parser)
    add_experiment_args(parser)
    args = parser.parse_args(argv)

    bundle = single_episode(args, wafer_index=args.wafer, seed=args.seed)
    warning = source_warning(bundle.dataset)
    if warning:
        print(warning)
    path = figures.plot_wafer_comparison(bundle.record, bundle.prior, bundle.episode, args.out)
    print(
        f"wrote {path} · {bundle.record.wafer_id} · "
        f"prior MAE {mae(bundle.prior, bundle.record.reality):.4f} → "
        f"NANO MAE {mae(bundle.episode.prediction, bundle.record.reality):.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
