"""``python -m nano.playground`` — build the browser playground from the real wafers.

The page at ``docs/public/playground.html`` re-runs the loop client-side, which
means it has to carry the wafers with it: the die coordinates, the biased prior
and the hidden reality for every evaluation wafer. Nothing there is hand-typed.
The measurement configuration and the headline margins printed in the page's
footnotes are read from ``results/benchmark_summary.json``, so the page cannot
drift away from the run it claims to illustrate; if that run used settings the
JavaScript port does not implement, this refuses to build.

It also writes ``playground/reference.json`` — the exact selections Python made
for every rule the page exposes. ``scripts/check-playground-parity.mjs`` replays
those through the engine embedded in the built page and stamps the result into
it, so the "traces match Python" claim the page prints is a checked one.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np

from nano.agent import draw_initial_mask, run_episode
from nano.baselines import GridPolicy, RandomPolicy
from nano.cli import RESULTS_DIR, add_source_args, resolve_wafers, source_warning, use_utf8_output
from nano.model import RealityModel, default_length_scale
from nano.policy import TERMS, AcquisitionPolicy
from nano.prior import BiasParams, make_biased_prior

TEMPLATE = Path("playground/template.html")
PAGE_OUT = Path("docs/public/playground.html")
REFERENCE_OUT = Path("playground/reference.json")
PLACEHOLDER = "__WAFER_DATA__"

# What the embedded JavaScript implements. A summary produced with anything else
# describes a different loop than the one the page runs.
PORTED_PRIOR_WEIGHT = 0.5
PORTED_KERNEL = "gaussian"
PORTED_LENGTH_SCALE = "per-wafer default (wafer span / 12)"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m nano.playground",
        description="Build the interactive playground page from the evaluation wafers.",
    )
    add_source_args(parser)
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[0, 1, 2],
        help="episode seeds offered on the page (a subset of the benchmark's seeds)",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=RESULTS_DIR / "benchmark_summary.json",
        help="published results file the page quotes and takes its configuration from",
    )
    parser.add_argument("--template", type=Path, default=TEMPLATE, help="page source")
    parser.add_argument("--out", type=Path, default=PAGE_OUT, help="built page")
    parser.add_argument(
        "--reference", type=Path, default=REFERENCE_OUT, help="Python traces for the parity check"
    )
    parser.add_argument(
        "--allow-stand-in",
        action="store_true",
        help=(
            "build the page from generated stand-in wafers. The page presents itself as "
            "real WM-811K data, so this is refused by default"
        ),
    )
    return parser


def headline(summary: dict) -> dict:
    """The published margins, quoted from the results file rather than retyped."""
    metric = summary["metric"]
    primary = summary["comparisons"][metric["key"]]

    def margin(arm: str) -> dict:
        block = primary[arm]
        return {
            "mean": round(block["relative_mean"], 1),
            "lo": round(block["relative_ci_low"], 1),
            "hi": round(block["relative_ci_high"], 1),
        }

    mae = summary["comparisons"].get("mae", {})
    separated = [
        label
        for arm, label in (("random", "Random"), ("grid", "Grid"))
        if mae.get(arm, {}).get("separates")
    ]
    return {
        "metric": metric["name"],
        "seeds": len(summary["experiment"]["seeds"]),
        "episodes": summary["experiment"]["episodes"],
        "random": margin("random"),
        "grid": margin("grid"),
        "maeSeparated": separated,
    }


def check_ported(summary: dict) -> None:
    """Refuse to illustrate a run the browser engine would not reproduce."""
    experiment = summary["experiment"]
    model = experiment["model"]
    problems = []
    if model.get("prior_weight") != PORTED_PRIOR_WEIGHT:
        problems.append(
            f"prior_weight {model.get('prior_weight')} (page implements {PORTED_PRIOR_WEIGHT})"
        )
    if model.get("kernel") != PORTED_KERNEL:
        problems.append(f"kernel {model.get('kernel')!r} (page implements {PORTED_KERNEL!r})")
    if model.get("length_scale") != PORTED_LENGTH_SCALE:
        problems.append(f"length_scale {model.get('length_scale')!r} (page implements the default)")
    if experiment.get("target_kind") != "binary":
        problems.append(f"target {experiment.get('target_kind')!r} (page implements binary)")
    if problems:
        raise SystemExit(
            "the published run uses settings the browser port does not implement:\n  "
            + "\n  ".join(problems)
        )


def build(args: argparse.Namespace) -> tuple[str, dict]:
    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    check_ported(summary)
    initial = summary["experiment"]["initial_measurements"]
    budget = summary["experiment"]["measurement_budget"]

    records, dataset = resolve_wafers(args)
    warning = source_warning(dataset)
    if warning:
        print(warning)
        if not args.allow_stand_in:
            raise SystemExit(
                "refusing to build the page from anything but WM-811K; pass --allow-stand-in "
                "to override, and do not publish the result"
            )

    bias = BiasParams()
    subsets = [c for r in range(1, len(TERMS) + 1) for c in itertools.combinations(TERMS, r)]
    wafers: list[dict] = []
    reference: dict[str, list[int]] = {}
    total_dies = 0

    for record in records:
        prior = make_biased_prior(record, bias)
        total_dies += int(record.n_dies)
        entry = {
            "id": record.wafer_id,
            "pattern": record.pattern,
            "shape": [int(record.grid_shape[0]), int(record.grid_shape[1])],
            "rows": [int(v) for v in record.coords[:, 0]],
            "cols": [int(v) for v in record.coords[:, 1]],
            "reality": "".join("1" if v > 0.5 else "0" for v in record.reality),
            # Full precision on purpose. The page reproduces Python's argmax to the
            # last bit, and rounding the prior is enough to change a decision.
            "prior": [float(v) for v in prior],
            "lengthScale": float(default_length_scale(record.coords)),
            "seeds": {},
        }
        for seed in args.seeds:
            mask = draw_initial_mask(record, initial, seed)
            block = {"initial": [int(i) for i in np.flatnonzero(mask)]}
            named = [(p.name, p) for p in (RandomPolicy(), GridPolicy(budget, record.coords))]
            named += [("+".join(terms), AcquisitionPolicy(terms)) for terms in subsets]
            for name, policy in named:
                episode = run_episode(
                    record,
                    prior,
                    policy,
                    initial_mask=mask,
                    budget=budget,
                    seed=seed,
                    model=RealityModel(record.coords, prior),
                )
                selections = [int(i) for i in episode.selections]
                if isinstance(policy, AcquisitionPolicy):
                    reference[f"{record.wafer_id}|{seed}|{name}"] = selections
                else:
                    block[name] = selections
            entry["seeds"][str(seed)] = block
        wafers.append(entry)
        print(f"  {record.wafer_id}  {record.pattern:<10} {record.n_dies:>5} dies")

    doc = {
        "meta": {
            "dataset": dataset["name"],
            "wafers": len(wafers),
            "dies": total_dies,
            "gitCommit": summary.get("git_commit", "unknown"),
            "generatedAt": summary.get("generated_at"),
            "headline": headline(summary),
            # Stamped by scripts/check-playground-parity.mjs once it has replayed the
            # reference traces through the engine this page actually ships.
            "parity": None,
        },
        "dataset": dataset,
        "bias": bias.as_dict(),
        "loop": {
            "initial": initial,
            "budget": budget,
            "seeds": list(args.seeds),
            "priorWeight": PORTED_PRIOR_WEIGHT,
            "spreadWeight": 0.5,
            "eps": 1e-3,
        },
        "wafers": wafers,
    }

    payload = json.dumps(doc, separators=(",", ":"))
    if "</script" in payload.lower():
        raise SystemExit("the wafer payload would close its own script tag")
    template = Path(args.template).read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise SystemExit(f"{args.template} has no {PLACEHOLDER} placeholder")
    return template.replace(PLACEHOLDER, payload), reference


def main(argv: list[str] | None = None) -> int:
    use_utf8_output()
    args = build_parser().parse_args(argv)
    page, reference = build(args)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    ref = Path(args.reference)
    ref.parent.mkdir(parents=True, exist_ok=True)
    ref.write_text(json.dumps(reference, separators=(",", ":")), encoding="utf-8")

    print(f"page      {out}  {out.stat().st_size // 1024} KB")
    print(f"reference {ref}  {ref.stat().st_size // 1024} KB ({len(reference)} traces)")
    print("run `npm run check:playground` to replay those traces through the shipped engine")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
