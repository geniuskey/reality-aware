"""Wafer records: WM-811K loading, subset indexing and a synthetic stand-in.

A :class:`WaferRecord` is the unit of work everywhere else in the package. It
carries the hidden reality field, the in-wafer die mask (known geometry, the
agent is allowed to see it) and a failure-pattern label used only for
stratification and reporting.

WM-811K itself is never committed to this repository. ``build_subset`` derives a
small JSON index from a local copy so an evaluation set can be reconstructed
exactly without redistributing the source data.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

# WM-811K wafer maps encode: 0 = no die at this grid position, 1 = pass, 2 = fail.
OUTSIDE, PASS, FAIL = 0, 1, 2

DEFAULT_RAW_PATH = Path("data/raw/LSWMD.pkl")
DEFAULT_SUBSET_PATH = Path("data/subsets/wm811k_eval.json")
SUBSET_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class WaferRecord:
    """One wafer, flattened to the dies that actually exist.

    ``reality`` is hidden from the agent: only :mod:`nano.tools.observe` and
    :mod:`nano.evaluate` are allowed to read it.
    """

    wafer_id: str
    pattern: str
    grid_shape: tuple[int, int]
    die_mask: np.ndarray  # (H, W) bool — known geometry
    reality: np.ndarray  # (N,) float in {0.0, 1.0}, ordered by coords
    coords: np.ndarray  # (N, 2) int, (row, col) of every in-wafer die
    source: str = "WM-811K"
    target_kind: str = "binary"
    """What the reality field holds: "binary" pass/fail, or "continuous" readings.

    It selects which metrics apply — the class-balanced ones are meaningless on a
    continuous target — and it is recorded in the results file.
    """

    @property
    def n_dies(self) -> int:
        return int(self.coords.shape[0])

    def to_grid(self, values: np.ndarray, fill: float = np.nan) -> np.ndarray:
        """Scatter a flat ``(N,)`` field back onto the ``(H, W)`` die grid."""
        grid = np.full(self.grid_shape, fill, dtype=float)
        grid[self.coords[:, 0], self.coords[:, 1]] = values
        return grid

    def radius(self) -> np.ndarray:
        """Normalised radial distance of each die from the wafer centre, in [0, 1]."""
        h, w = self.grid_shape
        centre = np.array([(h - 1) / 2.0, (w - 1) / 2.0])
        delta = self.coords - centre
        scale = np.array([max(h - 1, 1) / 2.0, max(w - 1, 1) / 2.0])
        r = np.linalg.norm(delta / scale, axis=1)
        return np.clip(r, 0.0, 1.0)


def record_from_map(
    wafer_map: np.ndarray, wafer_id: str, pattern: str, source: str = "WM-811K"
) -> WaferRecord:
    """Build a record from a raw WM-811K style integer wafer map.

    Preprocessing rule 3 and 4 from ``docs/data.md``: geometry comes from
    ``value != 0``, and ``{1 -> 0.0, 2 -> 1.0}`` gives the reality field. The map
    is never resized or interpolated.
    """
    arr = np.asarray(wafer_map)
    if arr.ndim != 2:
        raise ValueError(f"wafer map must be 2-D, got shape {arr.shape}")
    die_mask = arr != OUTSIDE
    coords = np.argwhere(die_mask)
    reality = (arr[die_mask] == FAIL).astype(float)
    return WaferRecord(
        wafer_id=wafer_id,
        pattern=pattern,
        grid_shape=(int(arr.shape[0]), int(arr.shape[1])),
        die_mask=die_mask,
        reality=reality,
        coords=coords.astype(int),
        source=source,
        target_kind="binary",
    )


# --------------------------------------------------------------------------- #
# WM-811K
# --------------------------------------------------------------------------- #


def _normalise_label(value: object) -> str:
    """WM-811K stores labels as nested numpy object arrays more often than as strings."""
    while isinstance(value, (list, tuple, np.ndarray)):
        if len(value) == 0:
            return ""
        value = value[0]
    if value is None:
        return ""
    return str(value).strip()


def load_wm811k(raw_path: os.PathLike[str] | str = DEFAULT_RAW_PATH):
    """Yield ``(index, wafer_map, pattern)`` triples from a local ``LSWMD.pkl``.

    The file is a pandas pickle, so pandas is imported lazily: the benchmark can
    run on a synthetic source without it installed.
    """
    path = Path(raw_path)
    if not path.exists():
        raise FileNotFoundError(
            f"WM-811K not found at {path}. Download LSWMD.pkl (see docs/data.md) or "
            f"run with --synthetic."
        )
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ImportError(
            "Reading LSWMD.pkl needs pandas. Install it with: pip install -e '.[data]'"
        ) from exc

    frame = pd.read_pickle(path)
    for i, row in enumerate(frame.itertuples(index=False)):
        wafer_map = getattr(row, "waferMap", None)
        if wafer_map is None:
            continue
        yield i, np.asarray(wafer_map), _normalise_label(getattr(row, "failureType", ""))


def build_subset(
    raw_path: os.PathLike[str] | str = DEFAULT_RAW_PATH,
    out_path: os.PathLike[str] | str = DEFAULT_SUBSET_PATH,
    *,
    seed: int = 0,
    n_wafers: int = 12,
    min_dies: int = 400,
    patterns: Sequence[str] | None = None,
) -> dict:
    """Filter WM-811K and write a versioned subset index.

    Preprocessing rules 1 and 2: drop wafers whose die grid is too small for a
    sparse budget to mean anything, and keep only wafers carrying a labelled
    failure pattern so results can be broken down by pattern type. Wafers are
    then sampled stratified across the surviving pattern classes.
    """
    candidates: dict[str, list[dict]] = {}
    for index, wafer_map, pattern in load_wm811k(raw_path):
        if not pattern or pattern.lower() in {"none", "nan", ""}:
            continue
        if patterns is not None and pattern not in patterns:
            continue
        n_dies = int(np.count_nonzero(np.asarray(wafer_map) != OUTSIDE))
        if n_dies < min_dies:
            continue
        candidates.setdefault(pattern, []).append(
            {
                "wafer_id": f"wm811k-{index}",
                "index": index,
                "pattern": pattern,
                "grid_shape": [int(wafer_map.shape[0]), int(wafer_map.shape[1])],
                "n_dies": n_dies,
            }
        )

    if not candidates:
        raise RuntimeError(
            f"No wafer in {raw_path} passed the filters "
            f"(min_dies={min_dies}, patterns={patterns})."
        )

    rng = np.random.default_rng(seed)
    chosen = _stratified_sample(candidates, n_wafers, rng)

    index_doc = {
        "schema_version": SUBSET_SCHEMA_VERSION,
        "dataset": "WM-811K",
        "source_file": str(raw_path),
        "selection": {
            "seed": seed,
            "n_wafers": len(chosen),
            "min_dies": min_dies,
            "patterns": sorted(candidates),
            "stratified": True,
        },
        "wafers": chosen,
    }
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index_doc, indent=2) + "\n", encoding="utf-8")
    return index_doc


def _stratified_sample(
    candidates: dict[str, list[dict]], n_wafers: int, rng: np.random.Generator
) -> list[dict]:
    """Round-robin across pattern classes so no class dominates the evaluation set."""
    pools = {
        pattern: [items[i] for i in rng.permutation(len(items))]
        for pattern, items in sorted(candidates.items())
    }
    chosen: list[dict] = []
    while len(chosen) < n_wafers and any(pools.values()):
        for pattern in sorted(pools):
            if not pools[pattern]:
                continue
            chosen.append(pools[pattern].pop())
            if len(chosen) == n_wafers:
                break
    chosen.sort(key=lambda item: item["index"])
    return chosen


def load_subset(
    subset_path: os.PathLike[str] | str = DEFAULT_SUBSET_PATH,
    raw_path: os.PathLike[str] | str = DEFAULT_RAW_PATH,
) -> list[WaferRecord]:
    """Rebuild the evaluation wafers named by a subset index from a local WM-811K."""
    index_file = Path(subset_path)
    if not index_file.exists():
        raise FileNotFoundError(
            f"No subset index at {index_file}. Build one from a local WM-811K with "
            f"`python -m nano.subset`, or run with --synthetic."
        )
    doc = json.loads(index_file.read_text(encoding="utf-8"))
    wanted = {int(entry["index"]): entry for entry in doc["wafers"]}
    records: list[WaferRecord] = []
    for index, wafer_map, pattern in load_wm811k(raw_path):
        entry = wanted.pop(index, None)
        if entry is None:
            continue
        records.append(
            record_from_map(wafer_map, wafer_id=entry["wafer_id"], pattern=entry["pattern"] or pattern)
        )
        if not wanted:
            break
    if wanted:
        missing = sorted(wanted)[:5]
        raise RuntimeError(
            f"{len(wanted)} wafer(s) from {subset_path} are not in {raw_path} "
            f"(first missing indices: {missing}). The index and the dataset disagree."
        )
    records.sort(key=lambda r: r.wafer_id)
    return records


# --------------------------------------------------------------------------- #
# Synthetic source
# --------------------------------------------------------------------------- #

SYNTHETIC_PATTERNS = ("Center", "Donut", "Edge-Ring", "Edge-Loc", "Loc", "Scratch")
CONTINUOUS_PATTERNS = ("Radial", "Tilt", "Saddle", "Ring", "Spot", "Stripe")


def synthetic_wafers(
    n_wafers: int = 12,
    *,
    seed: int = 0,
    grid: int = 40,
    patterns: Sequence[str] | None = None,
    target: str = "binary",
) -> list[WaferRecord]:
    """Generate wafer maps with WM-811K-like failure patterns.

    This exists so the loop, the policies and the harness can be exercised — in
    tests, and by anyone who has not downloaded WM-811K. It is **not** WM-811K:
    records produced here carry ``source="synthetic"`` and every artifact derived
    from them says so, because a number measured on a stand-in must never be
    presented as a number measured on the dataset.

    ``target="continuous"`` generates smooth, noisy fields in place of pass/fail
    maps — the shape real metrology produces (CD, thickness, overlay) rather than
    a binary label. WM-811K cannot answer whether the same selection rule ranks
    locations well on continuous data; this is the only source here that can even
    ask the question.
    """
    if target not in ("binary", "continuous"):
        raise ValueError(f"unknown target {target!r}; expected 'binary' or 'continuous'")
    patterns = patterns or (SYNTHETIC_PATTERNS if target == "binary" else CONTINUOUS_PATTERNS)

    rng = np.random.default_rng(seed)
    records: list[WaferRecord] = []
    for i in range(n_wafers):
        pattern = patterns[i % len(patterns)]
        size = int(grid + rng.integers(-4, 5))
        if target == "binary":
            records.append(
                record_from_map(
                    _synthetic_map(size, pattern, rng),
                    wafer_id=f"synthetic-{i:03d}",
                    pattern=pattern,
                    source="synthetic",
                )
            )
        else:
            records.append(
                _continuous_record(size, pattern, rng, wafer_id=f"synthetic-cont-{i:03d}")
            )
    return records


def _continuous_record(
    size: int, pattern: str, rng: np.random.Generator, *, wafer_id: str
) -> WaferRecord:
    """A smooth, noisy metrology-like field on the same circular die grid.

    Values are scaled into ``[0, 1]`` so the prior generator, the estimator and
    the metrics need no special case — what changes is that the truth is now a
    continuous surface plus measurement noise rather than a label.
    """
    yy, xx = np.mgrid[0:size, 0:size]
    centre = (size - 1) / 2.0
    ry = (yy - centre) / centre
    rx = (xx - centre) / centre
    radius = np.sqrt(ry**2 + rx**2)
    inside = radius <= 1.0

    if pattern == "Radial":
        field = 1.0 - 0.8 * radius**2
    elif pattern == "Tilt":
        angle = rng.uniform(-np.pi, np.pi)
        field = 0.5 + 0.45 * (rx * np.cos(angle) + ry * np.sin(angle))
    elif pattern == "Saddle":
        field = 0.5 + 0.4 * (rx**2 - ry**2)
    elif pattern == "Ring":
        field = 0.3 + 0.6 * np.exp(-((radius - 0.6) ** 2) / (2 * 0.15**2))
    elif pattern == "Spot":
        cy, cx = rng.uniform(-0.5, 0.5, size=2)
        field = 0.3 + 0.6 * np.exp(-((ry - cy) ** 2 + (rx - cx) ** 2) / (2 * 0.2**2))
    else:  # Stripe
        angle = rng.uniform(0, np.pi)
        field = 0.5 + 0.35 * np.sin(4.0 * (rx * np.cos(angle) + ry * np.sin(angle)))

    # Tool noise: real readings are not smooth, and an estimator that assumes
    # they are would look better here than it deserves.
    field = field + rng.normal(0.0, 0.04, field.shape)
    field = np.clip(field, 0.0, 1.0)

    coords = np.argwhere(inside)
    return WaferRecord(
        wafer_id=wafer_id,
        pattern=pattern,
        grid_shape=(size, size),
        die_mask=inside,
        reality=field[inside],
        coords=coords.astype(int),
        source="synthetic",
        target_kind="continuous",
    )


def _synthetic_map(size: int, pattern: str, rng: np.random.Generator) -> np.ndarray:
    """One integer wafer map: 0 outside the disc, 1 pass, 2 fail."""
    yy, xx = np.mgrid[0:size, 0:size]
    centre = (size - 1) / 2.0
    ry = (yy - centre) / centre
    rx = (xx - centre) / centre
    radius = np.sqrt(ry**2 + rx**2)
    theta = np.arctan2(ry, rx)
    inside = radius <= 1.0

    fail_rate = np.full((size, size), 0.03)
    if pattern == "Center":
        fail_rate += 0.75 * np.exp(-(radius**2) / (2 * 0.18**2))
    elif pattern == "Donut":
        fail_rate += 0.7 * np.exp(-((radius - 0.55) ** 2) / (2 * 0.09**2))
    elif pattern == "Edge-Ring":
        fail_rate += 0.8 * np.exp(-((radius - 0.93) ** 2) / (2 * 0.07**2))
    elif pattern == "Edge-Loc":
        angle = rng.uniform(-np.pi, np.pi)
        arc = np.cos(theta - angle)
        fail_rate += 0.8 * np.exp(-((radius - 0.9) ** 2) / (2 * 0.09**2)) * np.clip(arc, 0, 1) ** 4
    elif pattern == "Loc":
        cy, cx = rng.uniform(-0.55, 0.55, size=2)
        d2 = (ry - cy) ** 2 + (rx - cx) ** 2
        fail_rate += 0.8 * np.exp(-d2 / (2 * 0.13**2))
    elif pattern == "Scratch":
        angle = rng.uniform(0, np.pi)
        offset = rng.uniform(-0.4, 0.4)
        line = np.abs(rx * np.sin(angle) - ry * np.cos(angle) - offset)
        fail_rate += 0.85 * np.exp(-(line**2) / (2 * 0.035**2))
    else:
        fail_rate += 0.05

    draw = rng.random((size, size)) < np.clip(fail_rate, 0.0, 0.98)
    wafer_map = np.where(draw, FAIL, PASS)
    return np.where(inside, wafer_map, OUTSIDE).astype(int)


def load_wafers(
    *,
    synthetic: bool,
    n_wafers: int,
    seed: int,
    subset_path: os.PathLike[str] | str = DEFAULT_SUBSET_PATH,
    raw_path: os.PathLike[str] | str = DEFAULT_RAW_PATH,
    target: str = "binary",
) -> tuple[list[WaferRecord], dict]:
    """Resolve the evaluation wafers and the dataset block for the results file."""
    if synthetic:
        records = synthetic_wafers(n_wafers, seed=seed, target=target)
        continuous = target == "continuous"
        return records, {
            "name": "synthetic-wafers-continuous" if continuous else "synthetic-wafers",
            "subset_file": None,
            "n_wafers": len(records),
            "target": target,
            "note": (
                "Stand-in wafer maps generated by nano.data.synthetic_wafers"
                + (
                    " with a continuous, noisy metrology-like target. "
                    if continuous
                    else ". "
                )
                + "Not WM-811K. Numbers from this source describe the stand-in only."
            ),
        }
    if target != "binary":
        raise ValueError(
            "WM-811K labels are binary pass/fail; a continuous target needs --synthetic."
        )
    records = load_subset(subset_path, raw_path)[:n_wafers]
    return records, {
        "name": "WM-811K",
        "subset_file": str(subset_path),
        "n_wafers": len(records),
        "target": "binary",
    }


def summarise_patterns(records: Iterable[WaferRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.pattern] = counts.get(record.pattern, 0) + 1
    return dict(sorted(counts.items()))
