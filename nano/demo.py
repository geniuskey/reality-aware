"""``python -m nano.demo`` — one episode, narrated, with the figures the docs use."""

from __future__ import annotations

import argparse
from pathlib import Path


from nano.agent import draw_initial_mask, run_episode
from nano.cli import RESULTS_DIR, add_experiment_args, add_source_args, resolve_wafers, source_warning
from nano.evaluate import mae
from nano.model import RealityModel
from nano.policy import TERMS, AcquisitionPolicy
from nano.prior import BiasParams, make_biased_prior


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m nano.demo",
        description="Run a single NANO episode and record what it decided, and why.",
    )
    parser.add_argument("--wafer", type=int, default=0, help="index into the evaluation set")
    parser.add_argument("--seed", type=int, default=0, help="episode seed")
    add_source_args(parser)
    add_experiment_args(parser)
    parser.add_argument("--out", type=Path, default=RESULTS_DIR, help="directory for demo figures")
    parser.add_argument("--no-figures", action="store_true", help="print the trace only")
    parser.add_argument("--no-gif", action="store_true", help="skip the animation")
    parser.add_argument("--steps", type=int, default=6, help="trace lines to print")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    records, dataset_block = resolve_wafers(args)
    warning = source_warning(dataset_block)
    if warning:
        print(warning)
    if not 0 <= args.wafer < len(records):
        raise SystemExit(f"--wafer {args.wafer} is out of range for {len(records)} wafers")

    record = records[args.wafer]
    prior = make_biased_prior(record, BiasParams())
    policy = AcquisitionPolicy(args.terms or TERMS)
    model = RealityModel(
        record.coords, prior, length_scale=args.length_scale, prior_weight=args.prior_weight
    )
    episode = run_episode(
        record,
        prior,
        policy,
        initial_mask=draw_initial_mask(record, args.initial, args.seed),
        budget=args.budget,
        seed=args.seed,
        model=model,
    )

    print(
        f"wafer {record.wafer_id} · pattern {record.pattern} · {record.n_dies} dies · "
        f"seed {args.seed}"
    )
    print(f"  prior MAE          {mae(prior, record.reality):.4f}")
    print(f"  after {episode.n_initial} initial   {mae(episode.steps[0].prediction, record.reality):.4f}")
    print(f"  after +{args.budget} measured  {mae(episode.prediction, record.reality):.4f}")
    print("  decision trace (first steps):")
    for step in episode.steps[: args.steps]:
        if step.selected_index is None:
            continue
        terms = " ".join(f"{k}={v:.3f}" for k, v in step.terms.items())
        print(
            f"    m={step.measurements:>3}  die {step.selected_index:>5}  "
            f"score {step.score:.4f}  [{terms}]  measured {step.measured_value:.0f}"
        )

    if args.no_figures:
        return 0

    try:
        from nano import figures
    except ImportError as exc:
        print(f"  figures skipped: {exc}")
        return 0

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    figures.plot_demo_step(record, episode, 0, out / "demo_step_00.webp")
    figures.plot_demo_step(record, episode, min(5, len(episode.steps) - 1), out / "demo_step_05.webp")

    # Re-derive the acquisition surface at the step being illustrated, from the
    # same estimate the policy saw when it chose.
    step_index = min(5, len(episode.steps) - 1)
    observed = episode.mask_at_step(step_index)
    estimate = model.estimate(observed, episode.values_at_step(step_index))
    terms = policy.score_terms(estimate, observed, record.coords)
    figures.plot_selection(record, episode, terms, step_index, out / "demo_selection.webp")

    figures.plot_final_comparison(record, prior, episode, out / "demo_final.webp")
    if not args.no_gif:
        figures.animate_episode(record, episode, out / "demo.gif")
    print(f"  figures written to {out}/")
    print("run `npm run sync:assets` to publish them to the docs site")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
