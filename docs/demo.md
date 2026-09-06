---
title: Demo
description: A single NANO episode, step by step - biased prior, sparse start, the first selection and why, uncertainty collapse, and the final comparison against hidden ground truth.
---

# Demo

This page is static by design. GitHub Pages serves files, not Python, so the demo here is the
recording of a real run rather than a live one. The interactive version runs locally — see
[Reproduce](./reproducibility).

::: warning No published recording yet
The demo is implemented — `python -m nano.demo --wafer 0 --seed 0` prints the decision trace and
writes every figure below — but no recording from a WM-811K run is published here. Each block states
which artifact it is waiting for, and nothing is illustrated with a stand-in that could be mistaken
for a real run.

Run it locally and the figures appear; `npm run sync:assets` publishes them to a local build of this
site.
:::

## The schematic version

Before the recording, here is the shape of what happens, drawn from a formula rather than from data:

<WaferComparison />

## Walkthrough of one episode

### Step 1 — Look at the prior

The agent starts with a simulation prior covering every die and no measurements at all. The prior is
smooth, confident, and wrong at the wafer edge. At this point the estimate *is* the prior, and
uncertainty is high everywhere.

<ResultAsset
  file="demo_step_00.webp"
  title="Step 0 — prior only"
  caption="Prior across the full wafer, before any measurement. Uncertainty is uniformly high."
  producedBy="scripts/record_demo" />

### Step 2 — Take in the sparse start

A small, centre-biased set of initial measurements arrives. Near them the estimate tightens
immediately; far from them nothing has changed. The uncertainty map now has visible structure, and
that structure is the agent's own map of its ignorance.

<ResultAsset
  file="demo_step_05.webp"
  title="Step 5 — initial observations absorbed"
  caption="Prediction and uncertainty after the initial sparse mask, with measured dies marked."
  producedBy="scripts/record_demo" />

### Step 3 — Watch it choose, and check why

The selection is the part worth scrutinising. A die is chosen because it scores highest on the
acquisition function, and the score decomposes into terms that can be read separately: how unknown
the die is, how much the prior is expected to be wrong there, and how far it is from anything
already sampled. A choice that cannot be explained by those three numbers is a bug, not a decision.

The command prints the same decomposition as text, one line per measurement:

```text
m= 22  die   472  score 0.2551  [uncertainty=0.797 disagreement=0.572 novelty=0.559]  measured 0
```

<ResultAsset
  file="demo_selection.webp"
  title="Acquisition score at the moment of choice"
  caption="Acquisition surface with the selected die marked, alongside the uncertainty and disagreement terms that produced it."
  producedBy="scripts/record_demo" />

### Step 4 — Confirm uncertainty actually falls

After the measurement is taken, uncertainty should drop in the neighbourhood of the new point, and
the prediction should move towards the measured value. If uncertainty does not fall where a
measurement was just taken, the estimator is not doing its job.

<ResultAsset
  file="demo.gif"
  title="Full episode"
  caption="Every iteration of one budget: selection, measurement, and the uncertainty map collapsing."
  producedBy="scripts/record_demo" />

### Step 5 — Compare against the truth that was hidden

Only at the end does the evaluation harness reveal the full wafer.
<span class="nano-tag" data-kind="hidden">Hidden from agent</span> The comparison is between the
original biased prior, the final reconstruction, and reality.

<ResultAsset
  file="demo_final.webp"
  title="Final comparison"
  caption="Biased prior, NANO reconstruction and hidden ground truth on one common scale."
  producedBy="scripts/record_demo" />

## What to look for

| Question | Where the answer shows up |
| --- | --- |
| Does the estimate improve where measurements land? | Prediction map tightening around measured dies |
| Does the agent know where it is blind? | Uncertainty map structure before any correction |
| Is the selection explainable? | Acquisition surface decomposed into its terms |
| Does it beat spending the same budget arbitrarily? | [Benchmark](./benchmark), not this page |

A demo can show that a loop runs and that its decisions are legible. It cannot show that the loop is
better than the alternatives — only the benchmark can, and only under equal budget.
