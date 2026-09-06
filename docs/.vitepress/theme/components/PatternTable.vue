<script setup lang="ts">
import { computed } from 'vue'
import { data as benchmark } from '../../data/benchmark.data.mts'
import { useStrings } from '../i18n'

const t = useStrings()

/**
 * Per-pattern results, worst first, so the classes where the selection rule
 * earns least are the first thing read rather than the last.
 *
 * The margin column is a difference of means and nothing more. The paired
 * bootstrap on this site runs over all 60 episodes; a pattern class holds five
 * or ten of them, which is too few to separate, so no interval is printed here
 * and none should be inferred.
 */
const view = computed(() => {
  const summary = benchmark.summary
  const strategies = summary?.strategies
  if (!strategies?.nano?.by_pattern) return null

  const patterns = Object.keys(strategies.nano.by_pattern)
  const rows = patterns
    .map((pattern) => {
      const cell = (key: string) => strategies[key]?.by_pattern?.[pattern]?.mean
      const nano = cell('nano')
      const random = cell('random')
      const grid = cell('grid')
      const baselines = [random, grid].filter((v): v is number => typeof v === 'number')
      const best = baselines.length ? Math.min(...baselines) : undefined
      return {
        pattern,
        n: strategies.nano.by_pattern[pattern]?.n,
        nano,
        std: strategies.nano.by_pattern[pattern]?.std,
        random,
        grid,
        margin:
          typeof nano === 'number' && typeof best === 'number' ? best - nano : undefined
      }
    })
    .sort((a, b) => (a.margin ?? 0) - (b.margin ?? 0))

  return {
    rows,
    metric: summary.metric?.name ?? 'error',
    losses: rows.filter((row) => (row.margin ?? 0) <= 0).length
  }
})

const fmt = (v?: number | null, digits = 4) => (typeof v === 'number' ? v.toFixed(digits) : '—')
const signed = (v?: number | null) =>
  typeof v === 'number' ? `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(4)}` : '—'
</script>

<template>
  <div v-if="view">
    <div class="nano-table-scroll">
      <table>
        <caption class="nano-table-caption">{{ t.pattern.caption(view.metric) }}</caption>
        <thead>
          <tr>
            <th scope="col">{{ t.pattern.pattern }}</th>
            <th scope="col">{{ t.pattern.episodes }}</th>
            <th scope="col">NANO</th>
            <th scope="col">Random</th>
            <th scope="col">Grid</th>
            <th scope="col">{{ t.pattern.margin }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in view.rows" :key="row.pattern" :data-loss="(row.margin ?? 0) <= 0">
            <th scope="row">{{ row.pattern }}</th>
            <td class="num">{{ row.n ?? '—' }}</td>
            <td class="num">{{ fmt(row.nano) }}</td>
            <td class="num">{{ fmt(row.random) }}</td>
            <td class="num">{{ fmt(row.grid) }}</td>
            <td class="num" :class="{ 'nano-inconclusive': (row.margin ?? 0) <= 0 }">
              {{ signed(row.margin) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="nano-note">{{ t.pattern.note }}</p>
  </div>

  <div v-else class="nano-empty">
    <span class="nano-tag" data-kind="pending">{{ t.pending }}</span>
    <p>{{ t.pattern.empty }}</p>
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

tbody tr[data-loss='true'] {
  background: var(--vp-c-bg-soft);
}

.nano-inconclusive {
  color: var(--nano-gap);
  font-weight: 600;
}
</style>
