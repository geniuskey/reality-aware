#!/usr/bin/env python3
"""Draw results/uncertainty_before_after.webp: the uncertainty map at both ends of a budget."""

from __future__ import annotations

import argparse
from pathlib import Path

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

from nano import figures
from nano.cli import RESULTS_DIR, add_experiment_args, add_source_args, single_episode, source_warning


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wafer", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=RESULTS_DIR / "uncertainty_before_after.webp")
    add_source_args(parser)
    add_experiment_args(parser)
    args = parser.parse_args(argv)

    bundle = single_episode(args, wafer_index=args.wafer, seed=args.seed)
    warning = source_warning(bundle.dataset)
    if warning:
        print(warning)
    first, last = bundle.episode.steps[0], bundle.episode.steps[-1]
    path = figures.plot_uncertainty_before_after(bundle.record, bundle.episode, args.out)
    print(
        f"wrote {path} · mean uncertainty {first.uncertainty.mean():.3f} → "
        f"{last.uncertainty.mean():.3f} over {last.measurements - first.measurements} measurements"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
