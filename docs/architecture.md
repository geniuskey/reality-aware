---
title: System Design
description: The modules NANO is built from - observation tool, reality model, acquisition policy, agent loop and evaluation harness - with their inputs, outputs and responsibilities.
---

# System Design

::: tip Every row below points at a file that exists
The Python package is in `nano/`. This page was written before the code and has been corrected
against it: each module link resolves, and the boundaries described here are the ones
`tests/` enforces — including a leakage test that flips hidden reality at every unmeasured die and
requires the agent's trajectory to come out identical.
:::

## Data flow

```mermaid
flowchart TD
    A[WM-811K Reality] --> B[Observation Tool]
    C[Biased Prior] --> D[Reality Model]
    B --> D
    D --> E[Prediction and Uncertainty]
    E --> F[Acquisition Policy]
    F --> B
    A --> G[Evaluation Harness]
    E --> G
```

<p class="nano-note">Reality reaches the agent only through the observation tool. The biased prior and the observed values feed the reality model, which emits prediction and uncertainty; the acquisition policy reads those and asks the observation tool for one more die. Reality also flows directly to the evaluation harness, which the agent never reads.</p>

The single most important property of this graph: **reality reaches the agent only through the
observation tool**. The direct edge from reality to the evaluation harness carries ground truth that
the agent never sees. Any shortcut across that boundary invalidates every number on the
[benchmark page](./benchmark).

## Modules

| Module | Responsibility | Input | Output |
| --- | --- | --- | --- |
| [`nano/data.py`](https://github.com/geniuskey/reality-aware/blob/main/nano/data.py) | Load WM-811K, filter and index the evaluation subset, expose the in-wafer die mask | Dataset path, seed | Wafer records: reality field, die mask, pattern label |
| [`nano/prior.py`](https://github.com/geniuskey/reality-aware/blob/main/nano/prior.py) | Generate the deliberately biased simulation prior from a reality field | Reality field, bias parameters | Prior field defined on every in-wafer die |
| [`nano/tools/observe.py`](https://github.com/geniuskey/reality-aware/blob/main/nano/tools/observe.py) | The only channel to reality. Reveals one die's value and spends one unit of budget | Die index | Measured value, updated observation state |
| [`nano/model.py`](https://github.com/geniuskey/reality-aware/blob/main/nano/model.py) | Reconcile prior with observations; produce prediction, uncertainty, reality-gap and expected-disagreement maps | Prior, observed mask, observed values | `prediction`, `uncertainty`, `reality_gap`, `expected_disagreement` |
| [`nano/policy.py`](https://github.com/geniuskey/reality-aware/blob/main/nano/policy.py) | Score unmeasured dies and select the next measurement | Model outputs, observed mask | `next_index`, `next_score`, per-term breakdown |
| [`nano/agent.py`](https://github.com/geniuskey/reality-aware/blob/main/nano/agent.py) | Run the Observe → Estimate → Select → Measure loop until the budget is exhausted | Wafer record, budget, seed | Decision trace, per-step maps |
| [`nano/baselines.py`](https://github.com/geniuskey/reality-aware/blob/main/nano/baselines.py) | Random and Grid selection rules behind the same policy interface | Model outputs, observed mask | `next_index` |
| [`nano/evaluate.py`](https://github.com/geniuskey/reality-aware/blob/main/nano/evaluate.py) | Score predictions against hidden ground truth and aggregate over wafers and seeds | Predictions, reality fields | `results/benchmark_summary.json` |
| [`nano/figures.py`](https://github.com/geniuskey/reality-aware/blob/main/nano/figures.py) | Draw every published figure from a run, never from an illustration | Summary or episode | `results/*.svg`, `results/*.webp`, `results/demo.gif` |
| [`nano/cli.py`](https://github.com/geniuskey/reality-aware/blob/main/nano/cli.py) | Shared argument parsing; re-run one episode exactly as the benchmark ran it | Command-line arguments | Wafer records, episode bundle |

Entry points: `python -m nano.benchmark` (all arms, writes the results file), `python -m nano.demo`
(one narrated episode plus its figures) and `python -m nano.subset` (derive the versioned evaluation
index from a local WM-811K).

## Boundaries that matter

**One tool, one budget.** Every measurement goes through `nano.tools.observe`. Budget accounting
lives inside the tool, not in the caller, so no strategy can quietly take an extra look.

**Baselines share the policy interface.** Random and Grid implement the same signature as the NANO
policy and are driven by the same loop. Swapping the selection rule is the only change between arms —
which is what makes the comparison mean anything.

**Evaluation is downstream of everything.** `nano.evaluate` is the only module that touches full
reality fields, and it never returns anything to the agent.

**One results file.** `nano/evaluate.py` writes `results/benchmark_summary.json`; the site reads it.
Charts, tables and headline numbers on this site all derive from that file, so a number cannot be
updated in one place and stale in another. Schema is documented on the
[benchmark page](./benchmark).

## Documentation site

The site is deliberately boring: a static VitePress build with no backend, no runtime data fetching
and no analytics.

| Piece | Path | Role |
| --- | --- | --- |
| Config | `docs/.vitepress/config.mts` | Nav, sidebar, SEO, Mermaid, base-path handling for project and user Pages |
| Results loader | `docs/.vitepress/data/benchmark.data.mts` | Reads and validates `results/benchmark_summary.json` at build time |
| Asset loader | `docs/.vitepress/data/assets.data.mts` | Lists `docs/public/results/` so missing figures degrade to a pending state |
| Components | `docs/.vitepress/theme/components/` | `AgentLoop`, `WaferComparison`, `BenchmarkChart`, `BenchmarkTable`, `EvidenceStrip`, `MetricCard`, `ResultAsset` |
| Asset sync | `scripts/sync-doc-assets.mjs` | Copies published figures from `results/` into `docs/public/results/` |
| Figure scripts | `scripts/plot_*.py`, `scripts/record_demo.py` | Regenerate one published figure at a time from a run |
| Deployment | `.github/workflows/deploy-docs.yml` | Builds on push to `main` and publishes to GitHub Pages |

Components render at build time, so the pages carry their content as static HTML. With JavaScript
disabled the prose, the tables, the wafer schematic and the result figures all still read; only
Mermaid diagrams and the search box need the client runtime.

Next: [run it yourself →](./reproducibility)
