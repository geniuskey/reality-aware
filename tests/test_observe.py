"""The observation tool is the only channel to reality, and it holds the budget."""

import numpy as np
import pytest

from nano.tools.observe import AlreadyObserved, BudgetExhausted, ObservationTool


@pytest.fixture
def reality():
    return np.array([0.0, 1.0, 1.0, 0.0, 1.0])


def test_observe_spends_budget_and_returns_truth(reality):
    tool = ObservationTool(reality, budget=2)
    assert tool.budget_remaining == 2

    assert tool.observe(1) == 1.0
    assert tool.budget_remaining == 1
    assert tool.n_measurements == 1
    np.testing.assert_array_equal(tool.observed_indices, [1])
    np.testing.assert_array_equal(tool.observed_values, [1.0])


def test_budget_cannot_be_overspent(reality):
    tool = ObservationTool(reality, budget=1)
    tool.observe(0)
    with pytest.raises(BudgetExhausted):
        tool.observe(2)
    assert tool.n_measurements == 1


def test_a_die_cannot_be_measured_twice(reality):
    tool = ObservationTool(reality, budget=3)
    tool.observe(3)
    with pytest.raises(AlreadyObserved):
        tool.observe(3)
    assert tool.budget_remaining == 2  # the refused call costs nothing


def test_initial_observations_are_not_charged_to_the_budget(reality):
    mask = np.array([True, False, True, False, False])
    tool = ObservationTool(reality, budget=2, initial_mask=mask)

    assert tool.n_initial == 2
    assert tool.budget_remaining == 2
    assert tool.n_measurements == 2
    np.testing.assert_array_equal(tool.observed_values, [0.0, 1.0])


def test_observed_values_are_ordered_by_die_index(reality):
    tool = ObservationTool(reality, budget=3)
    for index in (4, 0, 2):
        tool.observe(index)
    np.testing.assert_array_equal(tool.observed_indices, [0, 2, 4])
    np.testing.assert_array_equal(tool.observed_values, [0.0, 1.0, 1.0])


def test_unobserved_reality_is_not_reachable_through_the_public_surface(reality):
    tool = ObservationTool(reality, budget=1)
    tool.observe(0)

    public = {
        name: getattr(tool, name)
        for name in dir(tool)
        if not name.startswith("_") and not callable(getattr(tool, name))
    }
    for value in public.values():
        array = np.asarray(value)
        if array.shape == reality.shape and array.dtype != bool:
            # Anything wafer-shaped and numeric must not be the full reality field.
            assert not np.array_equal(array, reality)

    # The values it does expose are exactly the ones that were paid for.
    np.testing.assert_array_equal(tool.observed_values, [0.0])


def test_the_tool_holds_a_copy_so_later_mutation_cannot_rewrite_history(reality):
    tool = ObservationTool(reality, budget=1)
    reality[1] = 99.0
    assert tool.observe(1) == 1.0
