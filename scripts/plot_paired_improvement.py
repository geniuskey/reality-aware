#!/usr/bin/env python3
"""Draw results/paired_improvement.svg from an existing benchmark summary.

Per-episode differences, not an average: a rule that helps most wafers a little
and hurts a few a lot looks identical to a good one in a mean.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

from nano import figures
from nano.cli import RESULTS_DIR
from nano.evaluate import DEFAULT_OUTPUT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--out", type=Path, default=RESULTS_DIR / "paired_improvement.svg")
    args = parser.parse_args(argv)

    if not args.summary.exists():
        raise SystemExit(
            f"{args.summary} does not exist. Run `python -m nano.benchmark` first — this script "
            f"plots a run, it does not invent one."
        )
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    path = figures.plot_paired_improvement(summary, args.out)
    print(f"wrote {path} from {args.summary} ({len(summary.get('episodes', []))} episodes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
