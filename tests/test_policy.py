"""The selection rule the documentation states must be the rule the code runs."""

import numpy as np
import pytest

from nano.baselines import GridPolicy, RandomPolicy
from nano.model import RealityModel
from nano.policy import AcquisitionPolicy, argmax_with_tiebreak


@pytest.fixture
def state(wafer, prior):
    model = RealityModel(wafer.coords, prior)
    mask = np.zeros(wafer.n_dies, dtype=bool)
    mask[[4, 77, 150]] = True
    estimate = model.estimate(mask, wafer.reality[mask])
    return estimate, mask


def test_acquisition_is_the_product_of_its_three_terms(wafer, state):
    estimate, mask = state
    policy = AcquisitionPolicy()
    terms = policy.score_terms(estimate, mask, wafer.coords)

    expected = terms["uncertainty"] * terms["disagreement"] * terms["novelty"]
    np.testing.assert_allclose(terms["acquisition"][~mask], expected[~mask])


def test_the_selected_die_is_the_argmax_over_unmeasured_dies(wafer, state, rng):
    estimate, mask = state
    policy = AcquisitionPolicy()
    terms = policy.score_terms(estimate, mask, wafer.coords)
    decision = policy.select(estimate, mask, wafer.coords, rng)

    assert not mask[decision.index]
    assert decision.score == pytest.approx(terms["acquisition"][~mask].max())
    # The trace must reproduce the score it claims to explain.
    product = (
        decision.terms["uncertainty"]
        * decision.terms["disagreement"]
        * decision.terms["novelty"]
    )
    assert product == pytest.approx(decision.score)


def test_a_measured_die_is_never_selected(wafer, prior, rng):
    model = RealityModel(wafer.coords, prior)
    policy = AcquisitionPolicy()
    mask = np.zeros(wafer.n_dies, dtype=bool)
    mask[: wafer.n_dies - 3] = True  # only three candidates left
    estimate = model.estimate(mask, wafer.reality[mask])

    for _ in range(3):
        decision = policy.select(estimate, mask, wafer.coords, rng)
        assert not mask[decision.index]
        mask[decision.index] = True


def test_no_term_can_veto_a_candidate_outright(wafer, state):
    """Each term is floored, because a zero factor would zero the whole product."""
    estimate, mask = state
    terms = AcquisitionPolicy().score_terms(estimate, mask, wafer.coords)
    for name in ("uncertainty", "disagreement", "novelty"):
        assert terms[name][~mask].min() > 0.0


def test_novelty_prefers_the_die_furthest_from_what_was_measured(wafer, state):
    estimate, mask = state
    terms = AcquisitionPolicy().score_terms(estimate, mask, wafer.coords)
    measured = wafer.coords[mask]
    distance = np.array(
        [np.linalg.norm(measured - c, axis=1).min() for c in wafer.coords]
    )
    assert terms["novelty"][int(np.argmax(distance))] == pytest.approx(1.0)


def test_ties_are_broken_by_the_seeded_generator():
    scores = np.array([1.0, 1.0, 1.0, 0.0])
    picks = {argmax_with_tiebreak(scores, np.random.default_rng(seed)) for seed in range(20)}
    assert picks <= {0, 1, 2}
    assert len(picks) > 1  # a tie is resolved by the seed, not by array order
    assert argmax_with_tiebreak(scores, np.random.default_rng(3)) == argmax_with_tiebreak(
        scores, np.random.default_rng(3)
    )


def test_every_arm_implements_the_same_interface(wafer, state):
    estimate, mask = state
    policies = [AcquisitionPolicy(), RandomPolicy(), GridPolicy(10, wafer.coords)]
    for policy in policies:
        decision = policy.select(estimate, mask, wafer.coords, np.random.default_rng(0))
        assert not mask[decision.index]
        assert isinstance(decision.score, float)
        assert decision.n_candidates == int((~mask).sum())


def test_grid_spreads_its_measurements_more_evenly_than_random(wafer, state):
    """Grid is the baseline it claims to be: even coverage, not chance."""
    estimate, mask = state

    def spread(policy, seed):
        working = mask.copy()
        chosen = []
        rng = np.random.default_rng(seed)
        for _ in range(16):
            index = policy.select(estimate, working, wafer.coords, rng).index
            working[index] = True
            chosen.append(index)
        points = wafer.coords[chosen]
        pairwise = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2)
        np.fill_diagonal(pairwise, np.inf)
        return float(pairwise.min(axis=1).mean())

    grid = spread(GridPolicy(16, wafer.coords), 0)
    random = np.mean([spread(RandomPolicy(), seed) for seed in range(5)])
    assert grid > random
