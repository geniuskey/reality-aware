<script setup lang="ts">
import { computed } from 'vue'
import { data as benchmark } from '../../data/benchmark.data.mts'
import { useStrings } from '../i18n'

const t = useStrings()

/**
 * What each term of the acquisition product is worth, measured rather than
 * asserted. Every ablation arm ran through the same loop, the same budget and
 * the same initial mask as the published rule; only the terms differ.
 */
const view = computed(() => {
  const summary = benchmark.summary
  const ablation = summary?.ablation
  if (!summary || !ablation || !Object.keys(ablation).length) return null

  const primary = summary.metric?.key ?? 'mae'
  const comparisons = summary.comparisons?.[primary] ?? {}
  const full = summary.strategies?.nano

  const rows = Object.entries(ablation).map(([key, arm]: [string, any]) => {
    const c = comparisons[key]
    return {
      key,
      rule: (arm.rule ?? key).replace(/ x /g, ' × '),
      mean: arm.final?.mean,
      std: arm.final?.std,
      // A negative delta means the reduced rule beat the full one: the dropped
      // term was costing accuracy, not buying it.
      verdict: c
        ? {
            separates: c.separates !== false,
            better: c.mean > 0,
            improvement: typeof c.relative_mean === 'number' ? c.relative_mean : null,
            low: c.relative_ci_low,
            high: c.relative_ci_high,
            // `wins` in the results file counts the episodes NANO won, so the
            // reduced rule's own win count is the mirror of it.
            wins: c.losses,
            n: c.n
          }
        : null
    }
  })

  return {
    rows,
    metric: summary.metric?.name ?? 'error',
    fullRule: (summary.experiment?.acquisition_rule ?? '').replace(/ x /g, ' × '),
    fullMean: full?.final?.mean,
    fullStd: full?.final?.std
  }
})

const fmt = (v?: number | null, digits = 4) => (typeof v === 'number' ? v.toFixed(digits) : '—')
</script>

<template>
  <div v-if="view">
    <div class="nano-table-scroll">
      <table>
        <caption class="nano-table-caption">{{ t.ablation.caption(view.metric) }}</caption>
        <thead>
          <tr>
            <th scope="col">{{ t.ablation.rule }}</th>
            <th scope="col">{{ view.metric }} ↓</th>
            <th scope="col">{{ t.ablation.std }}</th>
            <th scope="col">{{ t.ablation.verdict }}</th>
          </tr>
        </thead>
        <tbody>
          <tr data-nano="true">
            <th scope="row">{{ view.fullRule }} <span class="nano-ref-tag">{{ t.ablation.published }}</span></th>
            <td class="num">{{ fmt(view.fullMean) }}</td>
            <td class="num">{{ fmt(view.fullStd) }}</td>
            <td class="num">{{ t.ablation.reference }}</td>
          </tr>
          <tr v-for="row in view.rows" :key="row.key">
            <th scope="row">{{ row.rule }}</th>
            <td class="num">{{ fmt(row.mean) }}</td>
            <td class="num">{{ fmt(row.std) }}</td>
            <td class="num">
              <template v-if="!row.verdict">—</template>
              <template v-else-if="!row.verdict.separates">
                {{ t.ablation.notSeparated }}
                <span class="nano-ci">
                  {{ t.ablation.wins(String(row.verdict.wins), String(row.verdict.n)) }}
                </span>
              </template>
              <template v-else-if="row.verdict.better">
                {{ t.ablation.worse(fmt(Math.abs(row.verdict.improvement ?? 0), 1) + '%') }}
                <span class="nano-ci">
                  {{ t.ablation.wins(String(row.verdict.wins), String(row.verdict.n)) }}
                </span>
              </template>
              <template v-else>
                <span class="nano-inconclusive">
                  {{ t.ablation.better(fmt(Math.abs(row.verdict.improvement ?? 0), 1) + '%') }}
                </span>
                <span class="nano-ci">
                  {{ t.ablation.wins(String(row.verdict.wins), String(row.verdict.n)) }}
                </span>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="nano-note">{{ t.ablation.note }}</p>
  </div>

  <div v-else class="nano-empty">
    <span class="nano-tag" data-kind="pending">{{ t.pending }}</span>
    <p>{{ t.ablation.emptyLead }} <code>python -m nano.benchmark --ablation</code>{{ t.ablation.emptyTail }}</p>
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
  padding: 0.55rem 0.7rem;
  border-bottom: 1px solid var(--vp-c-divider);
  text-align: left;
  font-size: 0.88rem;
}

.num {
  font-variant-numeric: tabular-nums;
}

tbody tr[data-nano='true'] {
  background: var(--vp-c-bg-soft);
  font-weight: 600;
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
  background: var(--vp-c-bg-alt);
  font-size: 0.68rem;
  font-weight: 500;
  color: var(--nano-text-dim);
  vertical-align: middle;
}
</style>
