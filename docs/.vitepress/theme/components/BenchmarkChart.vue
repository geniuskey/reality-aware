<script setup lang="ts">
import { computed } from 'vue'
import { data as benchmark } from '../../data/benchmark.data.mts'

/**
 * Measurements vs reconstruction error, drawn from results/benchmark_summary.json.
 * The y-axis always starts at zero so differences are never visually exaggerated.
 */
const props = withDefaults(defineProps<{ height?: number }>(), { height: 300 })

const W = 720
const PAD = { top: 18, right: 132, bottom: 46, left: 62 }

const strategyTone: Record<string, string> = {
  nano: 'var(--nano-primary)',
  random: 'var(--nano-text-dim)',
  grid: 'var(--nano-secondary)'
}

const strategyDash: Record<string, string> = {
  nano: '0',
  random: '5 4',
  grid: '2 3'
}

const chart = computed(() => {
  const summary = benchmark.summary
  if (!summary?.strategies) return null

  const series = Object.entries(summary.strategies)
    .map(([key, s]) => ({
      key,
      label: s.label ?? key,
      points: (s.curve ?? []).slice().sort((a, b) => a.measurements - b.measurements)
    }))
    .filter((s) => s.points.length > 1)

  if (!series.length) return null

  const xs = series.flatMap((s) => s.points.map((p) => p.measurements))
  const ys = series.flatMap((s) => s.points.map((p) => p.mean + (p.std ?? 0)))
  const xMin = Math.min(...xs)
  const xMax = Math.max(...xs)
  const yMax = Math.max(...ys) * 1.08
  const H = props.height

  const sx = (v: number) =>
    PAD.left + ((v - xMin) / Math.max(xMax - xMin, 1e-9)) * (W - PAD.left - PAD.right)
  const sy = (v: number) => H - PAD.bottom - (v / Math.max(yMax, 1e-9)) * (H - PAD.top - PAD.bottom)

  const line = (pts: { measurements: number; mean: number }[]) =>
    pts.map((p, i) => `${i ? 'L' : 'M'}${sx(p.measurements).toFixed(2)} ${sy(p.mean).toFixed(2)}`).join(' ')

  const band = (pts: { measurements: number; mean: number; std?: number }[]) => {
    if (!pts.some((p) => typeof p.std === 'number')) return null
    const up = pts.map((p) => `${sx(p.measurements).toFixed(2)} ${sy(p.mean + (p.std ?? 0)).toFixed(2)}`)
    const down = [...pts]
      .reverse()
      .map((p) => `${sx(p.measurements).toFixed(2)} ${sy(Math.max(p.mean - (p.std ?? 0), 0)).toFixed(2)}`)
    return `M${up.join(' L')} L${down.join(' L')} Z`
  }

  const yTicks = Array.from({ length: 5 }, (_, i) => (yMax / 4) * i)
  const xTicks = Array.from({ length: 5 }, (_, i) => xMin + ((xMax - xMin) / 4) * i)

  return {
    H,
    series: series.map((s) => ({ ...s, d: line(s.points), band: band(s.points) })),
    yTicks: yTicks.map((v) => ({ v, y: sy(v) })),
    xTicks: xTicks.map((v) => ({ v, x: sx(v) })),
    metric: summary.metric?.name ?? 'error',
    direction: summary.metric?.direction === 'higher_is_better' ? '↑' : '↓',
    unit: summary.metric?.unit
  }
})
</script>

<template>
  <figure v-if="chart" class="nano-figure nano-chart">
    <svg
      :viewBox="`0 0 ${W} ${chart.H}`"
      role="img"
      :aria-label="`Reconstruction ${chart.metric} against the number of measurements for each selection strategy. Lower is better.`"
    >
      <g class="nano-chart__grid">
        <line
          v-for="tick in chart.yTicks"
          :key="`gy-${tick.v}`"
          :x1="PAD.left"
          :x2="W - PAD.right"
          :y1="tick.y"
          :y2="tick.y"
        />
      </g>

      <g class="nano-chart__axis">
        <line :x1="PAD.left" :x2="PAD.left" :y1="PAD.top" :y2="chart.H - PAD.bottom" />
        <line
          :x1="PAD.left"
          :x2="W - PAD.right"
          :y1="chart.H - PAD.bottom"
          :y2="chart.H - PAD.bottom"
        />
      </g>

      <g class="nano-chart__labels">
        <text
          v-for="tick in chart.yTicks"
          :key="`ty-${tick.v}`"
          :x="PAD.left - 10"
          :y="tick.y + 4"
          text-anchor="end"
        >
          {{ tick.v.toFixed(3) }}
        </text>
        <text
          v-for="tick in chart.xTicks"
          :key="`tx-${tick.v}`"
          :x="tick.x"
          :y="chart.H - PAD.bottom + 20"
          text-anchor="middle"
        >
          {{ Math.round(tick.v) }}
        </text>
        <text :x="PAD.left" :y="chart.H - 8" text-anchor="start" class="nano-chart__axis-title">
          Measurements used
        </text>
        <text
          :x="-(chart.H / 2)"
          y="16"
          transform="rotate(-90)"
          text-anchor="middle"
          class="nano-chart__axis-title"
        >
          {{ chart.metric }} {{ chart.direction }}{{ chart.unit ? ` (${chart.unit})` : '' }}
        </text>
      </g>

      <g v-for="s in chart.series" :key="s.key">
        <path
          v-if="s.band"
          :d="s.band"
          :fill="strategyTone[s.key] ?? 'var(--nano-text-dim)'"
          opacity="0.12"
        />
        <path
          :d="s.d"
          fill="none"
          :stroke="strategyTone[s.key] ?? 'var(--nano-text-dim)'"
          :stroke-dasharray="strategyDash[s.key] ?? '0'"
          stroke-width="2.2"
          stroke-linejoin="round"
        />
      </g>

      <g class="nano-chart__legend">
        <g v-for="(s, i) in chart.series" :key="`l-${s.key}`" :transform="`translate(${W - PAD.right + 16} ${PAD.top + 8 + i * 22})`">
          <line
            x1="0"
            x2="22"
            y1="0"
            y2="0"
            :stroke="strategyTone[s.key] ?? 'var(--nano-text-dim)'"
            :stroke-dasharray="strategyDash[s.key] ?? '0'"
            stroke-width="2.2"
          />
          <text x="28" y="4">{{ s.label }}</text>
        </g>
      </g>
    </svg>
    <figcaption>
      Reconstruction {{ chart.metric }} {{ chart.direction }} against measurement count. Shaded bands
      show &plusmn;1 standard deviation across seeds. The y-axis starts at zero. Generated from
      <code>{{ benchmark.sourcePath }}</code>.
    </figcaption>
  </figure>

  <div v-else class="nano-empty">
    <span class="nano-tag" data-kind="pending">Run benchmark to generate results</span>
    <p>
      No error curve yet. This chart renders once
      <code>{{ benchmark.sourcePath }}</code> contains per-strategy <code>curve</code> arrays.
    </p>
    <p class="nano-note">
      The site deliberately ships with no placeholder numbers, so nothing here can be mistaken for a
      measured result.
    </p>
  </div>
</template>

<style scoped>
.nano-chart svg {
  display: block;
  width: 100%;
  height: auto;
  background: var(--nano-surface);
  border: 1px solid var(--nano-border);
  border-radius: var(--nano-radius);
}

.nano-chart__grid line {
  stroke: var(--nano-border);
  stroke-width: 1;
}

.nano-chart__axis line {
  stroke: var(--nano-text-dim);
  stroke-width: 1;
}

.nano-chart__labels text,
.nano-chart__legend text {
  font-family: var(--nano-font-mono);
  font-size: 11px;
  fill: var(--nano-text-dim);
}

.nano-chart__axis-title {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
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
