"""Scoring, aggregation, and the results file the documentation site reads."""

import json

import numpy as np
import pytest

from nano.data import synthetic_wafers
from nano.evaluate import SCHEMA_VERSION, mae, relative_improvement, run_benchmark, write_summary


@pytest.fixture(scope="module")
def summary():
    return run_benchmark(
        synthetic_wafers(2, seed=1, grid=20),
        seeds=[0, 1],
        initial_measurements=10,
        budget=12,
    )


def test_mae_is_the_mean_absolute_error():
    assert mae(np.array([0.0, 1.0]), np.array([0.0, 0.0])) == pytest.approx(0.5)
    with pytest.raises(ValueError):
        mae(np.zeros(3), np.zeros(4))


def test_relative_improvement_matches_the_published_formula():
    assert relative_improvement(0.20, 0.15) == pytest.approx(25.0)
    assert relative_improvement(0.10, 0.12) == pytest.approx(-20.0)


def test_summary_carries_every_field_the_site_requires(summary):
    """docs/benchmark.md: the build fails without these, so the run must emit them."""
    assert summary["schema_version"] == SCHEMA_VERSION
    assert set(summary["strategies"]) == {"nano", "random", "grid"}
    for strategy in summary["strategies"].values():
        assert {"label", "description", "final", "curve"} <= set(strategy)
        assert {"mean", "std"} <= set(strategy["final"])
        assert strategy["curve"] and {"measurements", "mean", "std"} <= set(strategy["curve"][0])

    assert summary["metric"]["direction"] == "lower_is_better"
    assert summary["prior"]["initial_error"]["mean"] > 0
    assert summary["experiment"]["seeds"] == [0, 1]
    assert summary["experiment"]["measurement_budget"] == 12
    assert summary["experiment"]["initial_measurements"] == 10
    assert summary["dataset"]["n_wafers"] == 2


def test_the_recorded_rule_is_the_rule_that_ran(summary):
    """A three-term product in the docs and a one-term rule in the code is the
    failure mode this project exists to argue against."""
    assert summary["experiment"]["acquisition_rule"] == (
        "uncertainty x simulation_disagreement x spatial_novelty"
    )


def test_the_curve_covers_the_whole_budget_and_starts_from_a_shared_state(summary):
    curves = {name: s["curve"] for name, s in summary["strategies"].items()}
    for curve in curves.values():
        assert [point["measurements"] for point in curve] == list(range(10, 10 + 12 + 1))

    # Identical initial mask, so every arm's first point must be identical.
    firsts = {name: curve[0]["mean"] for name, curve in curves.items()}
    assert len(set(firsts.values())) == 1


def test_every_episode_is_recorded_so_wins_and_losses_stay_visible(summary):
    episodes = summary["episodes"]
    assert len(episodes) == 2 * 2  # wafers x seeds
    for episode in episodes:
        assert set(episode["final"]) == {"nano", "random", "grid"}
        assert episode["prior_error"] > 0


def test_the_summary_round_trips_as_json(tmp_path, summary):
    path = write_summary(summary, tmp_path / "benchmark_summary.json")
    assert json.loads(path.read_text()) == json.loads(json.dumps(summary))


def test_correction_beats_the_uncorrected_prior(summary):
    """The weakest claim the benchmark has to support: measuring helped at all."""
    prior_error = summary["prior"]["initial_error"]["mean"]
    for strategy in summary["strategies"].values():
        assert strategy["final"]["mean"] < prior_error


def test_the_bias_parameters_are_recorded_and_shared(summary):
    bias = summary["experiment"]["prior_bias"]
    assert bias["radial_strength"] > 0
    assert bias["smoothing_sigma"] > 0
    assert "prior_weight" in summary["experiment"]["model"]


def test_an_empty_evaluation_set_is_refused():
    with pytest.raises(ValueError, match="no evaluation wafers"):
        run_benchmark([], seeds=[0], initial_measurements=1, budget=1)
