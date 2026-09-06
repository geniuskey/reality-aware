<script setup lang="ts">
import { computed } from 'vue'
import { data as benchmark } from '../../data/benchmark.data.mts'

/**
 * Final-error table. Same JSON as BenchmarkChart, so the numbers cannot drift
 * apart. Relative improvement is computed here, never hardcoded in Markdown.
 */
const table = computed(() => {
  const summary = benchmark.summary
  if (!summary?.strategies) return null

  const entries = Object.entries(summary.strategies)
  const nano = summary.strategies.nano

  const rows = entries.map(([key, s]) => {
    const improvement =
      key === 'nano' || !nano || !s.final?.mean
        ? null
        : ((s.final.mean - nano.final.mean) / s.final.mean) * 100
    return {
      key,
      label: s.label ?? key,
      description: s.description,
      mean: s.final?.mean,
      std: s.final?.std,
      improvement
    }
  })

  const exp = summary.experiment ?? {}
  return {
    rows,
    metric: summary.metric?.name ?? 'error',
    direction: summary.metric?.direction === 'higher_is_better' ? '↑' : '↓',
    unit: summary.metric?.unit,
    wafers: summary.dataset?.n_wafers,
    seeds: exp.seeds?.length,
    initial: exp.initial_measurements,
    budget: exp.measurement_budget,
    prior: summary.prior?.initial_error,
    generated: summary.generated_at,
    commit: summary.git_commit
  }
})

const fmt = (v?: number | null, digits = 4) =>
  typeof v === 'number' ? v.toFixed(digits) : '—'
</script>

<template>
  <div v-if="table">
    <div class="nano-table-scroll">
      <table>
        <caption class="nano-table-caption">
          Final reconstruction {{ table.metric }} {{ table.direction }} after the full measurement
          budget, averaged over {{ table.wafers ?? '?' }} wafers &times; {{ table.seeds ?? '?' }} seeds.
          All strategies start from the same initial observations and spend the same budget.
        </caption>
        <thead>
          <tr>
            <th scope="col">Strategy</th>
            <th scope="col">Selection rule</th>
            <th scope="col">{{ table.metric }} mean {{ table.direction }}</th>
            <th scope="col">&plusmn; std</th>
            <th scope="col">Improvement vs NANO</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in table.rows" :key="row.key" :data-nano="row.key === 'nano'">
            <th scope="row">{{ row.label }}</th>
            <td>{{ row.description ?? '—' }}</td>
            <td class="num">{{ fmt(row.mean) }}</td>
            <td class="num">{{ fmt(row.std) }}</td>
            <td class="num">
              <template v-if="row.improvement === null">reference</template>
              <template v-else>
                {{ row.improvement > 0 ? 'NANO better by ' : 'NANO worse by ' }}
                {{ Math.abs(row.improvement).toFixed(1) }}%
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <ul class="nano-table-meta">
      <li>Initial measurements: <code>{{ table.initial ?? '—' }}</code></li>
      <li>Additional measurement budget: <code>{{ table.budget ?? '—' }}</code></li>
      <li v-if="table.prior">
        Simulation prior error before any correction:
        <code>{{ fmt(table.prior.mean) }}</code>
      </li>
      <li v-if="table.commit">Commit: <code>{{ table.commit }}</code></li>
      <li v-if="table.generated">Generated: <code>{{ table.generated }}</code></li>
      <li>Source: <code>{{ benchmark.sourcePath }}</code></li>
    </ul>
  </div>

  <div v-else class="nano-empty">
    <span class="nano-tag" data-kind="pending">Run benchmark to generate results</span>
    <p>
      No results table yet. Run the benchmark described on the
      <a href="./reproducibility">Reproduce</a> page; it writes
      <code>{{ benchmark.sourcePath }}</code> and this table fills itself in.
    </p>
  </div>
</template>

<style scoped>
.nano-table-scroll {
  overflow-x: auto;
  margin: 1.5rem 0 0.75rem;
}

table {
  width: 100%;
  border-collapse: collapse;
}

.nano-table-caption {
  caption-side: bottom;
  margin-top: 0.75rem;
  text-align: left;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--nano-text-dim);
}

th,
td {
  border: 1px solid var(--nano-border);
  padding: 0.55rem 0.75rem;
  text-align: left;
  font-size: 0.9rem;
}

thead th {
  font-size: 0.75rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--nano-text-dim);
  background: var(--nano-surface-2);
}

tbody th {
  white-space: nowrap;
  background: var(--nano-surface);
}

tr[data-nano='true'] th,
tr[data-nano='true'] td {
  background: var(--nano-primary-soft);
}

.num {
  font-family: var(--nano-font-mono);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.nano-table-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 1.25rem;
  padding: 0;
  margin: 0 0 1.5rem;
  list-style: none;
  font-size: 0.8rem;
  color: var(--nano-text-dim);
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
