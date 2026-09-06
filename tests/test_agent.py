"""The loop: budget discipline, determinism, and the boundary around ground truth."""

import numpy as np
import pytest

from nano.agent import draw_initial_mask, run_episode
from nano.baselines import GridPolicy, RandomPolicy, build_policies
from nano.data import WaferRecord
from nano.policy import AcquisitionPolicy


def episode(wafer, prior, policy, seed=0, budget=15, initial=8):
    return run_episode(
        wafer,
        prior,
        policy,
        initial_mask=draw_initial_mask(wafer, initial, seed),
        budget=budget,
        seed=seed,
    )


def test_the_budget_is_spent_exactly_once_each(wafer, prior):
    result = episode(wafer, prior, AcquisitionPolicy(), budget=15, initial=8)

    assert len(result.selections) == 15
    assert len(set(result.selections)) == 15  # never the same die twice
    assert int(result.observed_mask.sum()) == 8 + 15
    assert result.n_initial == 8


def test_every_arm_starts_from_the_same_initial_observations(wafer, prior):
    masks = [
        episode(wafer, prior, policy).steps[0]
        for policy in build_policies(15, wafer.coords).values()
    ]
    for step in masks[1:]:
        np.testing.assert_array_equal(step.prediction, masks[0].prediction)
        assert step.measurements == masks[0].measurements


def test_the_initial_mask_is_centre_biased(wafer):
    """The starting evidence reproduces the sampling bias, it does not correct it."""
    radii = [
        wafer.radius()[draw_initial_mask(wafer, 30, seed)].mean() for seed in range(12)
    ]
    assert np.mean(radii) < wafer.radius().mean()


def test_the_same_seed_reproduces_the_same_run(wafer, prior):
    for policy_factory in (AcquisitionPolicy, RandomPolicy, lambda: GridPolicy(15, wafer.coords)):
        left = episode(wafer, prior, policy_factory(), seed=3)
        right = episode(wafer, prior, policy_factory(), seed=3)
        assert left.selections == right.selections
        np.testing.assert_array_equal(left.prediction, right.prediction)


def test_different_seeds_give_different_runs(wafer, prior):
    left = episode(wafer, prior, RandomPolicy(), seed=0)
    right = episode(wafer, prior, RandomPolicy(), seed=1)
    assert left.selections != right.selections


def test_measured_values_are_ground_truth_at_the_measured_dies(wafer, prior):
    result = episode(wafer, prior, AcquisitionPolicy())
    for step in result.steps:
        if step.selected_index is not None:
            assert step.measured_value == wafer.reality[step.selected_index]


def test_hidden_reality_cannot_influence_the_agent(wafer, prior):
    """The leakage test.

    Run an episode, then flip ground truth at every die the agent never
    measured and run it again. Nothing the agent was allowed to see has changed,
    so if the trajectory changes, something is reading reality behind the tool.
    """
    first = episode(wafer, prior, AcquisitionPolicy(), seed=5)
    seen = first.observed_mask

    tampered_reality = wafer.reality.copy()
    tampered_reality[~seen] = 1.0 - tampered_reality[~seen]
    tampered = WaferRecord(
        wafer_id=wafer.wafer_id,
        pattern=wafer.pattern,
        grid_shape=wafer.grid_shape,
        die_mask=wafer.die_mask,
        reality=tampered_reality,
        coords=wafer.coords,
        source=wafer.source,
    )

    second = episode(tampered, prior, AcquisitionPolicy(), seed=5)
    assert first.selections == second.selections
    np.testing.assert_array_equal(first.prediction, second.prediction)


def test_the_loop_stops_when_the_wafer_runs_out_of_dies(wafer, prior):
    result = episode(wafer, prior, RandomPolicy(), budget=wafer.n_dies + 50, initial=4)
    assert int(result.observed_mask.sum()) == wafer.n_dies


def test_predictions_are_recorded_for_every_measurement_count(wafer, prior):
    result = episode(wafer, prior, AcquisitionPolicy(), budget=12, initial=6)
    counts = [step.measurements for step in result.steps]
    assert counts == list(range(6, 6 + 12 + 1))


def test_mask_and_values_at_step_reconstruct_the_agent_view(wafer, prior):
    result = episode(wafer, prior, AcquisitionPolicy(), budget=10, initial=5)
    for index, step in enumerate(result.steps):
        mask = result.mask_at_step(index)
        assert int(mask.sum()) == step.measurements
        np.testing.assert_allclose(result.values_at_step(index), wafer.reality[mask])


def test_a_budget_of_zero_still_produces_an_estimate(wafer, prior):
    result = episode(wafer, prior, AcquisitionPolicy(), budget=0, initial=5)
    assert result.selections == []
    assert len(result.steps) == 1
    assert result.prediction.shape == (wafer.n_dies,)
