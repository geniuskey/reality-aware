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


def rank_correlation(a: Sequence[float], b: Sequence[float]) -> float:
    """Spearman correlation, computed from ranks with numpy alone.

    Ranking is the claim NANO actually makes about its uncertainty map — that a
    die it calls more uncertain is a die it is more likely to be wrong about.
    Correlation of ranks is the direct test of it, and it needs no assumption
    about the shape of either distribution.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape:
        raise ValueError("rank correlation needs two equal-length sequences")
    if a.size < 2:
        return float("nan")
    ranks = np.corrcoef(_ranks(a), _ranks(b))[0, 1]
    return float(ranks)


def _ranks(values: np.ndarray) -> np.ndarray:
    """Average ranks, so ties do not distort the correlation."""
    order = np.argsort(values, kind="stable")
    ranks = np.empty(values.size, dtype=float)
    ranks[order] = np.arange(values.size, dtype=float)

    sorted_values = values[order]
    start = 0
    for stop in range(1, values.size + 1):
        if stop == values.size or sorted_values[stop] != sorted_values[start]:
            if stop - start > 1:
                ranks[order[start:stop]] = ranks[order[start:stop]].mean()
            start = stop
    return ranks


def reliability_bins(
    uncertainty: Sequence[float],
    absolute_error: Sequence[float],
    *,
    bins: int = 10,
) -> list[dict]:
    """Group dies by predicted uncertainty and report the error actually made.

    This does not test calibration in the strict sense — no interval is claimed,
    so none can be checked for coverage. It tests the weaker property the
    acquisition rule relies on: that uncertainty *orders* the dies by how wrong
    the estimate is there. A flat curve would mean the map is decorative.
    """
    uncertainty = np.asarray(uncertainty, dtype=float)
    absolute_error = np.asarray(absolute_error, dtype=float)
    if uncertainty.shape != absolute_error.shape:
        raise ValueError("reliability needs one error per uncertainty value")
    if uncertainty.size == 0:
        return []

    # Equal-count bins: equal-width ones would leave most bins nearly empty,
    # because uncertainty piles up once a budget has been spent.
    edges = np.quantile(uncertainty, np.linspace(0.0, 1.0, bins + 1))
    edges[0], edges[-1] = uncertainty.min(), uncertainty.max() + 1e-12
    index = np.clip(np.searchsorted(edges, uncertainty, side="right") - 1, 0, bins - 1)

    out = []
    for b in range(bins):
        selected = index == b
        if not selected.any():
            continue
        out.append(
            {
                "bin": b,
                "uncertainty_low": round(float(edges[b]), 6),
                "uncertainty_high": round(float(edges[b + 1]), 6),
                "mean_uncertainty": round(float(uncertainty[selected].mean()), 6),
                "mean_absolute_error": round(float(absolute_error[selected].mean()), 6),
                "n": int(selected.sum()),
            }
        )
    return out
