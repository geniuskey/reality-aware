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
from nano.policy import ABLATIONS, TERMS, AcquisitionPolicy
from nano.data import WaferRecord, summarise_patterns
from nano.metrics import (
    DEFAULT_PRIMARY,
    METRIC_LABELS,
    mae,
    metric_set,
    paired_bootstrap,
    rank_correlation,
    reliability_bins,
)
from nano.model import RealityModel, default_length_scale
from nano.prior import BiasParams, make_biased_prior

SCHEMA_VERSION = 1
DEFAULT_OUTPUT = Path("results/benchmark_summary.json")
ACQUISITION_RULE = "uncertainty x simulation_disagreement x spatial_novelty"
BOOTSTRAP_SEED = 0
BOOTSTRAP_RESAMPLES = 2000


def error_curve(
    episode: EpisodeResult,
    reality: np.ndarray,
    *,
    metric: str = "mae",
    target_kind: str = "binary",
) -> list[tuple[int, float]]:
    """``(measurements, error)`` after every step of one episode, on one metric."""
    return [
        (step.measurements, metric_set(step.prediction, reality, target_kind)[metric])
        for step in episode.steps
    ]


def run_benchmark(
    records: Sequence[WaferRecord],
    *,
    seeds: Sequence[int],
    initial_measurements: int,
    budget: int,
    bias: BiasParams | None = None,
    length_scale: float | None = None,
    prior_weight: float = 0.5,
    primary_metric: str | None = None,
    ablation: bool = False,
    terms: Sequence[str] | None = None,
    dataset_block: dict | None = None,
) -> dict:
    """Run every strategy on every ``(wafer, seed)`` pair and summarise the result.

    All arms of a pair share the wafer, the prior, the initial observation mask
    and the budget. Only the selection rule differs.
    """
    if not records:
        raise ValueError("no evaluation wafers were provided")
    bias = bias or BiasParams()
    target_kind = records[0].target_kind
    terms = tuple(terms or TERMS)
    primary = primary_metric or DEFAULT_PRIMARY[target_kind]
    if primary not in METRIC_LABELS:
        raise ValueError(f"unknown metric {primary!r}; known: {sorted(METRIC_LABELS)}")

    curves: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    by_pattern: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    episodes: list[dict] = []
    # Calibration evidence, pooled over episodes: the uncertainty NANO reported
    # at each die it never measured, against the error it actually made there.
    calibration_uncertainty: list[np.ndarray] = []
    calibration_error: list[np.ndarray] = []
    calibration_rho: list[float] = []

    for record in records:
        if record.target_kind != target_kind:
            raise ValueError("every evaluation wafer must carry the same target kind")

        prior = make_biased_prior(record, bias)
        model_scale = (
            float(length_scale) if length_scale is not None else default_length_scale(record.coords)
        )

        # Two predictors that spend no budget at all. They are not strategies —
        # they ignore every measurement — but a selection rule that cannot beat
        # them has not earned the tool time it spent, and on an imbalanced binary
        # target the constant one is a genuinely hard MAE baseline.
        references = {
            "prior": prior,
            "constant": np.full(record.n_dies, _constant_value(prior, target_kind)),
        }
        for name, prediction in references.items():
            for metric, value in metric_set(prediction, record.reality, target_kind).items():
                scores[name][metric].extend([value] * len(seeds))

        for seed in seeds:
            initial_mask = draw_initial_mask(record, initial_measurements, seed)
            entry = {
                "wafer_id": record.wafer_id,
                "pattern": record.pattern,
                "seed": int(seed),
                "n_dies": record.n_dies,
                "prior_error": round(scores["prior"][primary][0], 6),
                "final": {},
            }
            for name, prediction in references.items():
                entry["final"][name] = round(
                    metric_set(prediction, record.reality, target_kind)[primary], 6
                )

            for name, policy in _arms(budget, record.coords, ablation, terms).items():
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
                for measurements, value in error_curve(
                    episode, record.reality, metric=primary, target_kind=target_kind
                ):
                    curves[name][measurements].append(value)
                for metric, value in metric_set(
                    episode.prediction, record.reality, target_kind
                ).items():
                    scores[name][metric].append(value)
                final = scores[name][primary][-1]
                by_pattern[name][record.pattern].append(final)
                entry["final"][name] = round(final, 6)

                if name == "nano":
                    # Only unmeasured dies: a measured die has zero uncertainty
                    # and zero error by construction, and including those would
                    # manufacture a correlation out of the tool's own bookkeeping.
                    unseen = ~episode.observed_mask
                    if unseen.any():
                        unseen_uncertainty = episode.uncertainty[unseen]
                        unseen_error = np.abs(episode.prediction[unseen] - record.reality[unseen])
                        calibration_uncertainty.append(unseen_uncertainty)
                        calibration_error.append(unseen_error)
                        calibration_rho.append(
                            rank_correlation(unseen_uncertainty, unseen_error)
                        )

            episodes.append(entry)

    arms = _arms(budget, records[0].coords, ablation, terms)
    strategies = {}
    for name, policy in arms.items():
        if name in ABLATIONS and name != "nano":
            continue  # ablation arms are reported separately, not as strategies
        strategies[name] = {
            "label": policy.label,
            "description": policy.description,
            "final": _stats(scores[name][primary]),
            "metrics": {metric: _stats(values) for metric, values in scores[name].items()},
            "curve": [
                {"measurements": m, **_stats(curves[name][m])}
                for m in sorted(curves[name])
            ],
            "by_pattern": {
                pattern: {**_stats(values), "n": len(values)}
                for pattern, values in sorted(by_pattern[name].items())
            },
        }

    ablation_block = {
        name: {
            "label": arms[name].label,
            "rule": arms[name].rule,
            "terms": list(arms[name].terms),
            "final": _stats(scores[name][primary]),
            "metrics": {metric: _stats(values) for metric, values in scores[name].items()},
        }
        for name in arms
        if name in ABLATIONS and name != "nano"
    }

    calibration = _calibration_block(
        calibration_uncertainty, calibration_error, calibration_rho
    )

    reference_block = {
        "prior": {
            "label": "Uncorrected prior",
            "description": "the simulation prior, with no measurement applied",
            "final": _stats(scores["prior"][primary]),
            "metrics": {metric: _stats(values) for metric, values in scores["prior"].items()},
        },
        "constant": {
            "label": "Constant",
            "description": _constant_description(target_kind),
            "final": _stats(scores["constant"][primary]),
            "metrics": {metric: _stats(values) for metric, values in scores["constant"].items()},
        },
    }

    # Every comparison is against NANO, over the episodes both arms ran, on every
    # metric — so a claim that holds on one metric and fails on another cannot be
    # reported as if it held on both.
    comparisons: dict[str, dict[str, dict]] = {}
    for metric in sorted(scores["nano"]):
        per_metric = {}
        for name in list(strategies) + list(reference_block) + list(ablation_block):
            if name == "nano" or metric not in scores[name]:
                continue
            values = np.asarray(scores[name][metric], dtype=float)
            nano_values = np.asarray(scores["nano"][metric], dtype=float)
            if np.isnan(values).any() or np.isnan(nano_values).any():
                continue
            per_metric[name] = paired_bootstrap(
                values,
                nano_values,
                resamples=BOOTSTRAP_RESAMPLES,
                seed=BOOTSTRAP_SEED,
            ).as_dict()
        comparisons[metric] = per_metric

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
            "acquisition_rule": " x ".join(terms),
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
        "metric": {**METRIC_LABELS[primary], "key": primary, "direction": "lower_is_better"},
        "metrics": {
            key: {**METRIC_LABELS[key], "direction": "lower_is_better"}
            for key in sorted(scores["nano"])
        },
        "prior": {"initial_error": _stats(scores["prior"][primary])},
        "strategies": strategies,
        "references": reference_block,
        "ablation": ablation_block,
        "calibration": calibration,
        "comparisons": comparisons,
        "episodes": episodes,
        "assets": {
            "calibration": "results/calibration.svg",
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
    """Write the results file as JSON the site can actually parse.

    A metric can legitimately have no value — a percentage improvement over a
    baseline of exactly zero, for instance — and Python would happily write that
    as a bare `NaN`, which is not JSON. Those become `null`, and `allow_nan=False`
    makes any that slip through a loud failure here rather than a broken build
    later.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(json_safe(summary), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return out


def json_safe(value):
    """Replace every non-finite float with None, recursively."""
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, (np.floating, np.integer)):
        return json_safe(value.item())
    return value


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


def _calibration_block(
    uncertainty: list[np.ndarray], errors: list[np.ndarray], rho: list[float]
) -> dict:
    """Does the uncertainty map order the dies by how wrong the estimate is?

    NANO ranks locations by uncertainty, so this is the property the acquisition
    rule actually depends on. It is *not* a calibration claim in the strict
    sense: no interval is stated, so no coverage can be checked, and the field is
    named `rank_correlation` rather than `calibration_error` to keep those apart.
    """
    if not uncertainty:
        return {}
    pooled_uncertainty = np.concatenate(uncertainty)
    pooled_error = np.concatenate(errors)
    finite = np.asarray([value for value in rho if np.isfinite(value)], dtype=float)
    return {
        "scope": "unmeasured dies at the end of the budget, NANO arm",
        "n_dies": int(pooled_uncertainty.size),
        "rank_correlation": {
            "pooled": round(rank_correlation(pooled_uncertainty, pooled_error), 6),
            "per_episode_mean": round(float(finite.mean()), 6) if finite.size else None,
            "per_episode_std": round(float(finite.std(ddof=0)), 6) if finite.size else None,
            "note": (
                "Spearman correlation between reported uncertainty and absolute error. "
                "Positive means the map ranks usefully; it is not a coverage claim."
            ),
        },
        "reliability": reliability_bins(pooled_uncertainty, pooled_error),
    }


def _arms(budget: int, coords: np.ndarray, ablation: bool, terms: Sequence[str] = TERMS) -> dict:
    """The arms one episode runs: the three strategies, plus ablations on request.

    Ablation arms go through the same loop, the same budget and the same initial
    mask as everything else — the only difference is which terms their
    acquisition product contains.
    """
    arms = dict(build_policies(budget, coords, terms))
    if ablation:
        for name, terms in ABLATIONS.items():
            if name != "nano":
                arms[name] = AcquisitionPolicy(terms)
    return arms


def _constant_value(prior: np.ndarray, target_kind: str) -> float:
    """The value a measurement-free constant predictor answers everywhere.

    Chosen without looking at reality: on a binary target it is "no die fails",
    and on a continuous one it is the prior's own mean level.
    """
    if target_kind == "binary":
        return 0.0
    return float(np.mean(prior))


def _constant_description(target_kind: str) -> str:
    if target_kind == "binary":
        return 'predicts 0.0 everywhere — "no die fails" — and reads no measurement'
    return "predicts the prior's mean level everywhere and reads no measurement"
