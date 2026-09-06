"""Metrics that a trivial predictor cannot game, and intervals that can say "no"."""

import numpy as np
import pytest

from nano.metrics import metric_set, paired_bootstrap


def test_mae_is_dominated_by_the_majority_class():
    """The finding that motivated this module.

    Nine dies pass, one fails. Answering "nothing fails" everywhere scores an
    excellent MAE while knowing nothing at all — so MAE alone cannot be the
    only number a benchmark reports on an imbalanced binary target.
    """
    reality = np.array([0.0] * 9 + [1.0])
    silent = np.zeros(10)

    scores = metric_set(silent, reality)
    assert scores["mae"] == pytest.approx(0.1)  # looks good
    assert scores["balanced_mae"] == pytest.approx(0.5)  # is not
    assert scores["mae_failing"] == pytest.approx(1.0)


def test_balanced_mae_is_the_mean_of_the_two_class_errors():
    reality = np.array([0.0, 0.0, 1.0])
    prediction = np.array([0.2, 0.4, 0.5])
    scores = metric_set(prediction, reality)

    assert scores["mae_passing"] == pytest.approx(0.3)
    assert scores["mae_failing"] == pytest.approx(0.5)
    assert scores["balanced_mae"] == pytest.approx(0.4)


def test_a_continuous_target_gets_no_class_metrics():
    reality = np.array([0.12, 0.55, 0.81])
    scores = metric_set(reality + 0.05, reality, target_kind="continuous")
    assert set(scores) == {"mae", "rmse"}


def test_a_real_difference_separates_from_zero():
    baseline = [0.20, 0.22, 0.19, 0.24, 0.21, 0.23]
    candidate = [0.15, 0.16, 0.14, 0.18, 0.16, 0.17]
    result = paired_bootstrap(baseline, candidate, seed=0)

    assert result.separates
    assert result.ci_low > 0
    assert result.wins == 6
    assert result.mean == pytest.approx(np.mean(baseline) - np.mean(candidate))


def test_a_difference_the_evidence_cannot_support_does_not_separate():
    """A mean improvement with an interval spanning zero must report that."""
    rng = np.random.default_rng(0)
    baseline = rng.normal(0.20, 0.05, 24)
    candidate = baseline - rng.normal(0.001, 0.05, 24)
    result = paired_bootstrap(baseline, candidate, seed=0)

    assert result.mean != 0
    assert result.ci_low < 0 < result.ci_high
    assert not result.separates


def test_the_bootstrap_is_reproducible_from_its_seed():
    baseline = [0.2, 0.3, 0.25, 0.28, 0.21]
    candidate = [0.15, 0.29, 0.2, 0.3, 0.19]
    first = paired_bootstrap(baseline, candidate, seed=7)
    second = paired_bootstrap(baseline, candidate, seed=7)
    third = paired_bootstrap(baseline, candidate, seed=8)

    assert first.as_dict() == second.as_dict()
    assert (first.ci_low, first.ci_high) != (third.ci_low, third.ci_high)


def test_wins_losses_and_ties_account_for_every_episode():
    result = paired_bootstrap([0.2, 0.1, 0.3], [0.1, 0.2, 0.3], seed=0)
    assert (result.wins, result.losses, result.ties) == (1, 1, 1)
    assert result.wins + result.losses + result.ties == result.n


def test_a_zero_baseline_has_no_relative_scale():
    """No percentage improvement over "no error at all" — it must not be invented."""
    result = paired_bootstrap([0.0, 0.0, 0.0], [0.1, 0.2, 0.1], seed=0)
    assert np.isnan(result.relative_mean)
    assert np.isnan(result.relative_ci_low)
    assert result.ci_high < 0  # and the arm is genuinely worse


def test_mismatched_arms_are_refused():
    with pytest.raises(ValueError, match="one value per episode"):
        paired_bootstrap([0.1, 0.2], [0.1], seed=0)
    with pytest.raises(ValueError, match="at least one episode"):
        paired_bootstrap([], [], seed=0)
