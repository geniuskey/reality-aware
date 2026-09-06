"""The observation tool — the only channel from reality to the agent.

Budget accounting lives inside the tool rather than in the caller, so no
strategy can quietly take an extra look. Everything the agent is allowed to know
about reality is what ``observe`` has returned.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class BudgetExhausted(RuntimeError):
    """Raised when a measurement is requested with no budget left."""


class AlreadyObserved(ValueError):
    """Raised when a die that has already been measured is requested again."""


@dataclass(frozen=True)
class Measurement:
    step: int
    index: int
    value: float
    budget_remaining: int


class ObservationTool:
    """Reveals one die's value and spends one unit of budget.

    The reality field is held privately. Nothing in :mod:`nano.model`,
    :mod:`nano.policy`, :mod:`nano.baselines` or :mod:`nano.agent` receives it —
    they only ever see ``observed_mask`` and ``observed_values``.
    """

    def __init__(
        self,
        reality: np.ndarray,
        budget: int,
        initial_mask: np.ndarray | None = None,
    ) -> None:
        reality = np.asarray(reality, dtype=float)
        if reality.ndim != 1:
            raise ValueError(f"reality must be flat (N,), got shape {reality.shape}")
        if budget < 0:
            raise ValueError("budget must be non-negative")

        self.__reality = reality.copy()
        self._n = reality.shape[0]
        self._budget_total = int(budget)
        self._budget_remaining = int(budget)
        self._mask = np.zeros(self._n, dtype=bool)
        self._values = np.full(self._n, np.nan, dtype=float)
        self.trace: list[Measurement] = []

        if initial_mask is not None:
            initial_mask = np.asarray(initial_mask, dtype=bool)
            if initial_mask.shape != (self._n,):
                raise ValueError("initial_mask must have shape (N,)")
            # Initial observations are handed to every arm identically and are not
            # charged against the additional budget — that is what makes the arms
            # comparable. They are counted separately as `n_initial`.
            self._mask |= initial_mask
            self._values[initial_mask] = self.__reality[initial_mask]
        self._n_initial = int(self._mask.sum())

    # -- state the agent may read -------------------------------------------
    @property
    def n_dies(self) -> int:
        return self._n

    @property
    def observed_mask(self) -> np.ndarray:
        return self._mask.copy()

    @property
    def observed_values(self) -> np.ndarray:
        """Measured values, ordered by die index — shape ``(M,)``."""
        return self._values[self._mask].copy()

    @property
    def observed_indices(self) -> np.ndarray:
        return np.flatnonzero(self._mask)

    @property
    def budget_remaining(self) -> int:
        return self._budget_remaining

    @property
    def budget_spent(self) -> int:
        return self._budget_total - self._budget_remaining

    @property
    def n_initial(self) -> int:
        return self._n_initial

    @property
    def n_measurements(self) -> int:
        """Initial observations plus every measurement taken since."""
        return int(self._mask.sum())

    # -- the one operation that touches reality ------------------------------
    def observe(self, index: int) -> float:
        """Measure die ``index``, spending one unit of budget."""
        index = int(index)
        if not 0 <= index < self._n:
            raise IndexError(f"die index {index} out of range for {self._n} dies")
        if self._mask[index]:
            raise AlreadyObserved(f"die {index} has already been measured")
        if self._budget_remaining <= 0:
            raise BudgetExhausted("measurement budget is exhausted")

        self._budget_remaining -= 1
        self._mask[index] = True
        value = float(self.__reality[index])
        self._values[index] = value
        self.trace.append(
            Measurement(
                step=len(self.trace) + 1,
                index=index,
                value=value,
                budget_remaining=self._budget_remaining,
            )
        )
        return value
