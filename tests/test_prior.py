"""The prior must be wrong in the documented, structured way."""

import numpy as np

from nano.prior import BiasParams, gaussian_blur_masked, make_biased_prior


def test_prior_is_a_probability_field_over_every_die(wafer, prior):
    assert prior.shape == (wafer.n_dies,)
    assert prior.min() >= 0.0
    assert prior.max() <= 1.0


def test_prior_is_deterministic(wafer):
    np.testing.assert_array_equal(make_biased_prior(wafer), make_biased_prior(wafer))


def test_radial_bias_suppresses_the_edge_and_spares_the_centre(edge_wafer):
    """The distortion has to be radial, not a uniform shift.

    Compared against the same prior with the radial term switched off, failure
    must be pushed down at the edge while the centre is left roughly alone.
    """
    unbiased = make_biased_prior(edge_wafer, BiasParams(radial_strength=0.0))
    biased = make_biased_prior(edge_wafer, BiasParams(radial_strength=0.7))

    radius = edge_wafer.radius()
    edge, centre = radius > 0.75, radius < 0.35
    assert (unbiased[edge].mean() - biased[edge].mean()) > 0.05
    assert (unbiased[centre].mean() - biased[centre].mean()) < 0.01


def test_biased_prior_is_worse_than_reality_at_the_edge(edge_wafer):
    prior = make_biased_prior(edge_wafer)
    radius = edge_wafer.radius()
    edge = radius > 0.75
    # Under-prediction, specifically: the prior misses failures that are there.
    assert edge_wafer.reality[edge].mean() - prior[edge].mean() > 0.05


def test_smoothing_removes_fine_structure(wafer):
    smooth = make_biased_prior(wafer, BiasParams(smoothing_sigma=3.0, radial_strength=0.0, gain=1.0, offset=0.0))
    assert smooth.std() < wafer.reality.std()


def test_stronger_radial_bias_misses_more_edge_failures(edge_wafer):
    """Scored where the bias is supposed to hurt: failing dies near the edge.

    Whole-wafer MAE is the wrong lens for this. Most dies pass, so suppressing
    the prior towards zero can *lower* MAE while making the prior blinder to
    exactly the failures it should be catching - which is the reason the
    benchmark scores a reconstruction rather than the prior alone.
    """
    wafer = edge_wafer
    edge_failures = (wafer.radius() > 0.75) & (wafer.reality == 1.0)
    assert edge_failures.any()

    mild = make_biased_prior(wafer, BiasParams(radial_strength=0.1))
    harsh = make_biased_prior(wafer, BiasParams(radial_strength=0.9))
    miss = lambda p: float(np.abs(p - wafer.reality)[edge_failures].mean())
    assert miss(harsh) > miss(mild)


def test_masked_blur_ignores_positions_outside_the_wafer():
    field = np.array([[1.0, 1.0, 0.0], [1.0, 1.0, 0.0]])
    mask = np.array([[True, True, False], [True, True, False]])
    out = gaussian_blur_masked(field, mask, sigma=1.5)

    # A constant field over the mask must stay constant: the empty column may
    # not drag the wafer edge towards zero.
    np.testing.assert_allclose(out[mask], 1.0, atol=1e-9)
    assert (out[~mask] == 0.0).all()


def test_zero_sigma_is_a_no_op(wafer):
    grid = wafer.to_grid(wafer.reality, fill=0.0)
    out = gaussian_blur_masked(grid, wafer.die_mask, sigma=0.0)
    np.testing.assert_array_equal(out[wafer.die_mask], wafer.reality)
