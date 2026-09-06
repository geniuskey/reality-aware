"""The commands the documentation tells people to run must actually run."""

import json

import pytest

from nano import benchmark, demo, subset
from tests.test_data import _write_fake_lswmd


def test_benchmark_writes_a_results_file(tmp_path, capsys):
    out = tmp_path / "benchmark_summary.json"
    code = benchmark.main(
        [
            "--synthetic", "--wafers", "2", "--seeds", "0",
            "--initial", "8", "--budget", "6", "--out", str(out), "--no-figures",
        ]
    )
    assert code == 0

    summary = json.loads(out.read_text())
    assert summary["dataset"]["name"] == "synthetic-wafers"
    assert set(summary["strategies"]) == {"nano", "random", "grid"}

    printed = capsys.readouterr().out
    # A run on the stand-in must say so, loudly, every time.
    assert "not WM-811K" in printed
    assert "NANO" in printed


def test_demo_prints_a_decision_trace(capsys):
    code = demo.main(
        [
            "--synthetic", "--wafers", "1", "--wafer", "0", "--seed", "0",
            "--initial", "8", "--budget", "5", "--no-figures",
        ]
    )
    assert code == 0

    printed = capsys.readouterr().out
    assert "decision trace" in printed
    # Every selection is explained by the terms that produced it.
    assert "uncertainty=" in printed and "disagreement=" in printed and "novelty=" in printed


def test_demo_rejects_a_wafer_index_it_does_not_have():
    with pytest.raises(SystemExit):
        demo.main(["--synthetic", "--wafers", "2", "--wafer", "9", "--no-figures"])


def test_subset_builder_writes_a_committable_index(tmp_path, capsys):
    raw = tmp_path / "LSWMD.pkl"
    _write_fake_lswmd(raw)
    out = tmp_path / "subset.json"

    assert subset.main(["--raw", str(raw), "--out", str(out), "--wafers", "3", "--min-dies", "100"]) == 0
    doc = json.loads(out.read_text())
    assert doc["dataset"] == "WM-811K"
    assert len(doc["wafers"]) == 3
    assert "do not commit the dataset" in capsys.readouterr().out


@pytest.mark.parametrize("module", [benchmark, demo, subset])
def test_help_is_available_without_the_dataset(module, capsys):
    with pytest.raises(SystemExit) as exit_info:
        module.build_parser().parse_args(["--help"])
    assert exit_info.value.code == 0
    assert "usage" in capsys.readouterr().out
