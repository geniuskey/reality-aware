"""The acquisition policy: turn three maps into one decision.

    acquisition(i) = uncertainty(i) x simulation_disagreement(i) x spatial_novelty(i)

    next_index = argmax { acquisition(i) : observed_mask[i] == False }

This is the rule the documentation states and the rule the benchmark runs; the
per-term breakdown is returned with every decision so a choice can be checked
against the numbers that produced it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from nano.model import RealityEstimate

EPS = 1e-3
"""Floor under each normalised term.

A product is zero if any factor is zero, and both disagreement and novelty are
legitimately zero somewhere on every wafer. The floor keeps a term from vetoing
a candidate outright while still ranking it last on that term.
"""


@dataclass(frozen=True)
class Decision:
    index: int
    score: float
    terms: dict[str, float] = field(default_factory=dict)
    n_candidates: int = 0


class AcquisitionPolicy:
    """Pick the unmeasured die with the highest acquisition score."""

    name = "nano"
    label = "NANO"
    description = "highest acquisition score"

    def __init__(self, *, eps: float = EPS) -> None:
        self.eps = float(eps)

    def score_terms(
        self, estimate: RealityEstimate, observed_mask: np.ndarray, coords: np.ndarray
    ) -> dict[str, np.ndarray]:
        """Every term of the acquisition function, as full-wafer maps."""
        observed_mask = np.asarray(observed_mask, dtype=bool)

        uncertainty = _floor(_unit_scale(estimate.uncertainty), self.eps)
        disagreement = _floor(_unit_scale(estimate.expected_disagreement), self.eps)
        novelty = _floor(_unit_scale(_distance_to_nearest(coords, observed_mask)), self.eps)

        acquisition = uncertainty * disagreement * novelty
        acquisition = np.where(observed_mask, -np.inf, acquisition)
        return {
            "uncertainty": uncertainty,
            "disagreement": disagreement,
            "novelty": novelty,
            "acquisition": acquisition,
        }

    def select(
        self,
        estimate: RealityEstimate,
        observed_mask: np.ndarray,
        coords: np.ndarray,
        rng: np.random.Generator,
    ) -> Decision:
        terms = self.score_terms(estimate, observed_mask, coords)
        index = argmax_with_tiebreak(terms["acquisition"], rng)
        return Decision(
            index=index,
            score=float(terms["acquisition"][index]),
            terms={
                "uncertainty": float(terms["uncertainty"][index]),
                "disagreement": float(terms["disagreement"][index]),
                "novelty": float(terms["novelty"][index]),
            },
            n_candidates=int((~np.asarray(observed_mask, dtype=bool)).sum()),
        )


def argmax_with_tiebreak(scores: np.ndarray, rng: np.random.Generator) -> int:
    """``argmax`` whose ties are broken by the episode's seeded generator."""
    scores = np.asarray(scores, dtype=float)
    best = float(np.max(scores))
    if not np.isfinite(best):
        raise RuntimeError("no unmeasured die is available to select")
    ties = np.flatnonzero(scores >= best - 1e-12)
    if ties.size == 1:
        return int(ties[0])
    return int(rng.choice(ties))


def _distance_to_nearest(coords: np.ndarray, observed_mask: np.ndarray) -> np.ndarray:
    """Euclidean distance from every die to the nearest measured die."""
    coords = np.asarray(coords, dtype=float)
    obs = coords[np.asarray(observed_mask, dtype=bool)]
    if obs.shape[0] == 0:
        return np.ones(coords.shape[0])
    deltas = coords[:, None, :] - obs[None, :, :]
    d2 = np.einsum("nmk,nmk->nm", deltas, deltas)
    return np.sqrt(d2.min(axis=1))


def _unit_scale(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    low = float(values.min())
    high = float(values.max())
    if high - low <= 1e-12:
        return np.zeros_like(values)
    return (values - low) / (high - low)


def _floor(values: np.ndarray, eps: float) -> np.ndarray:
    return eps + (1.0 - eps) * values
