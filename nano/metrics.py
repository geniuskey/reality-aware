"""Metrics, and the paired statistics that say whether a difference is real.

Two things live here that the first version of this project got wrong by
omission. First, mean absolute error over every in-wafer die is dominated by
class imbalance when most dies pass — a predictor that answers "nothing fails"
scores well on it while knowing nothing — so the class-balanced variants are
computed alongside it and reported next to it. Second, a difference of means
without an interval is not a result; every strategy comparison is bootstrapped
over the paired episodes it came from.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

BINARY = "binary"
CONTINUOUS = "continuous"


def mae(prediction: np.ndarray, reality: np.ndarray) -> float:
    """Reconstruction error over every in-wafer die. Lower is better."""
    prediction = np.asarray(prediction, dtype=float)
    reality = np.asarray(reality, dtype=float)
    if prediction.shape != reality.shape:
        raise ValueError("prediction and reality must cover the same dies")
    return float(np.abs(prediction - reality).mean())


def rmse(prediction: np.ndarray, reality: np.ndarray) -> float:
    prediction = np.asarray(prediction, dtype=float)
    reality = np.asarray(reality, dtype=float)
    if prediction.shape != reality.shape:
        raise ValueError("prediction and reality must cover the same dies")
    return float(np.sqrt(np.mean((prediction - reality) ** 2)))


def _subset_mae(prediction: np.ndarray, reality: np.ndarray, mask: np.ndarray) -> float:
    if not mask.any():
        return float("nan")
    return float(np.abs(np.asarray(prediction)[mask] - np.asarray(reality)[mask]).mean())


def metric_set(
    prediction: np.ndarray, reality: np.ndarray, target_kind: str = BINARY
) -> dict[str, float]:
    """Every metric that applies to this target, keyed by name.

    ``mae`` stays the primary metric because it is the one the site is built
    around, but it is never reported alone: on a binary target the balanced
    variant is what a trivial constant predictor cannot game.
    """
    values = {"mae": mae(prediction, reality), "rmse": rmse(prediction, reality)}
    if target_kind == BINARY:
        reality = np.asarray(reality, dtype=float)
        failing = reality > 0.5
        passing = ~failing
        values["mae_failing"] = _subset_mae(prediction, reality, failing)
        values["mae_passing"] = _subset_mae(prediction, reality, passing)
        # Mean of the two class errors: a constant predictor scores 0.5 here
        # however rare failures are, which is the point.
        pair = [values["mae_failing"], values["mae_passing"]]
        values["balanced_mae"] = float(np.nanmean(pair)) if not all(np.isnan(pair)) else float("nan")
    return values


DEFAULT_PRIMARY = {BINARY: "balanced_mae", CONTINUOUS: "mae"}
"""Which metric leads the report, per target kind.

On a binary target with rare failures, plain MAE is led by the majority class:
the constant "nothing fails" predictor beats every strategy on it while reading
no measurement at all. The balanced variant is primary because a predictor that
knows nothing scores exactly 0.5 on it — the criterion is that chance must look
like chance, not that any particular arm wins. Plain MAE stays in every results
file, and where the two metrics disagree the benchmark page says so.
"""

METRIC_LABELS = {
    "mae": {"name": "MAE", "unit": "failure probability", "scope": "all in-wafer dies"},
    "balanced_mae": {
        "name": "Balanced MAE",
        "unit": "failure probability",
        "scope": "mean of the failing-die and passing-die errors",
    },
    "mae_failing": {
        "name": "MAE on failing dies",
        "unit": "failure probability",
        "scope": "dies whose hidden value is 1.0",
    },
    "mae_passing": {
        "name": "MAE on passing dies",
        "unit": "failure probability",
        "scope": "dies whose hidden value is 0.0",
    },
    "rmse": {"name": "RMSE", "unit": "failure probability", "scope": "all in-wafer dies"},
}


@dataclass(frozen=True)
class PairedComparison:
    """One arm against another, over the episodes they both ran."""

    n: int
    wins: int
    losses: int
    ties: int
    mean: float
    ci_low: float
    ci_high: float
    relative_mean: float
    relative_ci_low: float
    relative_ci_high: float
    separates: bool
    confidence: float
    resamples: int
    seed: int

    def as_dict(self) -> dict:
        return {
            "n": self.n,
            "wins": self.wins,
            "losses": self.losses,
            "ties": self.ties,
            "mean": round(self.mean, 6),
            "ci_low": round(self.ci_low, 6),
            "ci_high": round(self.ci_high, 6),
            "relative_mean": round(self.relative_mean, 4),
            "relative_ci_low": round(self.relative_ci_low, 4),
            "relative_ci_high": round(self.relative_ci_high, 4),
            "separates": self.separates,
            "confidence": self.confidence,
            "method": (
                f"paired bootstrap over {self.n} episodes, {self.resamples} resamples, "
                f"seed {self.seed}"
            ),
        }


def paired_bootstrap(
    baseline: Sequence[float],
    candidate: Sequence[float],
    *,
    confidence: float = 0.95,
    resamples: int = 2000,
    seed: int = 0,
    lower_is_better: bool = True,
) -> PairedComparison:
    """Bootstrap the paired difference ``baseline − candidate`` over episodes.

    Episodes are the unit of resampling because that is the unit the experiment
    pairs: the same wafer, seed, prior and initial mask ran through both arms, so
    the difference within an episode is the only quantity that isolates the
    selection rule. ``separates`` is False when the interval spans zero — which
    is the honest reading of a mean improvement the evidence cannot support.
    """
    baseline = np.asarray(baseline, dtype=float)
    candidate = np.asarray(candidate, dtype=float)
    if baseline.shape != candidate.shape:
        raise ValueError("paired comparison needs one value per episode from each arm")
    if baseline.size == 0:
        raise ValueError("paired comparison needs at least one episode")

    sign = 1.0 if lower_is_better else -1.0
    deltas = sign * (baseline - candidate)

    rng = np.random.default_rng(seed)
    picks = rng.integers(0, baseline.size, size=(resamples, baseline.size))
    boot_delta = deltas[picks].mean(axis=1)
    boot_baseline = baseline[picks].mean(axis=1)
    boot_candidate = candidate[picks].mean(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        boot_relative = np.where(
            boot_baseline != 0, sign * (boot_baseline - boot_candidate) / boot_baseline * 100.0, np.nan
        )

    tail = (1.0 - confidence) / 2.0 * 100.0
    ci_low, ci_high = np.percentile(boot_delta, [tail, 100.0 - tail])
    # A baseline that is exactly zero has no relative scale — an arm can be a
    # fixed amount better than "no error at all" but not a percentage better.
    if np.isnan(boot_relative).all():
        rel_low = rel_high = relative_mean = float("nan")
    else:
        rel_low, rel_high = np.nanpercentile(boot_relative, [tail, 100.0 - tail])
        relative_mean = (
            sign * (baseline.mean() - candidate.mean()) / baseline.mean() * 100.0
            if baseline.mean() != 0
            else float("nan")
        )

    return PairedComparison(
        n=int(baseline.size),
        wins=int((deltas > 0).sum()),
        losses=int((deltas < 0).sum()),
        ties=int((deltas == 0).sum()),
        mean=float(deltas.mean()),
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        relative_mean=float(relative_mean),
        relative_ci_low=float(rel_low),
        relative_ci_high=float(rel_high),
        separates=bool(ci_low > 0 or ci_high < 0),
        confidence=float(confidence),
        resamples=int(resamples),
        seed=int(seed),
    )
