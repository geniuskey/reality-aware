"""The published playground has to stay honest about what it is showing.

It ships inside the docs site with real wafers embedded in it, so the two things
worth guarding are that it cannot quietly become a stand-in demo, and that the
page in ``docs/public`` is still the page ``playground/template.html`` describes.
"""

import json
from pathlib import Path

import pytest

from nano import playground

TEMPLATE = Path("playground/template.html")
PAGE = Path("docs/public/playground.html")
DATA_OPEN = '<script type="application/json" id="wafer-data">'


def small_summary(path: Path, **overrides) -> Path:
    """A results file shaped like a published one, but cheap to illustrate."""
    experiment = {
        "seeds": [0, 1],
        "initial_measurements": 6,
        "measurement_budget": 4,
        "episodes": 2,
        "target_kind": "binary",
        "model": {
            "kernel": "gaussian",
            "length_scale": "per-wafer default (wafer span / 12)",
            "prior_weight": 0.5,
        },
    }
    experiment.update(overrides)
    comparison = {
        "relative_mean": 8.7486,
        "relative_ci_low": 6.5549,
        "relative_ci_high": 11.1144,
        "separates": True,
    }
    summary = {
        "git_commit": "abc1234",
        "generated_at": "2026-01-01T00:00:00Z",
        "experiment": experiment,
        "metric": {"name": "Balanced MAE", "key": "balanced_mae"},
        "comparisons": {
            "balanced_mae": {"random": comparison, "grid": dict(comparison, relative_mean=6.3)},
            "mae": {"random": dict(comparison, separates=False), "grid": dict(comparison, separates=False)},
        },
    }
    path.write_text(json.dumps(summary), encoding="utf-8")
    return path


def build_args(tmp_path, *extra):
    summary = small_summary(tmp_path / "summary.json")
    return [
        "--synthetic", "--wafers", "2", "--seeds", "0",
        "--summary", str(summary),
        "--out", str(tmp_path / "page.html"),
        "--reference", str(tmp_path / "reference.json"),
        *extra,
    ]


def test_it_refuses_to_publish_stand_in_wafers_as_the_dataset(tmp_path, capsys):
    """The page tells the reader it is showing WM-811K. It must not be lying."""
    with pytest.raises(SystemExit) as exit_info:
        playground.main(build_args(tmp_path))
    assert "refusing" in str(exit_info.value)
    assert "not WM-811K" in capsys.readouterr().out
    assert not (tmp_path / "page.html").exists()


def test_an_acknowledged_stand_in_build_produces_a_page_and_its_traces(tmp_path):
    assert playground.main(build_args(tmp_path, "--allow-stand-in")) == 0

    page = (tmp_path / "page.html").read_text(encoding="utf-8")
    assert playground.PLACEHOLDER not in page

    payload = page.split(DATA_OPEN, 1)[1].split("</script>", 1)[0]
    doc = json.loads(payload)
    assert doc["meta"]["wafers"] == len(doc["wafers"]) == 2
    assert doc["meta"]["parity"] is None, "parity is stamped by the node check, never by Python"
    assert doc["loop"]["budget"] == 4

    reference = json.loads((tmp_path / "reference.json").read_text(encoding="utf-8"))
    # One trace per non-empty subset of the three terms, per wafer, per seed.
    assert len(reference) == 2 * 1 * 7
    for key, selections in reference.items():
        wafer_id, seed, rule = key.split("|")
        assert seed == "0"
        assert len(selections) == doc["loop"]["budget"]
        assert set(rule.split("+")) <= {"uncertainty", "disagreement", "novelty"}


def test_it_refuses_a_run_the_browser_engine_does_not_implement(tmp_path):
    """A summary the port cannot reproduce would make the page an illustration of nothing."""
    for override in (
        {"model": {"kernel": "gaussian", "length_scale": "per-wafer default (wafer span / 12)", "prior_weight": 0.25}},
        {"target_kind": "continuous"},
    ):
        summary = json.loads(small_summary(tmp_path / "s.json", **override).read_text())
        with pytest.raises(SystemExit):
            playground.check_ported(summary)


def test_the_headline_is_quoted_from_the_results_file(tmp_path):
    summary = json.loads(small_summary(tmp_path / "s.json").read_text())
    headline = playground.headline(summary)
    assert headline["random"] == {"mean": 8.7, "lo": 6.6, "hi": 11.1}
    assert headline["metric"] == "Balanced MAE"
    assert headline["episodes"] == 2
    # Neither baseline separates on plain MAE here, and the page must say so.
    assert headline["maeSeparated"] == []


@pytest.mark.skipif(not PAGE.exists(), reason="the page has not been built")
def test_the_published_page_is_the_current_template():
    """Everything but the wafer payload must still be byte-for-byte the template.

    Editing ``playground/template.html`` without re-running the exporter would
    leave the site serving an older page while the repository shows the newer
    source. This is the cheap half of that check; the parity script is the other.
    """
    page = PAGE.read_text(encoding="utf-8")
    head, rest = page.split(DATA_OPEN, 1)
    _, tail = rest.split("</script>", 1)
    rebuilt = f"{head}{DATA_OPEN}{playground.PLACEHOLDER}</script>{tail}"
    assert rebuilt == TEMPLATE.read_text(encoding="utf-8"), (
        "docs/public/playground.html is stale — run `npm run build:playground`"
    )
