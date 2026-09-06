"""Wafer-map semantics and the subset index, per docs/data.md."""

import json

import numpy as np
import pytest

from nano.data import (
    FAIL,
    OUTSIDE,
    PASS,
    build_subset,
    load_subset,
    record_from_map,
    synthetic_wafers,
)


def test_wafer_map_value_semantics():
    wafer_map = np.array([[OUTSIDE, PASS, FAIL], [PASS, FAIL, OUTSIDE]])
    record = record_from_map(wafer_map, "w", "Loc")

    # 0 is masked out and never predicted; 1 -> 0.0 pass, 2 -> 1.0 fail.
    assert record.n_dies == 4
    assert record.die_mask.tolist() == [[False, True, True], [True, True, False]]
    assert record.reality.tolist() == [0.0, 1.0, 0.0, 1.0]


def test_wafers_are_not_resized():
    wafer_map = np.full((13, 21), PASS)
    record = record_from_map(wafer_map, "w", "Center")
    assert record.grid_shape == (13, 21)


def test_to_grid_round_trips_through_the_die_mask(wafer):
    grid = wafer.to_grid(wafer.reality)
    assert np.isnan(grid[~wafer.die_mask]).all()
    np.testing.assert_array_equal(grid[wafer.die_mask], wafer.reality)


def test_radius_is_normalised(wafer):
    radius = wafer.radius()
    assert radius.min() >= 0.0
    assert radius.max() <= 1.0


def test_synthetic_source_is_deterministic_and_labelled():
    a = synthetic_wafers(3, seed=3)
    b = synthetic_wafers(3, seed=3)
    for left, right in zip(a, b):
        np.testing.assert_array_equal(left.reality, right.reality)
        assert left.source == "synthetic"
    assert not np.array_equal(a[0].reality, synthetic_wafers(3, seed=4)[0].reality)


def test_subset_index_round_trips(tmp_path, fake_lswmd):
    raw = fake_lswmd(tmp_path / "LSWMD.pkl")
    index_path = tmp_path / "subset.json"

    doc = build_subset(raw, index_path, seed=0, n_wafers=4, min_dies=100)
    assert doc["dataset"] == "WM-811K"
    assert len(doc["wafers"]) == 4
    # Unlabelled wafers are dropped, so "none" must not survive the filter.
    assert all(entry["pattern"] != "none" for entry in doc["wafers"])

    saved = json.loads(index_path.read_text())
    assert saved == doc

    records = load_subset(index_path, raw)
    assert [r.wafer_id for r in records] == sorted(e["wafer_id"] for e in doc["wafers"])
    assert all(r.source == "WM-811K" for r in records)


def test_subset_rejects_small_grids(tmp_path, fake_lswmd):
    raw = fake_lswmd(tmp_path / "LSWMD.pkl", size=8)
    with pytest.raises(RuntimeError, match="passed the filters"):
        build_subset(raw, tmp_path / "subset.json", n_wafers=2, min_dies=400)


def test_missing_dataset_says_what_to_do(tmp_path):
    with pytest.raises(FileNotFoundError, match="--synthetic"):
        list(load_subset(tmp_path / "nope.json", tmp_path / "missing.pkl"))


def test_a_continuous_target_is_a_smooth_noisy_field():
    wafers = synthetic_wafers(3, seed=0, target="continuous")
    for wafer in wafers:
        assert wafer.target_kind == "continuous"
        assert wafer.source == "synthetic"
        assert 0.0 <= wafer.reality.min() and wafer.reality.max() <= 1.0
        # Not a label: the values must actually take intermediate levels.
        interior = (wafer.reality > 0.05) & (wafer.reality < 0.95)
        assert interior.mean() > 0.5
        assert len(np.unique(wafer.reality)) > 100


def test_binary_and_continuous_sources_are_told_apart():
    binary = synthetic_wafers(2, seed=0)[0]
    continuous = synthetic_wafers(2, seed=0, target="continuous")[0]

    assert set(np.unique(binary.reality)) <= {0.0, 1.0}
    assert binary.target_kind == "binary"
    assert continuous.wafer_id != binary.wafer_id  # ids say which source they came from


def test_a_continuous_target_is_deterministic():
    left = synthetic_wafers(2, seed=5, target="continuous")
    right = synthetic_wafers(2, seed=5, target="continuous")
    for a, b in zip(left, right):
        np.testing.assert_array_equal(a.reality, b.reality)


def test_an_unknown_target_is_refused():
    with pytest.raises(ValueError, match="unknown target"):
        synthetic_wafers(1, target="ternary")


def test_wm811k_cannot_serve_a_continuous_target(tmp_path):
    """Its labels are pass/fail; pretending otherwise would be the lie the
    limitations page warns about."""
    from nano.data import load_wafers

    with pytest.raises(ValueError, match="binary pass/fail"):
        load_wafers(
            synthetic=False,
            n_wafers=1,
            seed=0,
            subset_path=tmp_path / "subset.json",
            raw_path=tmp_path / "raw.pkl",
            target="continuous",
        )
