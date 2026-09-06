"""``python -m nano.benchmark`` — run every arm and write the results file."""

from __future__ import annotations

import argparse
from pathlib import Path

from nano.agent import draw_initial_mask, run_episode
from nano.cli import RESULTS_DIR, add_experiment_args, add_source_args, resolve_wafers, source_warning
from nano.evaluate import DEFAULT_OUTPUT, mae, run_benchmark, write_summary
from nano.model import RealityModel
from nano.policy import AcquisitionPolicy
from nano.prior import BiasParams, make_biased_prior


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m nano.benchmark",
        description="Compare NANO, Random and Grid selection under an identical budget.",
    )
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4], help="episode seeds"
    )
    add_source_args(parser)
    add_experiment_args(parser)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="results file to write")
    parser.add_argument(
        "--no-figures", action="store_true", help="skip figure generation (numbers only)"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    records, dataset_block = resolve_wafers(args)
    warning = source_warning(dataset_block)
    if warning:
        print(warning)

    print(
        f"benchmark: {len(records)} wafers × {len(args.seeds)} seeds · "
        f"{args.initial} initial + {args.budget} budget"
    )
    bias = BiasParams()
    summary = run_benchmark(
        records,
        seeds=args.seeds,
        initial_measurements=args.initial,
        budget=args.budget,
        bias=bias,
        length_scale=args.length_scale,
        prior_weight=args.prior_weight,
        primary_metric=args.metric,
        dataset_block=dataset_block,
    )
    path = write_summary(summary, args.out)
    _report(summary)
    print(f"wrote {path}")

    if not args.no_figures:
        _figures(summary, records, args, bias)
    print("run `npm run sync:assets` to publish figures to the docs site")
    return 0


def _report(summary: dict) -> None:
    """Print the arms, the measurement-free references, and what separates.

    A mean difference is printed with its interval or not at all: an arm whose
    interval spans zero is reported as not separated, however good its mean looks.
    """
    primary = summary["metric"]["key"]
    secondary = "mae" if primary != "mae" else "balanced_mae"
    rows = [(name, arm, False) for name, arm in summary["strategies"].items()]
    rows += [(name, arm, True) for name, arm in summary["references"].items()]

    for metric in (primary, secondary):
        if metric not in summary["metrics"]:
            continue
        label = summary["metrics"][metric]["name"]
        lead = "primary" if metric == primary else "also reported"
        print(f"  {label} ↓ ({summary['metrics'][metric]['scope']}) — {lead}")
        comparisons = summary["comparisons"].get(metric, {})
        for name, arm, is_reference in rows:
            stats = arm["metrics"][metric]
            mark = "·" if is_reference else " "
            line = f"   {mark} {arm['label']:<18} {stats['mean']:.4f} ± {stats['std']:.4f}"
            if name in comparisons:
                line += "   " + _verdict(comparisons[name])
            print(line)


def _verdict(comparison: dict) -> str:
    """One line saying whether NANO actually separated from this arm."""
    if not comparison["separates"]:
        return (
            f"NANO not separated (Δ {comparison['mean']:+.4f}, "
            f"95% CI [{comparison['ci_low']:+.4f}, {comparison['ci_high']:+.4f}], "
            f"{comparison['wins']}/{comparison['n']} wins)"
        )
    direction = "better" if comparison["mean"] > 0 else "WORSE"
    return (
        f"NANO {direction} by {abs(comparison['relative_mean']):.1f}% "
        f"[{comparison['relative_ci_low']:.1f}, {comparison['relative_ci_high']:.1f}], "
        f"{comparison['wins']}/{comparison['n']} wins"
    )


def _figures(summary: dict, records, args: argparse.Namespace, bias: BiasParams) -> None:
    """Regenerate the published figures from this run."""
    try:
        from nano import figures
    except ImportError as exc:
        print(f"  figures skipped: {exc}")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    figures.plot_error_curve(summary, RESULTS_DIR / "error_curve.svg")
    figures.plot_paired_improvement(summary, RESULTS_DIR / "paired_improvement.svg")

    # One representative episode, re-run with the same seed so the figure shows
    # exactly what the benchmark scored.
    record = records[0]
    seed = args.seeds[0]
    prior = make_biased_prior(record, bias)
    episode = run_episode(
        record,
        prior,
        AcquisitionPolicy(),
        initial_mask=draw_initial_mask(record, args.initial, seed),
        budget=args.budget,
        seed=seed,
        model=RealityModel(
            record.coords, prior, length_scale=args.length_scale, prior_weight=args.prior_weight
        ),
    )
    figures.plot_wafer_comparison(record, prior, episode, RESULTS_DIR / "wafer_comparison.webp")
    figures.plot_uncertainty_before_after(record, episode, RESULTS_DIR / "uncertainty_before_after.webp")
    print(
        f"  figures written to {RESULTS_DIR}/ "
        f"(episode figure: {record.wafer_id}, seed {seed}, "
        f"final {summary['metric']['name']} {mae(episode.prediction, record.reality):.4f})"
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
