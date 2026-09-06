"""The deliberately biased simulation prior.

Simulation is wrong in a *structured* way; noise added to ground truth would be
an easier and less interesting problem. The prior composes three distortions of
the reality field — radial bias, spatial smoothing, and a global offset and gain
— with parameters fixed per run, recorded in the results file, and identical
across every strategy arm.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from nano.data import WaferRecord


@dataclass(frozen=True)
class BiasParams:
    """Bias parameters. Deterministic: the same reality field always gives the same prior."""

    smoothing_sigma: float = 2.4
    """Blur radius in die units. Fine structure present in reality is absent from the prior."""

    radial_strength: float = 0.7
    """How strongly failure is under-predicted towards the wafer edge, in [0, 1]."""

    radial_power: float = 2.0
    """Shape of the radial fall-off. Higher keeps the wafer centre unaffected for longer."""

    gain: float = 0.85
    """Multiplicative calibration error applied to the whole wafer."""

    offset: float = 0.05
    """Additive calibration error applied to the whole wafer."""

    def as_dict(self) -> dict:
        return asdict(self)


def gaussian_blur_masked(
    field: np.ndarray, mask: np.ndarray, sigma: float, truncate: float = 3.0
) -> np.ndarray:
    """Separable Gaussian blur that ignores everything outside ``mask``.

    Normalised convolution: blurring the masked field and the mask itself and
    dividing keeps the wafer edge from being pulled towards zero by the empty
    grid positions around it. Implemented with numpy so the package does not
    depend on scipy.
    """
    if sigma <= 0:
        return np.where(mask, field, 0.0)

    radius = max(1, int(truncate * sigma + 0.5))
    offsets = np.arange(-radius, radius + 1)
    kernel = np.exp(-(offsets**2) / (2.0 * sigma**2))
    kernel /= kernel.sum()

    weights = mask.astype(float)
    values = np.where(mask, field, 0.0)
    for axis in (0, 1):
        values = _convolve1d(values, kernel, axis)
        weights = _convolve1d(weights, kernel, axis)

    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(weights > 1e-9, values / weights, 0.0)
    return np.where(mask, out, 0.0)


def _convolve1d(field: np.ndarray, kernel: np.ndarray, axis: int) -> np.ndarray:
    """Edge-padded 1-D convolution along ``axis``."""
    radius = (len(kernel) - 1) // 2
    pad = [(0, 0), (0, 0)]
    pad[axis] = (radius, radius)
    padded = np.pad(field, pad, mode="edge")
    out = np.zeros_like(field, dtype=float)
    for i, weight in enumerate(kernel):
        if weight == 0.0:
            continue
        sl = [slice(None), slice(None)]
        sl[axis] = slice(i, i + field.shape[axis])
        out += weight * padded[tuple(sl)]
    return out


def make_biased_prior(record: WaferRecord, params: BiasParams | None = None) -> np.ndarray:
    """Produce the prior the agent sees everywhere, as a flat ``(N,)`` field.

    The reality field goes in and never comes back out undistorted: this is the
    only place ground truth is used outside the observation tool and the
    evaluation harness, and its output is what the agent is asked to correct.
    """
    params = params or BiasParams()
    reality_grid = record.to_grid(record.reality, fill=0.0)

    smoothed = gaussian_blur_masked(reality_grid, record.die_mask, params.smoothing_sigma)
    prior = smoothed[record.coords[:, 0], record.coords[:, 1]]

    # Radial bias: failure is progressively under-predicted towards the edge, the
    # classic signature of a model calibrated on centre measurements.
    radius = record.radius()
    prior = prior * (1.0 - params.radial_strength * radius**params.radial_power)

    # Global calibration error.
    prior = params.gain * prior + params.offset

    return np.clip(prior, 0.0, 1.0)
