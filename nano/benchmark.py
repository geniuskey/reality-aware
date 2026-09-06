"""``python -m nano.benchmark`` — run every arm and write the results file."""

from __future__ import annotations

import argparse
from pathlib import Path

from nano.agent import draw_initial_mask, run_episode
from nano.cli import (
    RESULTS_DIR,
    add_experiment_args,
    add_source_args,
    resolve_wafer_index,
    resolve_wafers,
    source_warning,
    use_utf8_output,
)
from nano.evaluate import DEFAULT_OUTPUT, run_benchmark, select_figure_wafers, write_summary
from nano.metrics import metric_set
from nano.model import RealityModel
from nano.policy import TERMS, AcquisitionPolicy
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
    parser.add_argument(
        "--figure-wafer",
        default=None,
        help=(
            "wafer id or index to draw the illustrative figure from "
            "(default: the wafer whose prior error the measurements reduced most). "
            "The weakest wafer is always drawn as well and cannot be overridden"
        ),
    )
    parser.add_argument(
        "--ablation",
        action="store_true",
        help="also run the acquisition rule with terms dropped, to show what each one is worth",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    use_utf8_output()
    args = build_parser().parse_args(argv)
    records, dataset_block = resolve_wafers(args)
    if args.figure_wafer is not None:
        # Fail here rather than after the run: the selector is checkable the
        # moment the wafers are loaded, and a typo should cost a second.
        resolve_wafer_index(records, args.figure_wafer, flag="--figure-wafer")
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
        ablation=args.ablation,
        terms=args.terms,
        dataset_block=dataset_block,
    )
    summary["figures"] = select_figure_wafers(summary, override=args.figure_wafer)
    path = write_summary(summary, args.out)
    _report(summary)
    _report_ablation(summary)
    _report_calibration(summary)
    print(f"wrote {path}")

    # Figures follow the results file. A side run written elsewhere -- a
    # stand-in check, a different target -- must not overwrite the published
    # figures, which belong to whatever run wrote results/benchmark_summary.json.
    figures_dir = Path(path).parent
    if not args.no_figures:
        _figures(summary, records, args, bias, figures_dir)
    if figures_dir.resolve() == RESULTS_DIR.resolve():
        print("run `npm run sync:assets` to publish figures to the docs site")
    else:
        print(f"figures written beside the results file in {figures_dir}, not to {RESULTS_DIR}")
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


def _report_calibration(summary: dict) -> None:
    """Whether the uncertainty map ranks usefully — reported, never assumed."""
    calibration = summary.get("calibration") or {}
    rho = calibration.get("rank_correlation") or {}
    if not rho:
        return
    print(
        f"  uncertainty ranking: Spearman ρ = {rho['pooled']:.3f} pooled, "
        f"{rho['per_episode_mean']:.3f} ± {rho['per_episode_std']:.3f} per episode "
        f"({calibration['n_dies']} unmeasured dies) — ranking only, not a coverage claim"
    )


def _report_ablation(summary: dict) -> None:
    """What each term of the acquisition product is actually worth."""
    ablation = summary.get("ablation") or {}
    if not ablation:
        return
    primary = summary["metric"]["key"]
    comparisons = summary["comparisons"].get(primary, {})
    print(f"  ablation on {summary['metrics'][primary]['name']} ↓ (full rule = NANO)")
    full = summary["strategies"]["nano"]["final"]
    print(f"     {'uncertainty × disagreement × novelty':<38} {full['mean']:.4f} ± {full['std']:.4f}")
    for name, arm in ablation.items():
        stats = arm["final"]
        line = f"     {arm['rule'].replace(' x ', ' × '):<38} {stats['mean']:.4f} ± {stats['std']:.4f}"
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


def _figures(
    summary: dict, records, args: argparse.Namespace, bias: BiasParams, results_dir: Path
) -> None:
    """Regenerate the figures for this run, beside the results file it wrote."""
    try:
        from nano import figures
    except ImportError as exc:
        print(f"  figures skipped: {exc}")
        return

    results_dir.mkdir(parents=True, exist_ok=True)
    figures.plot_error_curve(summary, results_dir / "error_curve.svg")
    figures.plot_paired_improvement(summary, results_dir / "paired_improvement.svg")
    if summary.get("calibration", {}).get("reliability"):
        figures.plot_calibration(summary, results_dir / "calibration.svg")

    # Two named episodes, re-run with the benchmark's first seed so each figure
    # shows exactly what was scored. Which wafer each one is, and why, comes from
    # the summary rather than from this function, so the caption and the number
    # cannot drift apart.
    selection = summary["figures"]
    seed = int(selection["seed"])
    by_id = {record.wafer_id: record for record in records}
    primary = summary["metric"]["key"]

    illustrative = selection["illustrative"]
    weakest = selection["weakest"]
    _draw_episode(
        by_id[illustrative["wafer_id"]], illustrative, args, bias, seed, primary,
        comparison_path=results_dir / "wafer_comparison.webp",
        uncertainty_path=results_dir / "uncertainty_before_after.webp",
    )
    if weakest["wafer_id"] != illustrative["wafer_id"]:
        _draw_episode(
            by_id[weakest["wafer_id"]], weakest, args, bias, seed, primary,
            comparison_path=results_dir / "wafer_comparison_weakest.webp",
        )
    print(f"  {selection['note']}")


def _draw_episode(
    record,
    choice: dict,
    args: argparse.Namespace,
    bias: BiasParams,
    seed: int,
    primary: str,
    *,
    comparison_path,
    uncertainty_path=None,
):
    """Re-run one named wafer and write its figures, stamped with why it was picked."""
    from nano import figures

    prior = make_biased_prior(record, bias)
    episode = run_episode(
        record,
        prior,
        AcquisitionPolicy(args.terms or TERMS),
        initial_mask=draw_initial_mask(record, args.initial, seed),
        budget=args.budget,
        seed=seed,
        model=RealityModel(
            record.coords, prior, length_scale=args.length_scale, prior_weight=args.prior_weight
        ),
    )
    note = f"selected: {choice['criterion']} · seed {seed} · one wafer, not a sample"
    figures.plot_wafer_comparison(record, prior, episode, comparison_path, note=note)
    if uncertainty_path is not None:
        figures.plot_uncertainty_before_after(record, episode, uncertainty_path, note=note)
    score = metric_set(episode.prediction, record.reality, record.target_kind)[primary]
    print(
        f"  {comparison_path.name}: {record.wafer_id} ({record.pattern}), seed {seed}, "
        f"final {primary} {score:.4f} — {choice['criterion']}"
    )
    return episode


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
