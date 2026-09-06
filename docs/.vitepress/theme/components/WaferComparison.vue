<script setup lang="ts">
import { computed } from 'vue'

/**
 * Four-panel wafer story.
 *
 * When real experiment assets exist, pass them via `images` and this component
 * renders those instead. With no assets it draws a deterministic *conceptual*
 * illustration and labels it as such - it is never presented as benchmark data.
 */
const props = withDefaults(
  defineProps<{
    images?: { src: string; title: string; caption: string }[]
    grid?: number
    seed?: number
  }>(),
  { grid: 17, seed: 20260906 }
)

const useImages = computed(() => !!props.images?.length)

/* ---- deterministic field generation (identical on server and client) ---- */

function mulberry32(a: number) {
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function clamp01(v: number) {
  return v < 0 ? 0 : v > 1 ? 1 : v
}

type Cell = {
  x: number
  y: number
  reality: number
  prior: number
  prediction: number
  uncertainty: number
  observed: boolean
}

const model = computed(() => {
  const n = props.grid
  const rand = mulberry32(props.seed)
  const c = (n - 1) / 2
  const radius = c + 0.35

  const cells: Cell[] = []
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const r = Math.hypot(x - c, y - c) / radius
      if (r > 1) continue
      const theta = Math.atan2(y - c, x - c)
      // Reality: edge-heavy ring plus a mild azimuthal lobe and light noise.
      const reality = clamp01(
        0.18 + 0.62 * Math.pow(r, 2.2) + 0.14 * Math.sin(theta * 2 + 0.6) * r + 0.06 * (rand() - 0.5)
      )
      // Prior: deliberately biased - it under-predicts the wafer edge.
      const prior = clamp01(0.34 + 0.28 * r - 0.1 * Math.sin(theta * 2 + 0.6) * r)
      cells.push({ x, y, reality, prior, prediction: prior, uncertainty: 1, observed: false })
    }
  }

  // Sparse observation set: centre-biased sampling, the classic spatial bias.
  const budget = Math.max(10, Math.round(cells.length * 0.045))
  const pool = [...cells]
  for (let i = 0; i < budget && pool.length; i++) {
    let best = 0
    let bestScore = -Infinity
    for (let k = 0; k < 6 && pool.length; k++) {
      const idx = Math.floor(rand() * pool.length)
      const cand = pool[idx]
      const score = -Math.hypot(cand.x - c, cand.y - c) / radius + rand() * 0.8
      if (score > bestScore) {
        bestScore = score
        best = idx
      }
    }
    pool[best].observed = true
    pool.splice(best, 1)
  }

  const observed = cells.filter((cell) => cell.observed)

  // Prediction: prior corrected towards nearby observations. Uncertainty grows
  // with distance from the nearest measurement.
  for (const cell of cells) {
    let wSum = 0
    let vSum = 0
    let nearest = Infinity
    for (const o of observed) {
      const d = Math.hypot(cell.x - o.x, cell.y - o.y)
      if (d < nearest) nearest = d
      const w = 1 / (1 + Math.pow(d, 2.4))
      wSum += w
      vSum += w * o.reality
    }
    const trust = wSum / (wSum + 0.35)
    cell.prediction = clamp01(trust * (vSum / Math.max(wSum, 1e-9)) + (1 - trust) * cell.prior)
    cell.uncertainty = cell.observed ? 0 : clamp01(nearest / (radius * 0.9))
  }

  // Acquisition: uncertainty x prior-vs-prediction disagreement.
  let next = cells[0]
  let bestAcq = -Infinity
  for (const cell of cells) {
    if (cell.observed) continue
    const acq = cell.uncertainty * (0.25 + Math.abs(cell.prior - cell.prediction))
    if (acq > bestAcq) {
      bestAcq = acq
      next = cell
    }
  }

  return { cells, observed, next }
})

/* ---- colour ramps: prediction and uncertainty never share a scale ------- */

function ramp(stops: [number, number, number][], t: number) {
  const v = clamp01(t) * (stops.length - 1)
  const i = Math.min(Math.floor(v), stops.length - 2)
  const f = v - i
  const a = stops[i]
  const b = stops[i + 1]
  const mix = (p: number, q: number) => Math.round(p + (q - p) * f)
  return `rgb(${mix(a[0], b[0])} ${mix(a[1], b[1])} ${mix(a[2], b[2])})`
}

const violet = (t: number) =>
  ramp([[226, 222, 246], [156, 141, 224], [92, 74, 168], [46, 33, 102]], t)
const cyan = (t: number) =>
  ramp([[214, 238, 241], [110, 200, 214], [23, 138, 156], [8, 66, 80]], t)
const amber = (t: number) =>
  ramp([[245, 238, 222], [232, 198, 122], [196, 141, 26], [110, 74, 8]], t)

const cellSize = computed(() => 100 / props.grid)
const px = (i: number) => i * cellSize.value
</script>

<template>
  <section class="nano-wafer" aria-labelledby="nano-wafer-heading">
    <header class="nano-wafer__head">
      <h2 id="nano-wafer-heading" class="nano-wafer__title">One wafer, four states</h2>
      <span v-if="!useImages" class="nano-tag" data-kind="conceptual">Conceptual illustration</span>
    </header>

    <!-- Real experiment assets, once the benchmark has produced them. -->
    <div v-if="useImages" class="nano-wafer__panels">
      <figure v-for="panel in props.images" :key="panel.src" class="nano-wafer__panel">
        <img :src="panel.src" :alt="panel.caption" loading="lazy" />
        <figcaption>
          <strong>{{ panel.title }}</strong>
          <span>{{ panel.caption }}</span>
        </figcaption>
      </figure>
    </div>

    <!-- Conceptual fallback: deterministic, schematic, clearly labelled. -->
    <div v-else class="nano-wafer__panels">
      <figure class="nano-wafer__panel">
        <svg
          viewBox="-3 -3 106 106"
          role="img"
          aria-label="Biased simulation prior across the wafer: smooth everywhere and under-predicting the wafer edge."
        >
          <rect class="nano-wafer__bg" x="0" y="0" width="100" height="100" />
          <rect
            v-for="cell in model.cells"
            :key="`p-${cell.x}-${cell.y}`"
            :x="px(cell.x)"
            :y="px(cell.y)"
            :width="cellSize"
            :height="cellSize"
            :fill="violet(cell.prior)"
            class="nano-wafer__die"
          />
        </svg>
        <figcaption>
          <strong>1 · Biased Simulation Prior</strong>
          <span>Smooth and confident everywhere. It under-predicts the wafer edge.</span>
        </figcaption>
      </figure>

      <figure class="nano-wafer__panel">
        <svg
          viewBox="-3 -3 106 106"
          role="img"
          aria-label="Sparse measurements: a small number of measured dies, clustered near the wafer centre."
        >
          <rect class="nano-wafer__bg" x="0" y="0" width="100" height="100" />
          <rect
            v-for="cell in model.cells"
            :key="`m-${cell.x}-${cell.y}`"
            :x="px(cell.x)"
            :y="px(cell.y)"
            :width="cellSize"
            :height="cellSize"
            class="nano-wafer__die"
            :class="{ 'is-empty': !cell.observed }"
            :fill="cell.observed ? 'rgb(31 138 91)' : 'none'"
          />
          <circle
            v-for="cell in model.observed"
            :key="`mk-${cell.x}-${cell.y}`"
            :cx="px(cell.x) + cellSize / 2"
            :cy="px(cell.y) + cellSize / 2"
            :r="cellSize * 0.16"
            fill="#ffffff"
          />
        </svg>
        <figcaption>
          <strong>2 · Sparse Measurements</strong>
          <span>
            {{ model.observed.length }} of {{ model.cells.length }} dies measured, and the sample is
            centre-biased.
          </span>
        </figcaption>
      </figure>

      <figure class="nano-wafer__panel">
        <svg
          viewBox="-3 -3 106 106"
          role="img"
          aria-label="Predicted reality: the prior corrected towards the measurements, sharpening near the wafer edge."
        >
          <rect class="nano-wafer__bg" x="0" y="0" width="100" height="100" />
          <rect
            v-for="cell in model.cells"
            :key="`pr-${cell.x}-${cell.y}`"
            :x="px(cell.x)"
            :y="px(cell.y)"
            :width="cellSize"
            :height="cellSize"
            :fill="cyan(cell.prediction)"
            class="nano-wafer__die"
          />
          <rect
            v-for="cell in model.observed"
            :key="`pro-${cell.x}-${cell.y}`"
            :x="px(cell.x) + cellSize * 0.15"
            :y="px(cell.y) + cellSize * 0.15"
            :width="cellSize * 0.7"
            :height="cellSize * 0.7"
            fill="none"
            stroke="#ffffff"
            stroke-width="0.5"
          />
        </svg>
        <figcaption>
          <strong>3 · Predicted Reality</strong>
          <span>Prior pulled towards measured evidence. White outlines mark measured dies.</span>
        </figcaption>
      </figure>

      <figure class="nano-wafer__panel">
        <svg
          viewBox="-3 -3 106 106"
          role="img"
          aria-label="Uncertainty map with the recommended next die marked by a crosshair in the least-known region."
        >
          <rect class="nano-wafer__bg" x="0" y="0" width="100" height="100" />
          <rect
            v-for="cell in model.cells"
            :key="`u-${cell.x}-${cell.y}`"
            :x="px(cell.x)"
            :y="px(cell.y)"
            :width="cellSize"
            :height="cellSize"
            :fill="amber(cell.uncertainty)"
            class="nano-wafer__die"
          />
          <g
            :transform="`translate(${px(model.next.x) + cellSize / 2} ${px(model.next.y) + cellSize / 2})`"
            stroke="rgb(192 57 43)"
            stroke-width="0.9"
            fill="none"
          >
            <circle :r="cellSize * 0.62" />
            <line :x1="-cellSize" :x2="cellSize" y1="0" y2="0" />
            <line x1="0" x2="0" :y1="-cellSize" :y2="cellSize" />
          </g>
        </svg>
        <figcaption>
          <strong>4 · Recommended Next Die</strong>
          <span>Highest acquisition score: unknown <em>and</em> in disagreement with the prior.</span>
        </figcaption>
      </figure>
    </div>

    <ul v-if="!useImages" class="nano-wafer__legend">
      <li><span class="swatch" data-s="observed">&#9679;</span> Measured die (observed)</li>
      <li><span class="swatch" data-s="unobserved">&#9675;</span> Unmeasured die (hidden from agent)</li>
      <li><span class="swatch" data-s="prior">&#9638;</span> Prior scale &middot; violet, low &rarr; high</li>
      <li><span class="swatch" data-s="pred">&#9638;</span> Prediction scale &middot; cyan, low &rarr; high</li>
      <li><span class="swatch" data-s="unc">&#9638;</span> Uncertainty scale &middot; amber, certain &rarr; unknown</li>
      <li><span class="swatch" data-s="next">&#10011;</span> Recommended next measurement</li>
    </ul>

    <p v-if="!useImages" class="nano-note">
      Schematic only. These fields come from a deterministic formula inside this page, written to
      explain the loop. They are not WM-811K wafers and not benchmark output.
    </p>
  </section>
</template>

<style scoped>
.nano-wafer {
  margin: 2rem 0;
}

.nano-wafer__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.nano-wafer__title {
  margin: 0;
  font-size: 1.05rem;
  border: 0;
  padding: 0;
}

.nano-wafer__panels {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.85rem;
}

.nano-wafer__panel {
  margin: 0;
  background: var(--nano-surface);
  border: 1px solid var(--nano-border);
  border-radius: var(--nano-radius);
  padding: 0.6rem;
}

.nano-wafer__panel svg,
.nano-wafer__panel img {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 6px;
}

.nano-wafer__bg {
  fill: var(--nano-surface-2);
}

.nano-wafer__die {
  stroke: var(--nano-border);
  stroke-width: 0.15;
}

.nano-wafer__die.is-empty {
  fill: var(--nano-surface-2);
}

.nano-wafer__panel figcaption {
  display: block;
  margin-top: 0.55rem;
  font-size: 0.78rem;
  line-height: 1.45;
  color: var(--nano-text-dim);
}

.nano-wafer__panel figcaption strong {
  display: block;
  color: var(--nano-text);
  font-size: 0.8rem;
  margin-bottom: 0.15rem;
}

.nano-wafer__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
  margin: 1rem 0 0.75rem;
  padding: 0;
  list-style: none;
  font-size: 0.78rem;
  color: var(--nano-text-dim);
}

.nano-wafer__legend .swatch {
  font-family: var(--nano-font-mono);
  margin-right: 0.3rem;
}

.swatch[data-s='observed'] { color: var(--nano-observed); }
.swatch[data-s='unobserved'] { color: var(--nano-text-dim); }
.swatch[data-s='prior'] { color: var(--nano-secondary); }
.swatch[data-s='pred'] { color: var(--nano-primary); }
.swatch[data-s='unc'] { color: var(--nano-uncertain); }
.swatch[data-s='next'] { color: var(--nano-gap); }

@media (max-width: 960px) {
  .nano-wafer__panels { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 520px) {
  .nano-wafer__panels { grid-template-columns: minmax(0, 1fr); }
}
</style>
