---
title: Reproducibility
description: Clone, install, build the docs, and - once the agent lands - run the demo, the benchmark and the tests, with artifact locations and seed control.
---

# Reproducibility

Two things live in this repository, and they are at different stages. This page says plainly which
commands have been run and which have not.

| Path | Status |
| --- | --- |
| Documentation site | **Verified.** The commands below were run in this repository. |
| Agent, dataset and benchmark | **Not implemented yet.** The commands are the intended interface, not something you can run today. |

## Documentation site

Verified on Node.js 22.17.1 / npm 11.5.1; the workflow runs the same commands on Node.js 20.

```bash
git clone https://github.com/geniuskey/reality-aware.git
cd reality-aware
npm ci
npm run docs:dev      # local server with hot reload
npm run docs:build    # static build into docs/.vitepress/dist
npm run docs:preview  # serve the built output
```

`npm ci` needs the committed `package-lock.json`, which is what the deployment workflow installs
from as well.

### Building for a different Pages base path

The base path is derived from `GITHUB_REPOSITORY` during CI, so project Pages
(`/<repo>/`) and user or organisation Pages (`/`) both work without editing the config. Override it
locally when you need to:

```bash
DOCS_BASE=/ npm run docs:build           # user or organisation Pages
DOCS_BASE=/my-fork/ npm run docs:build   # a fork with a different repo name
```

### Publishing figures to the site

The canonical location for experiment output is `results/`. The site reads figures from
`docs/public/results/`. Copy between them with the sync script rather than by hand:

```bash
npm run sync:assets
```

It copies known figure names from `results/` into `docs/public/results/`, skipping anything absent,
and reports what it did. Missing figures are not an error: pages render an explicit
*Run benchmark to generate results* state instead of a broken image, and the build still succeeds.

## Agent and benchmark

::: danger Not runnable yet
No Python package, entry point or test suite is committed in this repository. Everything in this
section is the interface the implementation is expected to expose. Do not treat these as working
commands, and do not treat any number produced by an early version of them as a published result
until it lands in `results/benchmark_summary.json`.
:::

The intended interface:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

python -m nano.demo --wafer 0 --seed 0        # single episode, writes demo figures
python -m nano.benchmark --seeds 0 1 2 3 4    # full comparison, writes the results file
pytest                                        # test suite
```

### Getting the dataset

WM-811K is not committed here — see [Dataset](./data) for the distribution links and terms. The
expected local layout is:

```text
data/
└── raw/
    └── LSWMD.pkl        # downloaded, never committed
```

The subset index derived from it *is* versioned, so an evaluation set can be reconstructed exactly
without redistributing the source data.

### Artifact locations

| Artifact | Path |
| --- | --- |
| Results summary, single source of truth for the site | `results/benchmark_summary.json` |
| Error curve, wafer comparison, uncertainty maps | `results/*.svg`, `results/*.webp` |
| Demo recording | `results/demo.gif` |
| Site copies of published figures | `docs/public/results/` |

### Controlling seeds

Seeds are explicit arguments, never implicit global state:

```bash
python -m nano.benchmark --seeds 0 1 2 3 4     # published configuration
python -m nano.benchmark --seeds 7             # a single run, for a quick check
```

The seed set that produced a results file is recorded inside that file, and the site prints it under
every table and chart. A summary whose `seeds` do not match the run that produced it is a bug worth
reporting.

## Verifying a result you did not produce

1. Read `experiment.seeds`, `experiment.initial_measurements` and `experiment.measurement_budget`
   from `results/benchmark_summary.json`.
2. Re-run the benchmark with exactly those values.
3. Compare `strategies.*.final.mean` against your own run.

If the numbers do not reproduce, the results file is wrong and this site is wrong with it, because
this site does nothing but read it.
