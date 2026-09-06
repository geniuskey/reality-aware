# NANO — Reality-Aware AI Development Lifecycle for Semiconductor Manufacturing

An autonomous metrology agent that identifies what it does not know and selects the next most
valuable measurement to close the Sim2Real gap.

**Maximize knowledge of reality per measurement.**

Docs site: <https://geniuskey.github.io/reality-aware/> (Korean: <https://geniuskey.github.io/reality-aware/ko/>)

Playground — run the loop on the real wafers, in a browser:
<https://geniuskey.github.io/reality-aware/playground.html>

## Status

A benchmark run against WM-811K is published: 12 wafers × 5 seeds, 20 initial measurements plus a
budget of 60. On balanced MAE, NANO beats Random by 8.7% [6.6, 11.1] and Grid by 6.3% [4.6, 8.1],
both intervals clear of zero. On plain MAE it is **not separated** from either. The ablation in the
same run finds `uncertainty` alone beating the published three-term rule by 2.2% [0.6, 4.3] — a
result against the design, which is why it is on the benchmark page and not in a footnote.

The WM-811K distribution is not committed here. `data/subsets/wm811k_eval.json` names the twelve
wafers and `results/benchmark_summary.json` holds every number the site renders, so the run can be
rebuilt and checked without redistributing the dataset. The playground is the one narrow exception:
it re-runs the loop in the browser, so it embeds those twelve wafers' die coordinates and pass/fail
labels — 18,241 dies, about 0.002% of the 811,457 maps. The pipeline also runs without the dataset,
on clearly labelled stand-in wafers (`--synthetic`), which is how the code is tested. Those numbers
are never committed here and the site prints the wafer source under every results table, so a
stand-in number cannot be read as a dataset number.

See [Honest Scope](https://geniuskey.github.io/reality-aware/limitations) for what is claimed and
what is not.

## Run the agent

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

pytest                                                     # 121 tests, no dataset needed
python -m nano.demo --synthetic --wafer 0 --seed 0          # one narrated episode + figures
python -m nano.benchmark --synthetic --seeds 0 1 2 3 4      # all three arms + results file
python -m nano.benchmark --synthetic --ablation             # what each acquisition term is worth
python -m nano.benchmark --synthetic --target continuous    # metrology-like values, not labels
```

With a local copy of WM-811K at `data/raw/LSWMD.pkl`, build the versioned evaluation index once and
drop the `--synthetic` flag:

```bash
python -m nano.subset --wafers 12 --seed 0    # writes data/subsets/wm811k_eval.json
python -m nano.benchmark --seeds 0 1 2 3 4    # writes results/benchmark_summary.json
npm run sync:assets                           # publish the figures to the site
```

`pip install -e .` installs numpy alone, which is enough for the loop and the benchmark. The extras
add matplotlib and pillow (`figures`), pandas for reading `LSWMD.pkl` (`data`), and pytest (`dev`).

### What the loop is

`Observe → Estimate → Select → Measure`, once per unit of measurement budget. Reality reaches the
agent only through `nano/tools/observe.py`, which holds the budget itself, so no strategy can take an
extra look. `nano/evaluate.py` is the only module that reads full ground-truth fields, and it never
returns anything to the agent. The selection rule is

```text
acquisition(i) = uncertainty(i) × simulation_disagreement(i) × spatial_novelty(i)
```

and it is recorded in every results file, so the documented rule and the executed rule cannot drift
apart.

### What a run reports

Every arm is paired with NANO episode by episode and bootstrapped, so an improvement comes with a
95% interval and prints **not separated** when that interval spans zero. Two measurement-free
predictors — the uncorrected prior and a constant — are scored in the same table, because a rule that
cannot beat a predictor which reads nothing has not earned the tool time it spent. The primary
metric on a binary target is balanced MAE, since plain MAE over rare failures is won by answering
"no die fails" everywhere; both are reported. `--ablation` re-runs the rule with terms dropped, and
every run reports whether its uncertainty map actually ranks the dies by error.

What the published run does and does not establish is on the
[Honest Scope page](https://geniuskey.github.io/reality-aware/limitations), including the findings
that go against the design.

## Run the docs locally

Requires Node 20 or newer.

```bash
npm ci            # or: npm install
npm run docs:dev  # http://localhost:5173/reality-aware/
```

Other scripts:

```bash
npm run docs:build    # static build into docs/.vitepress/dist
npm run docs:preview  # serve the build
npm run sync:assets   # copy figures from results/ into docs/public/results/
```

The site's base path is derived from `GITHUB_REPOSITORY`, so a fork builds at its own path with no
edits. Override it locally when needed:

```bash
DOCS_BASE=/ npm run docs:build          # user or org Pages (<owner>.github.io)
DOCS_BASE=/my-fork/ npm run docs:build  # a differently named fork
```

## Deploying to GitHub Pages

`.github/workflows/deploy-docs.yml` builds and publishes on every push to `main`.

**One manual step is required:** in the repository, go to **Settings → Pages** and set
**Source** to **GitHub Actions**. Without it the workflow builds successfully but nothing is
published.

## Layout

| Path | Contents |
| --- | --- |
| `nano/` | The Python package: data, prior, observation tool, model, policy, baselines, agent, evaluation, figures |
| `tests/` | Test suite, including a leakage test that flips hidden reality at unmeasured dies and requires an identical trajectory |
| `data/subsets/` | Versioned evaluation index derived from WM-811K (the raw maps are never committed) |
| `docs/` | English Markdown pages, VitePress config, theme and Vue components |
| `docs/ko/` | Korean translation of every page |
| `docs/public/` | Logo, favicon, social card, published result figures, the built playground page |
| `playground/` | Playground source (`template.html`) and the Python traces its parity check replays |
| `results/` | Canonical benchmark output — `benchmark_summary.json` and generated figures |
| `scripts/` | Figure scripts (`plot_*.py`, `record_demo.py`), `sync-doc-assets.mjs`, `check-playground-parity.mjs`, social-card source |
| `.github/workflows/` | Pages deployment |

`results/` is the single source of truth for numbers. Nothing is hand-typed into the Markdown, so a
figure cannot go stale in one place and be correct in another.

## Layout of the package

| Module | Responsibility |
| --- | --- |
| `nano/data.py` | Load WM-811K, filter and index the evaluation subset, generate labelled stand-in wafers |
| `nano/prior.py` | The deliberately biased simulation prior: smoothing, radial bias, offset and gain |
| `nano/tools/observe.py` | The only channel to reality; holds and spends the measurement budget |
| `nano/model.py` | Prediction, uncertainty, reality gap and expected disagreement from prior + observations |
| `nano/policy.py` | The three-term acquisition rule, its ablations, and the per-term breakdown for every decision |
| `nano/metrics.py` | Class-balanced metrics, paired bootstrap intervals, and the uncertainty-ranking check |
| `nano/baselines.py` | Random and Grid, behind the same interface |
| `nano/agent.py` | The loop, and the initial centre-biased observation mask |
| `nano/evaluate.py` | Scoring against hidden ground truth; writes `results/benchmark_summary.json` |
| `nano/figures.py` | Every published figure, drawn from a real run |

## Data

The experiment uses the **WM-811K wafer map dataset** (Wu, Jang & Chen, IEEE Transactions on
Semiconductor Manufacturing, 2015). No raw dataset files are committed here; download it locally and
check the licence on the page you download from before redistributing. Details on the
[Dataset & Design page](https://geniuskey.github.io/reality-aware/data).
