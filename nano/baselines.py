"""Random and Grid selection, behind the same interface as the NANO policy.

Both are driven by the same agent loop, receive the same initial observations
and spend the same budget. The selection rule is the only thing that differs
between arms, which is the property that makes the benchmark interpretable.
"""

from __future__ import annotations

import numpy as np

from nano.model import RealityEstimate
from nano.policy import Decision


class RandomPolicy:
    """Uniformly sample an unmeasured die."""

    name = "random"
    label = "Random"
    description = "uniform over unmeasured dies"

    def select(
        self,
        estimate: RealityEstimate,
        observed_mask: np.ndarray,
        coords: np.ndarray,
        rng: np.random.Generator,
    ) -> Decision:
        candidates = np.flatnonzero(~np.asarray(observed_mask, dtype=bool))
        if candidates.size == 0:
            raise RuntimeError("no unmeasured die is available to select")
        index = int(rng.choice(candidates))
        return Decision(index=index, score=0.0, terms={}, n_candidates=int(candidates.size))


class GridPolicy:
    """Pick the unmeasured die closest to the next point on a uniform lattice.

    The lattice covers the wafer's bounding box and is sized to the budget, so
    the arm spends its measurements on even spatial coverage — the conventional
    plan this project is arguing against. Lattice points are consumed in a fixed
    row-major order; a point whose neighbourhood is already fully measured is
    skipped rather than re-spent.
    """

    name = "grid"
    label = "Grid"
    description = "spatially uniform lattice"

    def __init__(self, budget: int, coords: np.ndarray) -> None:
        self.budget = int(budget)
        self._targets = self._lattice(np.asarray(coords, dtype=float), self.budget)
        self._cursor = 0

    @staticmethod
    def _lattice(coords: np.ndarray, budget: int) -> np.ndarray:
        side = max(1, int(np.ceil(np.sqrt(max(budget, 1)))))
        lo = coords.min(axis=0)
        hi = coords.max(axis=0)
        # Cell centres, so the lattice does not pile points onto the bounding box edge.
        steps = [(np.arange(side) + 0.5) / side * (hi[k] - lo[k]) + lo[k] for k in (0, 1)]
        rows, cols = np.meshgrid(steps[0], steps[1], indexing="ij")
        return np.stack([rows.ravel(), cols.ravel()], axis=1)

    def select(
        self,
        estimate: RealityEstimate,
        observed_mask: np.ndarray,
        coords: np.ndarray,
        rng: np.random.Generator,
    ) -> Decision:
        coords = np.asarray(coords, dtype=float)
        unobserved = np.flatnonzero(~np.asarray(observed_mask, dtype=bool))
        if unobserved.size == 0:
            raise RuntimeError("no unmeasured die is available to select")

        while self._cursor < len(self._targets):
            target = self._targets[self._cursor]
            self._cursor += 1
            d2 = ((coords[unobserved] - target) ** 2).sum(axis=1)
            best = float(d2.min())
            ties = unobserved[np.flatnonzero(d2 <= best + 1e-12)]
            index = int(ties[0]) if ties.size == 1 else int(rng.choice(ties))
            return Decision(
                index=index,
                score=float(-np.sqrt(best)),
                terms={"lattice_row": float(target[0]), "lattice_col": float(target[1])},
                n_candidates=int(unobserved.size),
            )

        # Lattice exhausted (budget larger than the lattice it was sized for):
        # fall back to the die furthest from anything already measured.
        obs = coords[np.asarray(observed_mask, dtype=bool)]
        deltas = coords[unobserved][:, None, :] - obs[None, :, :]
        nearest = np.sqrt(np.einsum("nmk,nmk->nm", deltas, deltas).min(axis=1))
        index = int(unobserved[int(np.argmax(nearest))])
        return Decision(
            index=index,
            score=float(nearest.max()),
            terms={"fallback": 1.0},
            n_candidates=int(unobserved.size),
        )


def build_policies(budget: int, coords: np.ndarray) -> dict[str, object]:
    """The three arms of the benchmark, in the order they are reported."""
    from nano.policy import AcquisitionPolicy

    return {
        "nano": AcquisitionPolicy(),
        "random": RandomPolicy(),
        "grid": GridPolicy(budget, coords),
    }
