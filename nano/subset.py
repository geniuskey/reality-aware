"""``python -m nano.subset`` — derive the versioned evaluation index from WM-811K.

The dataset itself is never committed. This writes the small JSON index that
names which wafers the benchmark evaluates, so the evaluation set can be
reconstructed exactly from a local copy of the data.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from nano.data import DEFAULT_RAW_PATH, DEFAULT_SUBSET_PATH, build_subset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m nano.subset",
        description="Filter WM-811K and write the versioned subset index.",
    )
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW_PATH, help="local LSWMD.pkl")
    parser.add_argument("--out", type=Path, default=DEFAULT_SUBSET_PATH, help="index to write")
    parser.add_argument("--wafers", type=int, default=12, help="wafers in the evaluation set")
    parser.add_argument("--seed", type=int, default=0, help="selection seed, recorded in the index")
    parser.add_argument(
        "--min-dies", type=int, default=400, help="drop wafers with fewer dies than this"
    )
    parser.add_argument(
        "--patterns", nargs="*", default=None, help="restrict to these failure patterns"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    doc = build_subset(
        args.raw,
        args.out,
        seed=args.seed,
        n_wafers=args.wafers,
        min_dies=args.min_dies,
        patterns=args.patterns,
    )
    counts: dict[str, int] = {}
    for entry in doc["wafers"]:
        counts[entry["pattern"]] = counts.get(entry["pattern"], 0) + 1
    print(f"wrote {args.out} · {len(doc['wafers'])} wafers · patterns {counts}")
    print("commit this index; do not commit the dataset it was derived from")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
