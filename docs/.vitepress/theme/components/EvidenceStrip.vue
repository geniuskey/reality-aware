<script setup lang="ts">
import { computed } from 'vue'
import { data as benchmark } from '../../data/benchmark.data.mts'
import MetricCard from './MetricCard.vue'
import { useStrings } from '../i18n'

const t = useStrings()

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
        :label="t.evidence.nano"
        :value="view.nano"
        :std="view.nanoStd"
        :unit="view.unit"
        direction="down"
        tone="primary"
        :hint="t.evidence.nanoHint(view.metric)"
      />
      <MetricCard
        :label="t.evidence.random"
        :value="view.random"
        :std="view.randomStd"
        :unit="view.unit"
        direction="down"
        :hint="t.evidence.randomHint"
      />
      <MetricCard
        :label="t.evidence.grid"
        :value="view.grid"
        :std="view.gridStd"
        :unit="view.unit"
        direction="down"
        :hint="t.evidence.gridHint"
      />
      <MetricCard
        :label="t.evidence.priorDrop"
        :value="view.priorDrop !== null ? `${view.priorDrop.toFixed(1)}%` : null"
        tone="observed"
        :hint="t.evidence.priorDropHint"
      />
    </div>
    <p class="nano-note">
      {{
        t.evidence.footnote(
          String(view.wafers ?? '?'),
          String(view.seeds ?? '?'),
          String(view.budget ?? '?'),
          view.metric
        )
      }}
      <code>{{ benchmark.sourcePath }}</code>.
      <a href="./benchmark">{{ t.evidence.fullResults }}</a>
    </p>
  </section>

  <section v-else class="nano-empty">
    <span class="nano-tag" data-kind="pending">{{ t.pending }}</span>
    <p>
      {{ t.evidence.emptyLead }}
      <code>{{ benchmark.sourcePath }}</code> {{ t.evidence.emptyTail }}
    </p>
    <p class="nano-note">
      {{ t.evidence.emptyNote }}
      <a href="./reproducibility">{{ t.evidence.emptyNoteLink }}</a>
      {{ t.evidence.emptyNoteTail }}
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
