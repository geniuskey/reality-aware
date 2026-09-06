"""NANO — a reality-aware active metrology agent.

The package is organised around one boundary: reality reaches the agent only
through :mod:`nano.tools.observe`, which accounts for the measurement budget.
:mod:`nano.evaluate` is the only module that reads full ground-truth fields, and
it never returns anything to the agent.
"""

from nano.agent import EpisodeResult, run_episode
from nano.baselines import GridPolicy, RandomPolicy
from nano.data import WaferRecord, load_subset, synthetic_wafers
from nano.model import RealityEstimate, RealityModel
from nano.policy import AcquisitionPolicy, Decision
from nano.prior import BiasParams, make_biased_prior
from nano.tools.observe import BudgetExhausted, ObservationTool

__all__ = [
    "AcquisitionPolicy",
    "BiasParams",
    "BudgetExhausted",
    "Decision",
    "EpisodeResult",
    "GridPolicy",
    "ObservationTool",
    "RandomPolicy",
    "RealityEstimate",
    "RealityModel",
    "WaferRecord",
    "load_subset",
    "make_biased_prior",
    "run_episode",
    "synthetic_wafers",
]

__version__ = "0.1.0"
