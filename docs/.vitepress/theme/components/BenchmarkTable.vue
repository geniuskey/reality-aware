<script setup lang="ts">
import { computed } from 'vue'
import { data as benchmark } from '../../data/benchmark.data.mts'
import { useStrings } from '../i18n'

const t = useStrings()

/**
 * Final-error table. Same JSON as BenchmarkChart, so the numbers cannot drift
 * apart. Improvements are read from the run's own paired bootstrap rather than
 * recomputed here: a difference of means without its interval is not a result,
 * and an interval that spans zero is printed as "not separated".
 */
const table = computed(() => {
  const summary = benchmark.summary
  if (!summary?.strategies) return null

  const primary = summary.metric?.key ?? 'mae'
  const comparisons = summary.comparisons?.[primary] ?? {}

  const toRow = (key: string, s: any, isReference: boolean) => {
    const c = comparisons[key]
    return {
      key,
      label: s.label ?? key,
      description: s.description,
      mean: s.final?.mean,
      std: s.final?.std,
      isReference,
      comparison: c
        ? {
            separates: c.separates !== false,
            // null when the baseline is exactly zero: an arm can be a fixed
            // amount better than "no error at all", but not a percentage better.
            improvement: typeof c.relative_mean === 'number' ? c.relative_mean : null,
            low: c.relative_ci_low,
            high: c.relative_ci_high,
            delta: c.mean,
            deltaLow: c.ci_low,
            deltaHigh: c.ci_high,
            wins: c.wins,
            n: c.n
          }
        : null
    }
  }

  const rows = [
    ...Object.entries(summary.strategies).map(([key, s]) => toRow(key, s, false)),
    ...Object.entries(summary.references ?? {}).map(([key, s]) => toRow(key, s, true))
  ]

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
    commit: summary.git_commit,
    // A run on stand-in wafers writes a note into the results file. It is
    // printed here rather than dropped, so numbers measured on a stand-in can
    // never be read as numbers measured on the dataset.
    dataset: summary.dataset?.name,
    datasetNote: summary.dataset?.note,
    primary,
    // Every metric the run scored, so a claim that holds on one and fails on
    // another cannot be presented as if it held on both.
    secondary: Object.entries(summary.metrics ?? {})
      .filter(([key]) => key !== primary)
      .map(([key, meta]: [string, any]) => ({
        key,
        name: meta.name ?? key,
        scope: meta.scope,
        cells: rows.map((row) => {
          const stats = (summary.strategies?.[row.key] ?? summary.references?.[row.key])?.metrics?.[
            key
          ]
          const c = summary.comparisons?.[key]?.[row.key]
          return {
            key: row.key,
            mean: stats?.mean,
            separates: c ? c.separates !== false : null,
            improvement: c?.relative_mean
          }
        })
      }))
      .filter((m) => m.cells.some((cell) => typeof cell.mean === 'number'))
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
          {{
            t.table.caption(
              table.metric,
              table.direction,
              String(table.wafers ?? '?'),
              String(table.seeds ?? '?')
            )
          }}
        </caption>
        <thead>
          <tr>
            <th scope="col">{{ t.table.strategy }}</th>
            <th scope="col">{{ t.table.rule }}</th>
            <th scope="col">{{ t.table.mean(table.metric) }} {{ table.direction }}</th>
            <th scope="col">{{ t.table.std }}</th>
            <th scope="col">{{ t.table.improvement }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in table.rows"
            :key="row.key"
            :data-nano="row.key === 'nano'"
            :data-reference="row.isReference"
          >
            <th scope="row">
              {{ row.label }}
              <span v-if="row.isReference" class="nano-ref-tag">{{ t.table.noBudget }}</span>
            </th>
            <td>{{ row.description ?? '—' }}</td>
            <td class="num">{{ fmt(row.mean) }}</td>
            <td class="num">{{ fmt(row.std) }}</td>
            <td class="num">
              <template v-if="!row.comparison">{{ t.table.reference }}</template>
              <template v-else-if="!row.comparison.separates">
                <span class="nano-inconclusive">{{ t.table.notSeparated }}</span>
                <span class="nano-ci">
                  Δ {{ row.comparison.delta > 0 ? '+' : '' }}{{ fmt(row.comparison.delta) }},
                  95% CI [{{ fmt(row.comparison.deltaLow) }}, {{ fmt(row.comparison.deltaHigh) }}],
                  {{ t.table.wins(String(row.comparison.wins), String(row.comparison.n)) }}
                </span>
              </template>
              <template v-else-if="row.comparison.improvement === null">
                {{
                  (row.comparison.delta > 0 ? t.table.better : t.table.worse)(
                    fmt(Math.abs(row.comparison.delta))
                  )
                }}
                <span class="nano-ci">
                  95% CI [{{ fmt(row.comparison.deltaLow) }}, {{ fmt(row.comparison.deltaHigh) }}],
                  {{ t.table.wins(String(row.comparison.wins), String(row.comparison.n)) }}
                </span>
              </template>
              <template v-else>
                {{
                  (row.comparison.improvement > 0 ? t.table.better : t.table.worse)(
                    `${Math.abs(row.comparison.improvement).toFixed(1)}%`
                  )
                }}
                <span class="nano-ci">
                  95% CI [{{ fmt(row.comparison.low, 1) }}%, {{ fmt(row.comparison.high, 1) }}%],
                  {{ t.table.wins(String(row.comparison.wins), String(row.comparison.n)) }}
                </span>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="table.secondary.length" class="nano-table-scroll nano-secondary">
      <table>
        <caption class="nano-table-caption">{{ t.table.secondaryCaption }}</caption>
        <thead>
          <tr>
            <th scope="col">{{ t.table.strategy }}</th>
            <th v-for="metric in table.secondary" :key="metric.key" scope="col">
              {{ metric.name }} ↓
              <span class="nano-scope" v-if="metric.scope">{{ metric.scope }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, index) in table.rows"
            :key="row.key"
            :data-nano="row.key === 'nano'"
            :data-reference="row.isReference"
          >
            <th scope="row">{{ row.label }}</th>
            <td v-for="metric in table.secondary" :key="metric.key" class="num">
              {{ fmt(metric.cells[index].mean) }}
              <span
                v-if="metric.cells[index].separates === false"
                class="nano-inconclusive"
                :title="t.table.notSeparated"
                >*</span
              >
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="nano-note">{{ t.table.secondaryNote }}</p>

    <p v-if="table.datasetNote" class="nano-standin">
      <span class="nano-tag" data-kind="conceptual">{{ t.table.standIn }}</span>
      {{ table.datasetNote }}
    </p>

    <ul class="nano-table-meta">
      <li v-if="table.dataset">{{ t.table.metaDataset }}: <code>{{ table.dataset }}</code></li>
      <li>{{ t.table.metaInitial }}: <code>{{ table.initial ?? '—' }}</code></li>
      <li>{{ t.table.metaBudget }}: <code>{{ table.budget ?? '—' }}</code></li>
      <li v-if="table.prior">
        {{ t.table.metaPrior }}:
        <code>{{ fmt(table.prior.mean) }}</code>
      </li>
      <li v-if="table.commit">{{ t.table.metaCommit }}: <code>{{ table.commit }}</code></li>
      <li v-if="table.generated">{{ t.table.metaGenerated }}: <code>{{ table.generated }}</code></li>
      <li>{{ t.table.metaSource }}: <code>{{ benchmark.sourcePath }}</code></li>
    </ul>
  </div>

  <div v-else class="nano-empty">
    <span class="nano-tag" data-kind="pending">{{ t.pending }}</span>
    <p>
      {{ t.table.emptyLead }}
      <a href="./reproducibility">{{ t.table.emptyLink }}</a> {{ t.table.emptyTail }}
      <code>{{ benchmark.sourcePath }}</code> {{ t.table.emptyTailEnd }}
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

.nano-ci {
  display: block;
  font-size: 0.74rem;
  color: var(--nano-text-dim);
  font-variant-numeric: tabular-nums;
}

.nano-inconclusive {
  color: var(--nano-gap);
  font-weight: 600;
}

.nano-ref-tag {
  display: inline-block;
  margin-left: 0.4rem;
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
  background: var(--vp-c-bg-soft);
  font-size: 0.68rem;
  font-weight: 500;
  color: var(--nano-text-dim);
  vertical-align: middle;
}

tbody tr[data-reference='true'] {
  color: var(--nano-text-dim);
}

.nano-secondary {
  margin-top: 1.75rem;
}

.nano-scope {
  display: block;
  font-size: 0.7rem;
  font-weight: 400;
  color: var(--nano-text-dim);
}

.nano-standin {
  margin: 0.25rem 0 0.75rem;
  padding: 0.7rem 0.9rem;
  border-left: 3px solid var(--nano-gap);
  background: var(--vp-c-bg-soft);
  font-size: 0.85rem;
  line-height: 1.55;
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
