import numpy as np
import pytest

from nano.data import synthetic_wafers
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
