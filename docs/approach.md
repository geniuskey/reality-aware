---
title: Agentic Active Metrology
description: NANO observes sparse measurements, estimates reality and uncertainty against a biased simulation prior, and selects the next die to measure by acquisition score under a fixed budget.
---

# Agentic Active Metrology

NANO is a loop, not a model. The model produces maps; the loop spends a budget. This page states the
contract of each step — inputs, outputs, and the rule that turns uncertainty into a decision.

::: warning Implementation status
The agent and benchmark code are **not in this repository yet**. This page states the intended
contract so that the implementation and the documentation can be checked against each other. Where
the shipped code ends up differing, this page is the thing that must change. No page on this site
prints a benchmark number that has not been generated — see [Reproduce](./reproducibility).
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
   uncertainty is high everywhere.
2. **Correct locally.** Each measurement pulls the estimate towards ground truth in its
   neighbourhood, with influence decaying over distance.
3. **Report the reach.** Uncertainty grows with distance from the nearest measurement and with
   disagreement between nearby measurements.

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
| `simulation_disagreement(i)` | "The prior and the evidence disagree here." | This is where the Sim2Real gap actually lives. Uncertainty alone will happily sample empty agreement. |
| `spatial_novelty(i)` | "I have not looked in this region." | Prevents the loop from clustering measurements around one interesting spot. |

The next measurement is `argmax` over unmeasured dies:

```text
next_index = argmax { acquisition(i) : observed_mask[i] == False }
```

::: tip Keep the formula and the code in sync
If the implementation reduces to plain `argmax(uncertainty)`, this section must say
`argmax(uncertainty)`. A three-term product in the documentation and a one-term rule in the code is
the failure mode this project exists to argue against. The
[benchmark page](./benchmark) records which rule produced the published numbers.
:::

## Stopping and determinism

**Stopping.** The run ends when `budget_remaining` reaches zero. There is no early stop on a
convergence criterion, because a budget is the constraint that actually binds in a fab: tool time is
allocated, not discovered.

**Determinism.** Every stochastic choice is driven by an explicit seed:

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
