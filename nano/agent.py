"""The Observe -> Estimate -> Select -> Measure loop.

The loop spends a budget; the model produces maps. Nothing here reads ground
truth: reality enters only as the value returned by
:meth:`nano.tools.observe.ObservationTool.observe`, and the predictions the loop
records are scored later, by :mod:`nano.evaluate`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from nano.data import WaferRecord
from nano.model import RealityEstimate, RealityModel
from nano.policy import Decision
from nano.tools.observe import ObservationTool


class SelectionPolicy(Protocol):
    """What every arm of the benchmark must implement."""

    name: str

    def select(
        self,
        estimate: RealityEstimate,
        observed_mask: np.ndarray,
        coords: np.ndarray,
        rng: np.random.Generator,
    ) -> Decision: ...


@dataclass
class Step:
    """One iteration of the loop, kept for the decision trace."""

    measurements: int
    prediction: np.ndarray
    uncertainty: np.ndarray
    reality_gap: np.ndarray
    selected_index: int | None = None
    score: float | None = None
    terms: dict[str, float] = field(default_factory=dict)
    measured_value: float | None = None


@dataclass
class EpisodeResult:
    """One wafer, one seed, one strategy."""

    strategy: str
    wafer_id: str
    pattern: str
    seed: int
    n_initial: int
    budget: int
    steps: list[Step]
    observed_mask: np.ndarray
    prior: np.ndarray

    @property
    def prediction(self) -> np.ndarray:
        return self.steps[-1].prediction

    @property
    def uncertainty(self) -> np.ndarray:
        return self.steps[-1].uncertainty

    @property
    def selections(self) -> list[int]:
        return [s.selected_index for s in self.steps if s.selected_index is not None]

    def mask_at_step(self, step_index: int) -> np.ndarray:
        """Which dies had been measured when ``steps[step_index]`` was computed."""
        mask = self.observed_mask.copy()
        for step in self.steps[step_index:]:
            if step.selected_index is not None:
                mask[step.selected_index] = False
        return mask

    def values_at_step(self, step_index: int) -> np.ndarray:
        """Measured values behind ``mask_at_step``, read back from the trace.

        Ground truth is not consulted: values measured during the episode come
        from the trace, and values from the initial mask are read off the first
        prediction, which is exact at measured dies by construction.
        """
        mask = self.mask_at_step(step_index)
        values = np.array(self.steps[0].prediction, dtype=float)
        for step in self.steps:
            if step.selected_index is not None and step.measured_value is not None:
                values[step.selected_index] = step.measured_value
        return values[mask]


def draw_initial_mask(
    record: WaferRecord, n_initial: int, seed: int, *, centre_bias: float = 0.45
) -> np.ndarray:
    """Draw the initial observation mask centre-biased, not uniformly.

    Sampling plans revisit convenient sites, so the starting evidence
    under-represents the edge — the bias the whole project is about. All
    strategies start from the mask this returns for a given ``(wafer, seed)``.
    """
    n = record.n_dies
    n_initial = int(min(max(n_initial, 0), n))
    if n_initial == 0:
        return np.zeros(n, dtype=bool)

    rng = np.random.default_rng([seed, _stable_hash(record.wafer_id)])
    weights = np.exp(-(record.radius() ** 2) / (2.0 * centre_bias**2))
    weights = weights / weights.sum()
    chosen = rng.choice(n, size=n_initial, replace=False, p=weights)

    mask = np.zeros(n, dtype=bool)
    mask[chosen] = True
    return mask


def run_episode(
    record: WaferRecord,
    prior: np.ndarray,
    policy: SelectionPolicy,
    *,
    initial_mask: np.ndarray,
    budget: int,
    seed: int,
    model: RealityModel | None = None,
) -> EpisodeResult:
    """Spend ``budget`` measurements on one wafer with one selection rule."""
    tool = ObservationTool(record.reality, budget=budget, initial_mask=initial_mask)
    model = model or RealityModel(record.coords, prior)
    rng = np.random.default_rng([seed, _stable_hash(record.wafer_id), _stable_hash(policy.name)])

    steps: list[Step] = []
    while True:
        estimate = model.estimate(tool.observed_mask, tool.observed_values)
        step = Step(
            measurements=tool.n_measurements,
            prediction=estimate.prediction,
            uncertainty=estimate.uncertainty,
            reality_gap=estimate.reality_gap,
        )
        steps.append(step)

        if tool.budget_remaining <= 0 or tool.n_measurements >= record.n_dies:
            break

        decision = policy.select(estimate, tool.observed_mask, record.coords, rng)
        step.selected_index = decision.index
        step.score = decision.score
        step.terms = dict(decision.terms)
        step.measured_value = tool.observe(decision.index)

    return EpisodeResult(
        strategy=policy.name,
        wafer_id=record.wafer_id,
        pattern=record.pattern,
        seed=seed,
        n_initial=tool.n_initial,
        budget=budget,
        steps=steps,
        observed_mask=tool.observed_mask,
        prior=np.asarray(prior, dtype=float),
    )


def _stable_hash(text: str) -> int:
    """A seed component that does not change between interpreter runs."""
    value = 2166136261
    for byte in text.encode("utf-8"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return int(value)
