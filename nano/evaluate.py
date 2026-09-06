"""Scoring and aggregation — the only module that reads full reality fields.

Nothing here is returned to the agent. It consumes the predictions an episode
recorded, compares them to hidden ground truth, and writes
``results/benchmark_summary.json``, the single source of truth for the
documentation site.
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from nano.agent import EpisodeResult, draw_initial_mask, run_episode
from nano.baselines import build_policies
from nano.data import WaferRecord, summarise_patterns
from nano.model import RealityModel, default_length_scale
from nano.prior import BiasParams, make_biased_prior

SCHEMA_VERSION = 1
METRIC = {"name": "MAE", "direction": "lower_is_better", "unit": "failure probability"}
DEFAULT_OUTPUT = Path("results/benchmark_summary.json")
ACQUISITION_RULE = "uncertainty x simulation_disagreement x spatial_novelty"


def mae(prediction: np.ndarray, reality: np.ndarray) -> float:
    """Reconstruction error over every in-wafer die. Lower is better."""
    prediction = np.asarray(prediction, dtype=float)
    reality = np.asarray(reality, dtype=float)
    if prediction.shape != reality.shape:
        raise ValueError("prediction and reality must cover the same dies")
    return float(np.abs(prediction - reality).mean())


def error_curve(episode: EpisodeResult, reality: np.ndarray) -> list[tuple[int, float]]:
    """``(measurements, error)`` after every step of one episode."""
    return [(step.measurements, mae(step.prediction, reality)) for step in episode.steps]


def run_benchmark(
    records: Sequence[WaferRecord],
    *,
    seeds: Sequence[int],
    initial_measurements: int,
    budget: int,
    bias: BiasParams | None = None,
    length_scale: float | None = None,
    prior_weight: float = 0.5,
    dataset_block: dict | None = None,
) -> dict:
    """Run every strategy on every ``(wafer, seed)`` pair and summarise the result.

    All arms of a pair share the wafer, the prior, the initial observation mask
    and the budget. Only the selection rule differs.
    """
    if not records:
        raise ValueError("no evaluation wafers were provided")
    bias = bias or BiasParams()

    curves: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    finals: dict[str, list[float]] = defaultdict(list)
    by_pattern: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    prior_errors: list[float] = []
    episodes: list[dict] = []

    for record in records:
        prior = make_biased_prior(record, bias)
        prior_error = mae(prior, record.reality)
        model_scale = (
            float(length_scale) if length_scale is not None else default_length_scale(record.coords)
        )

        for seed in seeds:
            initial_mask = draw_initial_mask(record, initial_measurements, seed)
            prior_errors.append(prior_error)
            entry = {
                "wafer_id": record.wafer_id,
                "pattern": record.pattern,
                "seed": int(seed),
                "n_dies": record.n_dies,
                "prior_error": round(prior_error, 6),
                "final": {},
            }

            for name, policy in build_policies(budget, record.coords).items():
                model = RealityModel(
                    record.coords, prior, length_scale=model_scale, prior_weight=prior_weight
                )
                episode = run_episode(
                    record,
                    prior,
                    policy,
                    initial_mask=initial_mask,
                    budget=budget,
                    seed=seed,
                    model=model,
                )
                for measurements, value in error_curve(episode, record.reality):
                    curves[name][measurements].append(value)
                final = mae(episode.prediction, record.reality)
                finals[name].append(final)
                by_pattern[name][record.pattern].append(final)
                entry["final"][name] = round(final, 6)

            episodes.append(entry)

    strategies = {}
    for name, policy in build_policies(budget, records[0].coords).items():
        strategies[name] = {
            "label": policy.label,
            "description": policy.description,
            "final": _stats(finals[name]),
            "curve": [
                {"measurements": m, **_stats(curves[name][m])}
                for m in sorted(curves[name])
            ],
            "by_pattern": {
                pattern: {**_stats(values), "n": len(values)}
                for pattern, values in sorted(by_pattern[name].items())
            },
        }

    shapes = Counter(record.grid_shape for record in records)
    modal_shape, _ = shapes.most_common(1)[0]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_commit": _git_commit(),
        "dataset": {
            **(dataset_block or {"name": records[0].source, "n_wafers": len(records)}),
            "patterns": summarise_patterns(records),
        },
        "experiment": {
            "seeds": [int(s) for s in seeds],
            "initial_measurements": int(initial_measurements),
            "measurement_budget": int(budget),
            "grid_shape": [int(modal_shape[0]), int(modal_shape[1])],
            "grid_shape_note": "modal die grid across the evaluation wafers; wafers are never resized",
            "mean_dies_per_wafer": round(float(np.mean([r.n_dies for r in records])), 1),
            "episodes": len(episodes),
            "acquisition_rule": ACQUISITION_RULE,
            "prior_bias": bias.as_dict(),
            "model": {
                "kernel": "gaussian",
                "length_scale": (
                    round(float(length_scale), 4)
                    if length_scale is not None
                    else "per-wafer default (wafer span / 12)"
                ),
                "prior_weight": round(float(prior_weight), 4),
            },
        },
        "metric": dict(METRIC),
        "prior": {"initial_error": _stats(prior_errors)},
        "strategies": strategies,
        "episodes": episodes,
        "assets": {
            "error_curve": "results/error_curve.svg",
            "wafer_comparison": "results/wafer_comparison.webp",
            "uncertainty_before_after": "results/uncertainty_before_after.webp",
            "paired_improvement": "results/paired_improvement.svg",
        },
    }


def relative_improvement(baseline: float, nano: float) -> float:
    """``(baseline - nano) / baseline * 100``. Positive means NANO was better."""
    if baseline == 0:
        return float("nan")
    return (baseline - nano) / baseline * 100.0


def write_summary(summary: dict, path: Path | str = DEFAULT_OUTPUT) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return out


def _stats(values: Iterable[float]) -> dict[str, float]:
    array = np.asarray(list(values), dtype=float)
    if array.size == 0:
        return {"mean": float("nan"), "std": float("nan")}
    return {"mean": round(float(array.mean()), 6), "std": round(float(array.std(ddof=0)), 6)}


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - environment dependent
        return None
    commit = out.stdout.strip()
    return commit or None
