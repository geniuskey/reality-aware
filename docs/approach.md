---
title: Agentic Active Metrology
description: NANO observes sparse measurements, estimates reality and uncertainty against a biased simulation prior, and selects the next die to measure by acquisition score under a fixed budget.
---

# Agentic Active Metrology

NANO is a loop, not a model. The model produces maps; the loop spends a budget. This page states the
contract of each step — inputs, outputs, and the rule that turns uncertainty into a decision.

::: tip Implementation status
The loop described here is implemented in `nano/`, and the contract below is enforced by the test
suite. The estimator is `nano/model.py`, the acquisition rule is `nano/policy.py`, and the loop is
`nano/agent.py`. Where code and page disagree, that is a bug in one of them — see
[System Design](./architecture) for the file-by-file map.

No page on this site prints a benchmark number that has not been generated. Running the benchmark
against WM-811K is what fills them in — see [Reproduce](./reproducibility).
:::

## The loop

<AgentLoop />

## Interface contract

### Input, per iteration

| Field | Shape | Meaning |
| --- | --- | --- |
| `coords` | `(N, 2)` | Die grid coordinates on the wafer |
| `prior` | `(N,)` | Simulation prediction for every die, available everywhere |
| `observed_mask` | `(N,)` bool | Which dies have been measured so far |
| `observed_values` | `(M,)` | Measured values for those dies, `M = observed_mask.sum()` |
| `budget_remaining` | `int` | Measurements left before the run stops |

### Output, per iteration

| Field | Shape | Meaning |
| --- | --- | --- |
| `prediction` | `(N,)` | Best current estimate of reality at every die |
| `uncertainty` | `(N,)` | Model uncertainty at every die, `0` at measured dies |
| `reality_gap` | `(N,)` | Signed disagreement, `prediction − prior` |
| `next_index` | `int` | Die selected for the next measurement |
| `next_score` | `float` | Acquisition score of that die, for the decision trace |

The three maps are the reason the agent is auditable. A prediction alone cannot be argued with; a
prediction plus an uncertainty map plus a gap map can be inspected before the tool is scheduled.

## Estimating reality

The estimator has one job: reconcile a dense, biased prior with a sparse, trusted set of
measurements, and stay honest about how far the reconciliation reaches.

1. **Start from the prior.** With zero measurements, the estimate *is* the simulation prior, and
   uncertainty is `1.0` everywhere.
2. **Correct locally.** Each measurement contributes a residual, `measured value − prior`, spread by
   a Gaussian kernel in die distance. The weighted mean of those residuals is added to the prior and
   the result is clipped to `[0, 1]`; at a measured die the prediction is the measured value exactly.
3. **Return to the prior where nothing was measured.** The weighted mean is shrunk by
   `prior_weight`, which counts the prior as that many measurements' worth of evidence for "no
   correction here". Without it the estimate would extrapolate a global offset into regions nothing
   has been measured in.
4. **Report the reach.** Uncertainty is `1 / (1 + total kernel weight)`, raised back towards `1` by
   disagreement between the measurements that do reach a die. The scale is absolute — `1.0` means
   nothing measured reaches here, `0.0` means measured — so two maps from one episode are
   comparable, and "uncertainty fell" is a falsifiable claim rather than a rescaling artifact.

The two hyper-parameters (`length_scale`, defaulting to a twelfth of the wafer span, and
`prior_weight`) are fixed before the comparison, identical across every arm, and written into
`results/benchmark_summary.json` under `experiment.model`.

Ground truth for unmeasured dies is never read by the estimator. It exists only in the evaluation
harness. <span class="nano-tag" data-kind="hidden">Hidden from agent</span>

## Selecting the next measurement

The intended acquisition score combines three terms:

```text
acquisition(i) = uncertainty(i) × simulation_disagreement(i) × spatial_novelty(i)
```

| Term | Reads as | Why it belongs |
| --- | --- | --- |
| `uncertainty(i)` | "I do not know this die." | Spending budget where the estimate is already firm buys nothing. |
| `simulation_disagreement(i)` | "The prior is expected to be wrong here." | This is where the Sim2Real gap actually lives. Uncertainty alone will happily sample empty agreement. |
| `spatial_novelty(i)` | "I have not looked in this region." | Prevents the loop from clustering measurements around one interesting spot. |

Each term is min-max scaled to `[0, 1]` over the wafer and floored at `eps = 1e-3`, because a
product is zero if any factor is zero and all three terms are legitimately zero somewhere on every
wafer. The floor ranks a candidate last on a term instead of vetoing it outright.

The disagreement term is **not** `|prediction − prior|`. That map necessarily decays to nothing
beyond the reach of the measurements, so a rule built on it would call every unexplored region
settled and never look there. The model emits a second map, `expected_disagreement`: the locally
weighted *magnitude* of the residuals, shrunk towards the wafer-wide mean residual magnitude
wherever local evidence is thin. It reads as "the prior is off by about this much here, and I have
no evidence to the contrary". `reality_gap` remains an output, because the correction actually
applied is what a reviewer needs to see.

The next measurement is `argmax` over unmeasured dies:

```text
next_index = argmax { acquisition(i) : observed_mask[i] == False }
```

::: tip Keep the formula and the code in sync
If the implementation reduced to plain `argmax(uncertainty)`, this section would have to say
`argmax(uncertainty)`. A three-term product in the documentation and a one-term rule in the code is
the failure mode this project exists to argue against, so the rule that ran is written into every
results file as `experiment.acquisition_rule`, `nano/policy.py` returns the per-term breakdown with
every decision, and `tests/test_policy.py` asserts that the score of the selected die equals the
product of the three terms in its own trace.

Stating a rule is not the same as showing it helps. `python -m nano.benchmark --ablation` re-runs the
loop with terms dropped, and the [benchmark page](./benchmark) publishes what each term is worth —
including where a reduced rule beats this one.
:::

## Stopping and determinism

**Stopping.** The run ends when `budget_remaining` reaches zero. There is no early stop on a
convergence criterion, because a budget is the constraint that actually binds in a fab: tool time is
allocated, not discovered.

**Determinism.** Every stochastic choice is driven by an explicit seed. Seeds are combined with a
stable hash of the wafer id and the strategy name, so a run reproduces across interpreter sessions:

- which wafers enter the evaluation set,
- how the initial sparse observation mask is drawn,
- the Random baseline's selections,
- any tie-breaking inside `argmax`.

Given the same seed, the same wafer and the same budget, a run reproduces exactly. Baselines are
handed the *same* initial observations and the *same* budget as NANO, so the only thing that differs
between arms is the selection rule.

## What this is not

- Not wafer-map interpolation with extra steps. Interpolation answers "what is the value here?"
  NANO answers "where should the next measurement go?"
- Not a replacement for physical simulation. The prior is an input to be corrected, not an output to
  be replaced.
- Not a calibration claim. NANO reports uncertainty and uses it to rank locations; that its
  uncertainty is *calibrated* is a separate assertion, and one this project does not make. See
  [Honest Scope](./limitations).

Next: [the data and the experimental design →](./data)
