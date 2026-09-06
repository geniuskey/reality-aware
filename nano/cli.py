"""Shared command-line plumbing for the benchmark, the demo and the plot scripts."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from nano.agent import EpisodeResult, draw_initial_mask, run_episode
from nano.data import DEFAULT_RAW_PATH, DEFAULT_SUBSET_PATH, WaferRecord, load_wafers
from nano.model import RealityModel
from nano.policy import TERMS, AcquisitionPolicy
from nano.prior import BiasParams, make_biased_prior

RESULTS_DIR = Path("results")


def add_source_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Where the wafers come from. Identical across every entry point."""
    group = parser.add_argument_group("wafer source")
    group.add_argument(
        "--raw",
        type=Path,
        default=DEFAULT_RAW_PATH,
        help="local WM-811K distribution (LSWMD.pkl), never committed",
    )
    group.add_argument(
        "--subset",
        type=Path,
        default=DEFAULT_SUBSET_PATH,
        help="versioned subset index naming the evaluation wafers",
    )
    group.add_argument(
        "--synthetic",
        action="store_true",
        help=(
            "use generated stand-in wafers instead of WM-811K. Results are labelled "
            "synthetic-wafers and must not be published as dataset results"
        ),
    )
    group.add_argument("--wafers", type=int, default=12, help="number of evaluation wafers")
    group.add_argument(
        "--subset-seed", type=int, default=0, help="seed for the wafer source, not for an episode"
    )
    return parser


def add_experiment_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    group = parser.add_argument_group("experiment")
    group.add_argument("--initial", type=int, default=20, help="initial centre-biased measurements")
    group.add_argument("--budget", type=int, default=60, help="additional measurement budget")
    group.add_argument(
        "--length-scale",
        type=float,
        default=None,
        help="model kernel length scale in die units (default: per-wafer, from wafer span)",
    )
    group.add_argument(
        "--terms",
        nargs="+",
        default=None,
        choices=["uncertainty", "disagreement", "novelty"],
        help=(
            "which terms the NANO acquisition product multiplies "
            "(default: all three, the documented rule)"
        ),
    )
    group.add_argument(
        "--metric",
        default=None,
        help=(
            "primary metric for the table, the curve and every comparison "
            "(default: balanced_mae on a binary target, mae on a continuous one). "
            "Every metric is reported either way"
        ),
    )
    group.add_argument(
        "--prior-weight",
        type=float,
        default=0.5,
        help="how many measurements' worth of evidence the prior is treated as carrying",
    )
    return parser


def resolve_wafers(args: argparse.Namespace) -> tuple[list[WaferRecord], dict]:
    """Load the evaluation wafers plus the dataset block written into the results file."""
    return load_wafers(
        synthetic=args.synthetic,
        n_wafers=args.wafers,
        seed=args.subset_seed,
        subset_path=args.subset,
        raw_path=args.raw,
    )


@dataclass
class EpisodeBundle:
    """Everything a plot script needs to draw one episode it just re-ran."""

    record: WaferRecord
    prior: np.ndarray
    model: RealityModel
    episode: EpisodeResult
    dataset: dict


def single_episode(
    args: argparse.Namespace,
    *,
    wafer_index: int = 0,
    seed: int = 0,
    policy=None,
    bias: BiasParams | None = None,
) -> EpisodeBundle:
    """Re-run one episode exactly as the benchmark ran it.

    Same wafer, same prior, same initial mask, same seed — so a figure drawn
    from this shows what was scored, not a fresh unrelated run.
    """
    records, dataset = resolve_wafers(args)
    if not 0 <= wafer_index < len(records):
        raise SystemExit(f"wafer index {wafer_index} is out of range for {len(records)} wafers")
    record = records[wafer_index]
    prior = make_biased_prior(record, bias or BiasParams())
    model = RealityModel(
        record.coords,
        prior,
        length_scale=getattr(args, "length_scale", None),
        prior_weight=getattr(args, "prior_weight", 0.5),
    )
    episode = run_episode(
        record,
        prior,
        policy or AcquisitionPolicy(getattr(args, "terms", None) or TERMS),
        initial_mask=draw_initial_mask(record, args.initial, seed),
        budget=args.budget,
        seed=seed,
        model=model,
    )
    return EpisodeBundle(record=record, prior=prior, model=model, episode=episode, dataset=dataset)


def source_warning(dataset_block: dict) -> str | None:
    """A line printed whenever the run did not use the real dataset."""
    if dataset_block.get("name") == "WM-811K":
        return None
    return (
        "NOTE: this run used generated stand-in wafers, not WM-811K. The results file "
        "records dataset.name = "
        f"{dataset_block.get('name')!r}. Do not publish these numbers as dataset results."
    )
