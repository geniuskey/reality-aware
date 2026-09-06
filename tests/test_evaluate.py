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
    assert summary["experiment"]["acquisition_rule"] == "uncertainty x disagreement x novelty"


def test_a_reduced_rule_is_recorded_as_the_reduced_rule():
    """Run fewer terms and the file must say so — that is the whole point."""
    from nano.data import synthetic_wafers

    reduced = run_benchmark(
        synthetic_wafers(2, seed=1, grid=20),
        seeds=[0],
        initial_measurements=8,
        budget=8,
        terms=["uncertainty", "disagreement"],
    )
    assert reduced["experiment"]["acquisition_rule"] == "uncertainty x disagreement"


def test_ablation_arms_are_scored_against_the_full_rule():
    from nano.data import synthetic_wafers

    summary = run_benchmark(
        synthetic_wafers(2, seed=1, grid=20),
        seeds=[0, 1],
        initial_measurements=8,
        budget=10,
        ablation=True,
    )
    ablation = summary["ablation"]
    assert set(ablation) == {"nano_u", "nano_ud", "nano_un", "nano_dn"}

    # Ablations are not strategies: they do not appear in the main table.
    assert set(summary["strategies"]) == {"nano", "random", "grid"}

    primary = summary["metric"]["key"]
    for name, arm in ablation.items():
        assert arm["terms"] and set(arm["terms"]) <= {"uncertainty", "disagreement", "novelty"}
        assert len(arm["terms"]) < 3
        # Each one is paired against the full rule, interval and all.
        assert name in summary["comparisons"][primary]


def test_an_ablation_run_leaves_the_headline_arms_untouched():
    """Adding arms must not change what the three published arms did."""
    from nano.data import synthetic_wafers

    kwargs = dict(seeds=[0], initial_measurements=8, budget=8)
    plain = run_benchmark(synthetic_wafers(2, seed=1, grid=20), **kwargs)
    with_ablation = run_benchmark(synthetic_wafers(2, seed=1, grid=20), ablation=True, **kwargs)

    for name in ("nano", "random", "grid"):
        assert plain["strategies"][name]["metrics"] == with_ablation["strategies"][name]["metrics"]


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
        # The two measurement-free references are recorded per episode too, so a
        # pairing against them can be recomputed from the published file.
        assert set(episode["final"]) == {"nano", "random", "grid", "prior", "constant"}
        assert episode["prior_error"] > 0


def test_the_summary_round_trips_as_json(tmp_path, summary):
    from nano.evaluate import json_safe

    path = write_summary(summary, tmp_path / "benchmark_summary.json")
    assert json.loads(path.read_text()) == json_safe(summary)


def test_the_written_file_is_json_a_strict_parser_accepts(tmp_path, summary):
    """`NaN` is what Python writes and what JSON forbids.

    A metric can legitimately have no value — a percentage improvement over a
    baseline of exactly zero — and writing that as a bare NaN produces a file
    the site cannot parse and refuses to render.
    """
    path = write_summary(summary, tmp_path / "benchmark_summary.json")
    text = path.read_text()
    assert "NaN" not in text and "Infinity" not in text
    json.loads(text, parse_constant=_no_constants)

    # The undefined value survives as null rather than being invented.
    passing = summary["comparisons"]["mae_passing"]["constant"]
    assert passing["relative_mean"] != passing["relative_mean"]  # NaN in memory
    written = json.loads(text)["comparisons"]["mae_passing"]["constant"]
    assert written["relative_mean"] is None
    assert written["mean"] is not None  # the absolute difference is still defined


def _no_constants(name):
    raise AssertionError(f"results file contains the non-JSON constant {name}")


def test_correction_beats_the_uncorrected_prior(summary):
    """The weakest claim the benchmark has to support: measuring helped at all."""
    prior_error = summary["prior"]["initial_error"]["mean"]
    for strategy in summary["strategies"].values():
        assert strategy["final"]["mean"] < prior_error


def test_measurement_free_references_are_scored_alongside_the_strategies(summary):
    """A rule that cannot beat a predictor which reads nothing has earned nothing."""
    references = summary["references"]
    assert set(references) == {"prior", "constant"}
    for reference in references.values():
        assert reference["final"]["mean"] >= 0
        assert "mae" in reference["metrics"] and "balanced_mae" in reference["metrics"]

    # The constant predictor is the trap MAE alone walks into: strong on MAE,
    # and exactly 0.5 once the two classes are weighted equally.
    assert references["constant"]["metrics"]["balanced_mae"]["mean"] == pytest.approx(0.5)


def test_every_comparison_carries_an_interval_and_a_win_count(summary):
    comparisons = summary["comparisons"]
    assert "mae" in comparisons and "balanced_mae" in comparisons

    for metric, arms in comparisons.items():
        assert "nano" not in arms  # nothing is compared against itself
        for arm, result in arms.items():
            assert result["ci_low"] <= result["mean"] <= result["ci_high"]
            assert result["wins"] + result["losses"] + result["ties"] == result["n"]
            assert result["n"] == 2 * 2  # wafers x seeds
            assert isinstance(result["separates"], bool)
            assert "paired bootstrap" in result["method"]


def test_a_comparison_that_does_not_separate_is_marked_as_such(summary):
    """The site must be able to print "not separated" instead of a bare mean."""
    for arms in summary["comparisons"].values():
        for result in arms.values():
            spans_zero = result["ci_low"] < 0 < result["ci_high"]
            assert result["separates"] is not spans_zero


def test_secondary_metrics_are_reported_for_every_strategy(summary):
    primary = summary["metric"]["key"]
    for strategy in summary["strategies"].values():
        metrics = strategy["metrics"]
        assert {"mae", "balanced_mae", "mae_failing", "mae_passing", "rmse"} <= set(metrics)
        # `final` is the primary metric, whichever that is, so the site's table
        # and the comparisons it prints can never be on different scales.
        assert strategy["final"] == metrics[primary]

    # A binary target leads with the balanced metric: plain MAE on rare failures
    # is won by a predictor that reads nothing.
    assert primary == "balanced_mae"
    assert summary["metrics"]["mae"]["direction"] == "lower_is_better"


def test_the_primary_metric_can_be_overridden(summary):
    from nano.data import synthetic_wafers

    plain = run_benchmark(
        synthetic_wafers(2, seed=1, grid=20),
        seeds=[0, 1],
        initial_measurements=10,
        budget=12,
        primary_metric="mae",
    )
    assert plain["metric"]["key"] == "mae"
    assert plain["strategies"]["nano"]["final"] == plain["strategies"]["nano"]["metrics"]["mae"]
    # Same run, different lens: the underlying per-metric numbers are unchanged.
    assert plain["strategies"]["nano"]["metrics"] == summary["strategies"]["nano"]["metrics"]


def test_an_unknown_metric_is_refused():
    from nano.data import synthetic_wafers

    with pytest.raises(ValueError, match="unknown metric"):
        run_benchmark(
            synthetic_wafers(1, seed=0, grid=16),
            seeds=[0],
            initial_measurements=4,
            budget=4,
            primary_metric="accuracy",
        )


def test_calibration_is_measured_on_dies_the_agent_never_saw(summary):
    calibration = summary["calibration"]
    assert calibration["n_dies"] > 0
    assert "unmeasured" in calibration["scope"]

    bins = calibration["reliability"]
    assert len(bins) == 10
    assert sum(b["n"] for b in bins) == calibration["n_dies"]

    rho = calibration["rank_correlation"]
    assert -1.0 <= rho["pooled"] <= 1.0
    assert "not a coverage claim" in rho["note"]


def test_calibration_excludes_measured_dies():
    """A measured die has zero uncertainty and zero error by construction.

    Counting those would manufacture a correlation out of the tool's own
    bookkeeping rather than measuring the map.
    """
    from nano.data import synthetic_wafers

    wafers = synthetic_wafers(2, seed=1, grid=20)
    summary = run_benchmark(
        wafers, seeds=[0], initial_measurements=10, budget=12
    )
    measured = (10 + 12) * len(wafers)
    total_dies = sum(w.n_dies for w in wafers)
    assert summary["calibration"]["n_dies"] == total_dies - measured


def test_the_bias_parameters_are_recorded_and_shared(summary):
    bias = summary["experiment"]["prior_bias"]
    assert bias["radial_strength"] > 0
    assert bias["smoothing_sigma"] > 0
    assert "prior_weight" in summary["experiment"]["model"]


def test_an_empty_evaluation_set_is_refused():
    with pytest.raises(ValueError, match="no evaluation wafers"):
        run_benchmark([], seeds=[0], initial_measurements=1, budget=1)
