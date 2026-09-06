---
layout: home
title: NANO — Reality-Aware AI Development Lifecycle for Semiconductor Manufacturing
titleTemplate: false

hero:
  name: NANO
  text: Reality-Aware AI Development Lifecycle for Semiconductor Manufacturing
  tagline: An autonomous metrology agent that knows what it does not know. It estimates reality from a biased simulation prior plus sparse measurements, quantifies where it is uncertain, and selects the most valuable die to measure next.
  actions:
    - theme: brand
      text: See how it works
      link: /approach
    - theme: alt
      text: View results
      link: /benchmark
    - theme: alt
      text: GitHub
      link: https://github.com/geniuskey/reality-aware
---

## Semiconductor AI learns from what we measure — not necessarily from reality

A model can score well on the data you have and still be wrong about the wafer. Full inspection of
millions of dies is impossible, so every dataset is a sample, and every sample carries a bias the
metric does not show. High accuracy is not the same thing as confidence about reality.

<div class="nano-grid" data-cols="4">
  <div class="nano-panel">
    <p class="nano-eyebrow">Constraint 01</p>
    <h3>Sparse inspection</h3>
    <p>Only a small fraction of dies can be measured. The rest is inference, whether or not anyone calls it that.</p>
  </div>
  <div class="nano-panel">
    <p class="nano-eyebrow">Constraint 02</p>
    <h3>Sim2Real mismatch</h3>
    <p>Simulation covers the whole wafer but is systematically off. Measurement is correct but covers almost nothing.</p>
  </div>
  <div class="nano-panel">
    <p class="nano-eyebrow">Constraint 03</p>
    <h3>Local measurement bias</h3>
    <p>SEM and TEM see a very narrow field of view, and sampling plans tend to revisit convenient locations.</p>
  </div>
  <div class="nano-panel">
    <p class="nano-eyebrow">Constraint 04</p>
    <h3>Missing process data</h3>
    <p>Process and metrology tables arrive with gaps, so the feature space itself is only partially observed.</p>
  </div>
</div>

NANO reframes the AI Development Lifecycle (AI DLC). Instead of training on the data that happens to
exist, it actively acquires the data needed to understand reality — under a fixed measurement budget.

**Maximize knowledge of reality per measurement.**

## What the agent sees

<WaferComparison />

## The loop

```mermaid
flowchart LR
    A[Observe] --> B[Estimate]
    B --> C[Select]
    C --> D[Measure]
    D --> A
```

<p class="nano-note">Observe &rarr; Estimate &rarr; Select &rarr; Measure &rarr; back to Observe, once per unit of measurement budget.</p>

<AgentLoop />

It does not only predict. It quantifies uncertainty and decides what should be measured next.
That decision — not the interpolation — is the contribution.

## Evidence

<EvidenceStrip />

## Run the experiment yourself

Every number on this site is generated from a single results file in the repository. Nothing is
hand-written into the pages, so if the benchmark has not been run, the site says so.

<div class="nano-panel" style="text-align:center; margin: 1.5rem 0 2.5rem;">
  <p style="margin:0 0 0.9rem;">Clone the repository, run the benchmark, and regenerate every figure on this site.</p>
  <a class="nano-cta" href="./reproducibility">Run the experiment yourself</a>
</div>
