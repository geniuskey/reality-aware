"""What the estimator promises: start from the prior, correct locally, report the reach."""

import numpy as np
import pytest

from nano.model import RealityModel, default_length_scale


def observe(wafer, indices):
    mask = np.zeros(wafer.n_dies, dtype=bool)
    mask[list(indices)] = True
    return mask, wafer.reality[mask]


def test_with_no_measurements_the_estimate_is_the_prior(wafer, prior):
    model = RealityModel(wafer.coords, prior)
    estimate = model.estimate(np.zeros(wafer.n_dies, dtype=bool), np.array([]))

    np.testing.assert_array_equal(estimate.prediction, prior)
    np.testing.assert_array_equal(estimate.uncertainty, np.ones(wafer.n_dies))
    np.testing.assert_array_equal(estimate.reality_gap, np.zeros(wafer.n_dies))


def test_prediction_is_exact_at_measured_dies(wafer, prior):
    model = RealityModel(wafer.coords, prior)
    indices = [3, 40, 100, 250]
    mask, values = observe(wafer, indices)
    estimate = model.estimate(mask, values)

    np.testing.assert_allclose(estimate.prediction[indices], values)


def test_uncertainty_is_zero_where_measured_and_positive_elsewhere(wafer, prior):
    model = RealityModel(wafer.coords, prior)
    mask, values = observe(wafer, [5, 60, 180])
    estimate = model.estimate(mask, values)

    assert (estimate.uncertainty[mask] == 0.0).all()
    assert (estimate.uncertainty[~mask] > 0.0).all()
    assert estimate.uncertainty.max() <= 1.0


def test_uncertainty_falls_as_measurements_accumulate(wafer, prior):
    model = RealityModel(wafer.coords, prior)
    rng = np.random.default_rng(0)
    order = rng.permutation(wafer.n_dies)

    means = []
    for count in (10, 40, 120):
        mask, values = observe(wafer, order[:count])
        means.append(float(model.estimate(mask, values).uncertainty.mean()))

    assert means[0] > means[1] > means[2]


def test_uncertainty_drops_hardest_near_a_new_measurement(wafer, prior):
    model = RealityModel(wafer.coords, prior)
    mask, values = observe(wafer, [10, 200])
    before = model.estimate(mask, values).uncertainty

    new = int(np.argmax(before))
    mask2, values2 = observe(wafer, [10, 200, new])
    after = model.estimate(mask2, values2).uncertainty

    distance = np.linalg.norm(wafer.coords - wafer.coords[new], axis=1)
    near = (distance > 0) & (distance < model.length_scale)
    far = distance > 4 * model.length_scale

    assert after[new] == 0.0
    assert far.any()
    # Uncertainty is not promised to fall everywhere - a measurement that
    # disagrees with its neighbours can legitimately raise it nearby - but the
    # neighbourhood of a new measurement must gain more than the far field.
    assert (before - after)[near].mean() > (before - after)[far].mean()


def test_influence_decays_with_distance(wafer, prior):
    model = RealityModel(wafer.coords, prior)
    index = int(np.argmax(wafer.reality))  # a failing die, so the residual is large
    mask, values = observe(wafer, [index])
    gap = np.abs(model.estimate(mask, values).reality_gap)

    distance = np.linalg.norm(wafer.coords - wafer.coords[index], axis=1)
    near = (distance > 0) & (distance < model.length_scale)
    far = distance > 4 * model.length_scale
    assert gap[near].mean() > gap[far].mean()


def test_expected_disagreement_survives_residuals_that_cancel(wafer):
    """The two "how wrong is the prior" maps must not be the same map.

    Where residuals cancel, the correction actually applied (`reality_gap`)
    goes to nothing, and a selection rule built on it would call that region
    settled. `expected_disagreement` averages magnitudes instead, so it still
    reports that the prior is known to be off here.
    """
    flat_prior = np.full(wafer.n_dies, 0.5)
    model = RealityModel(wafer.coords, flat_prior)

    # Two measurements either side of the prior, equidistant from the midpoint.
    left, right = 0, wafer.n_dies - 1
    mask = np.zeros(wafer.n_dies, dtype=bool)
    mask[[left, right]] = True
    estimate = model.estimate(mask, np.array([0.0, 1.0]))

    midpoint = int(np.argmin(np.abs(estimate.reality_gap)))
    assert abs(estimate.reality_gap[midpoint]) < 1e-6
    assert estimate.expected_disagreement[midpoint] > 0.1


def test_correction_decays_back_to_the_prior_far_from_any_measurement(wafer, prior):
    """Influence decays with distance, so the far field is the prior again.

    The estimate is only allowed to claim what measurements support. Beyond
    their reach the correction is shrunk away by `prior_weight` and the
    prediction returns to the simulation prior, with uncertainty high to say so.
    """
    # A flat mid-scale prior, so the clip at 0 and 1 cannot mask the effect.
    flat_prior = np.full(wafer.n_dies, 0.5)
    model = RealityModel(wafer.coords, flat_prior)
    indices = [0, 1, 2]
    mask = np.zeros(wafer.n_dies, dtype=bool)
    mask[indices] = True
    values = np.array([1.0, 1.0, 1.0])
    estimate = model.estimate(mask, values)

    distance = np.linalg.norm(wafer.coords - wafer.coords[0], axis=1)
    far = distance > 6 * model.length_scale
    assert far.any()

    near = ~far & ~mask
    assert np.abs(estimate.reality_gap[far]).max() < 0.01
    assert np.abs(estimate.reality_gap[near]).max() > 0.1
    assert estimate.uncertainty[far].mean() > estimate.uncertainty[near].mean()


def test_length_scale_tracks_wafer_size():
    small = np.argwhere(np.ones((12, 12), dtype=bool))
    large = np.argwhere(np.ones((60, 60), dtype=bool))
    assert default_length_scale(small) < default_length_scale(large)


def test_shape_mismatches_are_rejected(wafer, prior):
    model = RealityModel(wafer.coords, prior)
    with pytest.raises(ValueError):
        model.estimate(np.zeros(3, dtype=bool), np.array([]))
    with pytest.raises(ValueError):
        mask, _ = observe(wafer, [1, 2])
        model.estimate(mask, np.array([0.5]))
