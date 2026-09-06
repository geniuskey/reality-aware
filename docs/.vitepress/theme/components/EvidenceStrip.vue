<script setup lang="ts">
import { computed } from 'vue'
import { data as benchmark } from '../../data/benchmark.data.mts'
import MetricCard from './MetricCard.vue'

/** Home-page evidence row. Same JSON as the benchmark page - one source, no drift. */
const view = computed(() => {
  const summary = benchmark.summary
  if (!summary?.strategies?.nano) return null

  const s = summary.strategies
  const nano = s.nano.final?.mean
  const random = s.random?.final?.mean
  const prior = summary.prior?.initial_error?.mean

  return {
    metric: summary.metric?.name ?? 'error',
    unit: summary.metric?.unit,
    nano,
    nanoStd: s.nano.final?.std ?? null,
    random,
    randomStd: s.random?.final?.std ?? null,
    grid: s.grid?.final?.mean,
    gridStd: s.grid?.final?.std ?? null,
    prior,
    priorDrop:
      typeof prior === 'number' && typeof nano === 'number' && prior > 0
        ? ((prior - nano) / prior) * 100
        : null,
    wafers: summary.dataset?.n_wafers,
    seeds: summary.experiment?.seeds?.length,
    budget: summary.experiment?.measurement_budget
  }
})
</script>

<template>
  <section v-if="view" class="nano-evidence">
    <div class="nano-grid" data-cols="4">
      <MetricCard
        label="NANO"
        :value="view.nano"
        :std="view.nanoStd"
        :unit="view.unit"
        direction="down"
        tone="primary"
        :hint="`Final ${view.metric} after the full budget`"
      />
      <MetricCard
        label="Random baseline"
        :value="view.random"
        :std="view.randomStd"
        :unit="view.unit"
        direction="down"
        hint="Same budget, same initial observations"
      />
      <MetricCard
        label="Grid baseline"
        :value="view.grid"
        :std="view.gridStd"
        :unit="view.unit"
        direction="down"
        hint="Spatially uniform selection"
      />
      <MetricCard
        label="Prior error removed"
        :value="view.priorDrop !== null ? `${view.priorDrop.toFixed(1)}%` : null"
        tone="observed"
        hint="Biased simulation prior vs corrected estimate"
      />
    </div>
    <p class="nano-note">
      {{ view.wafers ?? '?' }} wafers &times; {{ view.seeds ?? '?' }} seeds &middot; measurement
      budget {{ view.budget ?? '?' }} &middot; {{ view.metric }} &darr; lower is better &middot;
      generated from <code>{{ benchmark.sourcePath }}</code>.
      <a href="./benchmark">Full results &rarr;</a>
    </p>
  </section>

  <section v-else class="nano-empty">
    <span class="nano-tag" data-kind="pending">Run benchmark to generate results</span>
    <p>
      This repository ships no pre-baked numbers. Once the benchmark writes
      <code>{{ benchmark.sourcePath }}</code>, the headline metrics, the results table and the error
      curve all render from that one file.
    </p>
    <p class="nano-note">
      Until then the honest answer is: unverified. See
      <a href="./reproducibility">Reproduce</a> for how to produce the evidence.
    </p>
  </section>
</template>

<style scoped>
.nano-evidence {
  margin: 1.5rem 0;
}

.nano-empty {
  background: var(--nano-surface);
  border: 1px dashed var(--nano-border);
  border-radius: var(--nano-radius);
  padding: 1.25rem;
  margin: 1.75rem 0;
}

.nano-empty p {
  margin: 0.7rem 0 0;
  font-size: 0.9rem;
  color: var(--nano-text-dim);
}
</style>
