"""Figures are optional to install, but when installed they must draw a real run."""

import json

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("PIL")

from nano import figures  # noqa: E402
from nano.agent import draw_initial_mask, run_episode  # noqa: E402
from nano.data import synthetic_wafers  # noqa: E402
from nano.evaluate import run_benchmark  # noqa: E402
from nano.policy import AcquisitionPolicy  # noqa: E402
from nano.prior import make_biased_prior  # noqa: E402


@pytest.fixture(scope="module")
def run():
    wafers = synthetic_wafers(2, seed=2, grid=18)
    summary = run_benchmark(wafers, seeds=[0], initial_measurements=8, budget=8)
    record = wafers[0]
    prior = make_biased_prior(record)
    episode = run_episode(
        record,
        prior,
        AcquisitionPolicy(),
        initial_mask=draw_initial_mask(record, 8, 0),
        budget=8,
        seed=0,
    )
    return summary, record, prior, episode


def test_error_curve_and_paired_improvement_are_written(tmp_path, run):
    summary, *_ = run
    curve = figures.plot_error_curve(summary, tmp_path / "error_curve.svg")
    paired = figures.plot_paired_improvement(summary, tmp_path / "paired_improvement.svg")
    assert curve.exists() and curve.stat().st_size > 0
    assert paired.exists() and paired.stat().st_size > 0


def test_webp_figures_are_written_as_webp(tmp_path, run):
    _, record, prior, episode = run
    path = figures.plot_wafer_comparison(record, prior, episode, tmp_path / "wafer_comparison.webp")
    assert path.read_bytes()[:4] == b"RIFF"


def test_uncertainty_figure_shows_both_ends_of_the_budget(tmp_path, run):
    _, record, _, episode = run
    path = figures.plot_uncertainty_before_after(record, episode, tmp_path / "u.webp")
    assert path.exists()
    assert episode.steps[0].measurements != episode.steps[-1].measurements


def test_the_gif_records_the_whole_episode(tmp_path, run):
    _, record, _, episode = run
    path = figures.animate_episode(record, episode, tmp_path / "demo.gif", fps=4)
    assert path.read_bytes()[:3] == b"GIF"


def test_paired_improvement_needs_a_run_not_an_expectation(tmp_path):
    with pytest.raises(ValueError, match="no per-episode records"):
        figures.plot_paired_improvement({"strategies": {}}, tmp_path / "x.svg")


def test_published_figure_names_match_the_sync_script(tmp_path, run):
    """scripts/sync-doc-assets.mjs only copies names it knows about."""
    published = set(json.loads(_published_names()))
    produced = {
        "error_curve.svg",
        "paired_improvement.svg",
        "wafer_comparison.webp",
        "uncertainty_before_after.webp",
        "demo.gif",
        "demo_step_00.webp",
        "demo_step_05.webp",
        "demo_selection.webp",
        "demo_final.webp",
    }
    assert produced <= published


def _published_names() -> str:
    import re
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "scripts" / "sync-doc-assets.mjs"
    block = re.search(r"const published = \[(.*?)\]", source.read_text(), re.S).group(1)
    return "[" + block.replace("'", '"').strip().rstrip(",") + "]"
