"""The reality model: reconcile a dense biased prior with sparse measurements.

The estimator has one job and one prohibition. The job is to pull the prior
towards ground truth wherever ground truth has actually been seen, with
influence decaying over distance, and to stay honest about how far that
correction reaches. The prohibition is ground truth at unmeasured dies: it is
never passed to this module, only to :mod:`nano.evaluate`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RealityEstimate:
    """The three maps that make a decision auditable."""

    prediction: np.ndarray  # (N,) best current estimate of reality
    uncertainty: np.ndarray  # (N,) in [0, 1], exactly 0 at measured dies
    reality_gap: np.ndarray  # (N,) signed prediction - prior, the correction actually applied
    expected_disagreement: np.ndarray  # (N,) estimated |reality - prior|, defined everywhere
    reach: np.ndarray  # (N,) total measurement influence, diagnostic
    local_spread: np.ndarray  # (N,) disagreement between nearby measurements


class RealityModel:
    """Distance-weighted correction of the prior, with a reach-based uncertainty.

    ``prediction = clip(prior + weighted mean residual, 0, 1)``, where a residual
    is ``measured value - prior`` at a measured die and weights are Gaussian in
    die distance. The weighted mean is shrunk towards zero by ``prior_weight``,
    so influence genuinely decays with distance and the estimate returns to the
    prior where nothing has been measured. Uncertainty combines two things a
    measurement plan should care about: how little measurement influence reaches
    a die at all, and how much the measurements that do reach it disagree with
    each other.
    """

    def __init__(
        self,
        coords: np.ndarray,
        prior: np.ndarray,
        *,
        length_scale: float | None = None,
        prior_weight: float = 0.5,
        spread_weight: float = 0.5,
    ) -> None:
        self.coords = np.asarray(coords, dtype=float)
        self.prior = np.asarray(prior, dtype=float)
        if self.coords.shape[0] != self.prior.shape[0]:
            raise ValueError("coords and prior must describe the same dies")
        self.length_scale = float(
            length_scale if length_scale is not None else default_length_scale(self.coords)
        )
        self.prior_weight = float(prior_weight)
        self.spread_weight = float(spread_weight)

    def estimate(
        self, observed_mask: np.ndarray, observed_values: np.ndarray
    ) -> RealityEstimate:
        """Produce prediction, uncertainty and reality-gap maps over every die."""
        observed_mask = np.asarray(observed_mask, dtype=bool)
        observed_values = np.asarray(observed_values, dtype=float)
        n = self.prior.shape[0]
        if observed_mask.shape != (n,):
            raise ValueError("observed_mask must have shape (N,)")
        if observed_values.shape[0] != int(observed_mask.sum()):
            raise ValueError("observed_values must hold one value per observed die")

        # With no measurements the estimate *is* the prior, and the agent is
        # maximally uncertain everywhere.
        if observed_values.size == 0:
            return RealityEstimate(
                prediction=self.prior.copy(),
                uncertainty=np.ones(n),
                reality_gap=np.zeros(n),
                expected_disagreement=np.zeros(n),
                reach=np.zeros(n),
                local_spread=np.zeros(n),
            )

        obs_idx = np.flatnonzero(observed_mask)
        deltas = self.coords[:, None, :] - self.coords[None, obs_idx, :]
        d2 = np.einsum("nmk,nmk->nm", deltas, deltas)
        weights = np.exp(-d2 / (2.0 * self.length_scale**2))  # (N, M)

        residuals = observed_values - self.prior[obs_idx]
        reach = weights.sum(axis=1)
        # The prior counts as `prior_weight` measurements' worth of evidence for
        # "no correction here". So the correction decays smoothly to zero as the
        # measurements' influence fades, instead of extrapolating a global offset
        # into regions nothing has been measured in. The value is fixed before the
        # comparison, identical across every arm, and recorded in the results file.
        denom = reach + self.prior_weight

        mean_residual = (weights @ residuals) / denom
        mean_square = (weights @ (residuals**2)) / denom
        variance = np.clip(mean_square - mean_residual**2, 0.0, None)
        local_spread = np.sqrt(variance)

        prediction = np.clip(self.prior + mean_residual, 0.0, 1.0)
        # A measured die is known, not estimated.
        prediction[obs_idx] = np.clip(observed_values, 0.0, 1.0)

        # Uncertainty has two sources. `base` is reach: how little measurement
        # influence arrives here at all, 1.0 where none does. Disagreement
        # between the measurements that *do* reach a die pushes it back up
        # towards 1, because coverage without agreement is not knowledge.
        #
        # The scale is absolute, not per-step: 1.0 is "nothing measured reaches
        # this die", 0.0 is "measured". Normalising each step by its own maximum
        # would make two uncertainty maps from one episode incomparable, and the
        # claim that uncertainty falls as budget is spent unfalsifiable.
        base = 1.0 / (1.0 + reach)
        # Values live in [0, 1], so the largest possible local spread is 0.5.
        spread_term = np.clip(local_spread / 0.5, 0.0, 1.0)
        uncertainty = base + (1.0 - base) * self.spread_weight * spread_term
        uncertainty[obs_idx] = 0.0

        reality_gap = prediction - self.prior

        # How wrong the prior is expected to be here. `reality_gap` answers a
        # different question - how much the estimate has *already* been moved -
        # and it necessarily decays to zero far from every measurement, which
        # would make it useless for deciding where to look next. This is a
        # shrinkage estimate instead: the locally weighted residual magnitude,
        # pulled towards the wafer-wide mean residual magnitude wherever local
        # evidence is thin.
        local_magnitude = (weights @ np.abs(residuals)) / denom
        global_magnitude = float(np.abs(residuals).mean())
        shrink = reach / (reach + self.prior_weight)
        expected_disagreement = shrink * local_magnitude + (1.0 - shrink) * global_magnitude

        return RealityEstimate(
            prediction=prediction,
            uncertainty=uncertainty,
            reality_gap=reality_gap,
            expected_disagreement=expected_disagreement,
            reach=reach,
            local_spread=local_spread,
        )


def default_length_scale(coords: np.ndarray) -> float:
    """A length scale in die units, tied to wafer size rather than hard-coded.

    Roughly a twelfth of the wafer span: wide enough that one measurement
    informs its neighbourhood, narrow enough that it does not claim to explain
    the opposite edge.
    """
    coords = np.asarray(coords, dtype=float)
    span = float(np.max(coords.max(axis=0) - coords.min(axis=0) + 1.0))
    return max(1.5, span / 12.0)


def _unit_scale(values: np.ndarray) -> np.ndarray:
    """Min-max to [0, 1]; a flat field maps to zeros rather than to NaN."""
    values = np.asarray(values, dtype=float)
    low = float(values.min())
    high = float(values.max())
    if high - low <= 1e-12:
        return np.zeros_like(values)
    return (values - low) / (high - low)
