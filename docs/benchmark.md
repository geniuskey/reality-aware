---
title: Benchmark
description: NANO against Random and Grid selection under an identical measurement budget, identical initial observations and identical wafers, scored against hidden ground truth.
---

# Benchmark

Every figure and every number on this page is rendered from one file,
`results/benchmark_summary.json`. Nothing here is typed into Markdown by hand, so the table, the
chart and the home page cannot disagree with each other.

::: tip Published run — WM-811K, 12 wafers × 5 seeds
Written by `python -m nano.benchmark --ablation` against a local copy of WM-811K. The raw dataset is
not committed; `data/subsets/wm811k_eval.json` names the twelve wafers, so the evaluation set can be
rebuilt exactly. Two things below are worth knowing before reading the rest: NANO separates from
Random and Grid on the primary metric and **not** on plain MAE, and the ablation finds a reduced rule
beating the published one.

A results file is committed only for a run against the dataset. A run on generated stand-in wafers
(`--synthetic`) produces the same file locally and is labelled as such — the table prints the wafer
source — but stand-in numbers are not published as dataset results. See
[Reproduce](./reproducibility).
:::

## What is being compared

All three arms receive the same wafers, the same seeds, the same initial observation mask and the
same additional measurement budget. The **only** difference is which die each one picks next.

| Strategy | Selection rule |
| --- | --- |
| **Random** | Uniformly sample an unmeasured die |
| **Grid** | Pick the unmeasured die closest to the next point on a spatially uniform lattice |
| **NANO** | Pick the unmeasured die with the highest acquisition score |

The rule each arm ran is recorded in the results file, and all three are driven by the same loop in
`nano/agent.py` through the same `select(estimate, observed_mask, coords, rng)` signature. Grid sizes
its lattice to the budget and consumes it in a fixed order; Random draws uniformly from the
unmeasured dies with the episode's seeded generator.

A fair comparison here is a matter of protocol, not of intent: if NANO started from a different
initial mask or spent a larger budget, any improvement would be uninterpretable.

## Headline results

<BenchmarkTable />

### How relative improvement is defined

```text
relative improvement = (baseline error − NANO error) / baseline error × 100
```

Positive means NANO reconstructed the wafer more accurately than the baseline at equal cost.
Negative means it did not, and the table prints that with the same prominence.

### Why every improvement carries an interval

A difference of means is not a result. Each arm is paired with NANO **episode by episode** — same
wafer, same seed, same prior, same initial mask, so the difference within an episode isolates the
selection rule — and the paired differences are bootstrapped (2000 resamples, seed recorded in the
file) into a 95% interval.

If that interval spans zero, the table prints **not separated** instead of a percentage, however
good the mean looks. The win count is printed next to it, because "better on average" and "better on
most wafers" are different claims and a benchmark should not let them be confused.

### Why the primary metric is not plain MAE

Most dies pass. On a wafer where 12% of dies fail, a predictor that answers *"no die fails"*
everywhere and reads **no measurement at all** scores an excellent MAE — better than any strategy
here. That is not a property of the strategies; it is class imbalance being scored as if it were
knowledge.

So the primary metric is **balanced MAE**: the mean of the error on failing dies and the error on
passing dies. A predictor that knows nothing scores exactly `0.5` on it, whatever the failure rate.
The criterion is that chance must look like chance — not that any particular arm wins.

Plain MAE is still computed, still written into the results file, and still printed on this page in
the second table. Where the two disagree, both are shown. Override the choice with
`python -m nano.benchmark --metric mae`; the underlying per-episode numbers do not change, only
which one leads.

### The two rows that spend no budget

Two predictors appear in the table marked *spends no budget*:

| Reference | What it answers | Why it is there |
| --- | --- | --- |
| **Uncorrected prior** | The simulation prior, with no measurement applied | The floor the whole exercise is meant to beat |
| **Constant** | `0.0` everywhere on a binary target — reads nothing | The trap plain MAE walks into, made visible instead of hidden |

A selection rule that cannot beat a predictor which reads nothing has not earned the tool time it
spent. Putting both in the same table as the strategies is the cheapest way to keep that check from
being skipped.

## Measurements versus error

<BenchmarkChart />

The interesting part of this curve is its shape, not just its endpoint. A selection rule that is
merely lucky converges at the same rate as Random and separates only at the end. A rule that is
genuinely choosing informative locations should separate early, while budget still remains.

## Does each term of the acquisition rule earn its place?

The selection rule is a product of three terms, and a product of three terms is a claim: that each
one changes the decision for the better. The way to find out is to drop them and re-run, so
`python -m nano.benchmark --ablation` runs the reduced rules as extra arms — same loop, same budget,
same initial observations, only the terms differ.

<AblationTable />

This is the table most likely to embarrass the rest of this site, which is exactly why it is here
rather than in a notebook. A reduced rule that beats the published one means the term it dropped is
costing accuracy rather than buying it — and on this run one does: `uncertainty` alone. The published
rule stays what the [approach page](./approach) documents, for a reason [Honest Scope](./limitations)
states in full: twelve wafers on a binary target are not grounds to redefine the method, and the
continuous run reverses the finding. `--terms uncertainty` runs the reduced rule today.

## Prior versus corrected reconstruction

Both wafers below are single episodes, not results. The scored table above covers every evaluation
wafer; these two are drawn because the mechanism is clearest on one and weakest on the other, and
each image states the criterion that picked it. The pair is published together on purpose — one
flattering wafer on its own is a claim nobody can check.

<ResultAsset
  file="wafer_comparison.webp"
  title="Prior → reconstruction → ground truth"
  caption="The wafer whose prior error the measurements reduced most: biased prior, NANO reconstruction, and hidden ground truth on a common scale."
  producedBy="scripts/plot_wafer_comparison" />

<ResultAsset
  file="wafer_comparison_weakest.webp"
  title="The same three panels, weakest wafer"
  caption="The wafer where choosing what to measure earned the least over Random and Grid. Nobody selected it; it is whichever wafer the benchmark scored worst, and it is here so the figure above cannot be read as typical."
  producedBy="python -m nano.benchmark" />

Which wafer each figure shows is recorded in `results/benchmark_summary.json` under `figures`,
together with the rule that chose it, so the caption cannot drift from the image. `--figure-wafer`
overrides the first one; the weakest wafer is deliberately not overridable.

## Uncertainty before and after

<ResultAsset
  file="uncertainty_before_after.webp"
  title="Uncertainty map, start versus end of budget"
  caption="Where the agent knew it was blind at the start, and what remained unknown after the budget was spent."
  producedBy="scripts/plot_uncertainty" />

Uncertainty and prediction are drawn on deliberately different colour scales. They answer different
questions and should never be read off the same legend.

## Per-wafer improvement

<ResultAsset
  file="paired_improvement.svg"
  title="Paired improvement distribution"
  caption="Per-wafer difference between NANO and each baseline, so wins and losses are both visible rather than averaged away."
  producedBy="scripts/plot_paired_improvement" />

A mean improvement can hide a rule that helps most wafers a little and hurts a few a lot. The paired
distribution is the figure that would expose that, which is why it is here rather than a single bar.

## Does the uncertainty map rank anything?

NANO ranks locations by uncertainty, so the map has to order the dies by how wrong the estimate is
there — otherwise the acquisition rule is sorting on noise. The run checks it directly: on the dies
the agent never measured, bin by reported uncertainty and report the error actually made.

<ResultAsset
  file="calibration.svg"
  title="Reported uncertainty against the error actually made"
  caption="Equal-count bins over the unmeasured dies at the end of the budget, with the Spearman rank correlation printed."
  producedBy="scripts/plot_calibration" />

Measured dies are excluded on purpose. They have zero uncertainty and zero error by construction, so
including them would manufacture a correlation out of the tool's own bookkeeping.

::: warning This is a ranking check, not a calibration claim
A rising curve says uncertainty *orders* the dies usefully. It does not say the values are
probabilities, and nothing here evaluates whether a stated interval covers the truth at its stated
rate — no interval is stated. The results file names the field `rank_correlation` for that reason.
See [Honest Scope](./limitations).
:::

## Where NANO fails

Every pattern class in the evaluation set is scored, including the ones that go the wrong way, and
this is where they are rather than in a footnote.

<PatternTable />

Three things in this run deserve more attention than the headline number:

- **Random defects.** On the one wafer whose failures have no spatial structure, NANO ends behind
  Grid. A rule that ranks locations by coverage and prior disagreement has nothing to exploit when
  failures are scattered independently, and that is the honest shape of the claim: choosing where to
  measure helps where reality has structure to find.
- **Plain MAE.** The advantage over Random and Grid does not survive the switch away from the
  balanced metric — both intervals span zero, and the table at the top of this page says so. What
  balancing rewards is getting the rare failing dies right, which is what the budget is being spent
  on.
- **Seed spread.** On the Near-full class the seed-to-seed spread is wider than the margin over the
  baselines, so that row's mean is not a conclusion. Five episodes is five episodes.

The wafer where selection earned least is published as a figure above. The per-episode records
behind this table are in `episodes`, one entry per `(wafer, seed)`, and the per-pattern means come
from `strategies.*.by_pattern`.

## Results file schema

`results/benchmark_summary.json` is the single source of truth. The site validates it on build and
fails loudly on a malformed file rather than rendering something plausible.

```json
{
  "schema_version": 1,
  "generated_at": "2026-01-01T00:00:00Z",
  "git_commit": "<short sha of the run>",
  "dataset": {
    "name": "WM-811K",
    "subset_file": "<path to the versioned subset index>",
    "n_wafers": 0
  },
  "experiment": {
    "seeds": [0, 1, 2],
    "initial_measurements": 0,
    "measurement_budget": 0,
    "grid_shape": [0, 0]
  },
  "metric": {
    "name": "MAE",
    "direction": "lower_is_better",
    "unit": "failure probability"
  },
  "prior": { "initial_error": { "mean": 0.0, "std": 0.0 } },
  "strategies": {
    "nano": {
      "label": "NANO",
      "description": "highest acquisition score",
      "final": { "mean": 0.0, "std": 0.0 },
      "curve": [{ "measurements": 0, "mean": 0.0, "std": 0.0 }]
    },
    "random": {
      "label": "Random",
      "description": "uniform over unmeasured dies",
      "final": { "mean": 0.0, "std": 0.0 },
      "curve": []
    },
    "grid": {
      "label": "Grid",
      "description": "spatially uniform lattice",
      "final": { "mean": 0.0, "std": 0.0 },
      "curve": []
    }
  },
  "assets": { "error_curve": "results/error_curve.svg" }
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `schema_version` | yes | Build fails without it |
| `strategies` | yes | Keys `nano`, `random`, `grid` get dedicated colours and line styles |
| `strategies.*.final` | yes | Drives the table and the home-page metric cards |
| `strategies.*.curve` | for the chart | Omit it and the chart shows its pending state; the table still renders |
| `metric.direction` | recommended | Controls the `↓` / `↑` marker printed next to every metric |
| `prior.initial_error` | recommended | Lets the site report how much prior error the correction removed |
| `dataset.name` | recommended | Printed under the table as the wafer source |
| `dataset.note` | when not WM-811K | A stand-in run writes a note here and the table prints it prominently |
| `metric.key` | recommended | Which entry of `metrics` leads the table, the curve and every comparison |
| `metrics` | for the second table | Every metric the run scored, with its name and scope |
| `strategies.*.metrics` | for the second table | Per-arm values for each of those metrics |
| `references` | recommended | The measurement-free rows: `prior` and `constant` |
| `comparisons` | for the intervals | `comparisons[metric][arm]` — paired mean, 95% interval, win count and `separates` |

The file the harness writes carries more than the minimum: `experiment.acquisition_rule` and
`experiment.prior_bias` and `experiment.model` record the rule and the parameters that produced the
numbers, `strategies.*.by_pattern` breaks results down by failure pattern, and `episodes` lists every
`(wafer, seed)` pair so per-episode wins and losses stay recoverable from the published file.

Figures referenced by [ResultAsset](./architecture) are read from `docs/public/results/`. The sync
script copies them there from the canonical `results/` directory — see
[Reproduce](./reproducibility).

Next: [walk through a single run →](./demo)
