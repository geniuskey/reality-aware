import numpy as np
import pytest

from nano.data import FAIL, OUTSIDE, PASS, synthetic_wafers
from nano.prior import BiasParams, make_biased_prior


@pytest.fixture(scope="session")
def wafers():
    return synthetic_wafers(3, seed=7, grid=24)


@pytest.fixture(scope="session")
def wafer(wafers):
    return wafers[0]


@pytest.fixture(scope="session")
def edge_wafer(wafers):
    """A wafer whose failures live at the edge, where the radial bias bites."""
    return next(w for w in wafers if w.pattern == "Edge-Ring")


@pytest.fixture(scope="session")
def prior(wafer):
    return make_biased_prior(wafer, BiasParams())


@pytest.fixture
def rng():
    return np.random.default_rng(0)


@pytest.fixture
def fake_lswmd():
    """Write a pandas pickle shaped like ``LSWMD.pkl`` and return its path.

    It lives in conftest rather than in one test module because two modules
    need it, and importing across test modules only resolves when the repo root
    happens to be on ``sys.path`` — true under ``python -m pytest``, false under
    the bare ``pytest`` console script that CI runs.
    """

    def build(path, n_wafers=8, size=24):
        pd = pytest.importorskip("pandas")
        rng = np.random.default_rng(0)
        rows = []
        patterns = ["Center", "Edge-Ring", "Scratch", "none"]
        for i in range(n_wafers):
            yy, xx = np.mgrid[0:size, 0:size]
            centre = (size - 1) / 2
            inside = np.sqrt((yy - centre) ** 2 + (xx - centre) ** 2) <= centre
            wafer_map = np.where(rng.random((size, size)) < 0.2, FAIL, PASS)
            wafer_map = np.where(inside, wafer_map, OUTSIDE)
            rows.append(
                {
                    "waferMap": wafer_map,
                    # WM-811K nests its labels inside object arrays; the loader must cope.
                    "failureType": np.array([[patterns[i % len(patterns)]]], dtype=object),
                    "waferIndex": i,
                }
            )
        pd.DataFrame(rows).to_pickle(path)
        return path

    return build
