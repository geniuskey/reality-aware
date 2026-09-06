<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    value?: number | string | null
    std?: number | null
    unit?: string
    /** 'down' renders "↓ lower is better"; 'up' renders "↑ higher is better" */
    direction?: 'down' | 'up' | null
    hint?: string
    tone?: 'neutral' | 'primary' | 'observed' | 'uncertain' | 'gap'
    precision?: number
  }>(),
  { tone: 'neutral', precision: 4, direction: null }
)

const hasValue = computed(() => props.value !== null && props.value !== undefined)

const display = computed(() => {
  if (!hasValue.value) return 'not measured'
  if (typeof props.value === 'string') return props.value
  return props.value.toFixed(props.precision)
})

const spread = computed(() =>
  typeof props.std === 'number' ? `± ${props.std.toFixed(props.precision)}` : null
)

const directionText = computed(() => {
  if (props.direction === 'down') return '↓ lower is better'
  if (props.direction === 'up') return '↑ higher is better'
  return null
})
</script>

<template>
  <div class="nano-metric" :data-tone="tone" :data-empty="!hasValue">
    <p class="nano-metric__label">{{ label }}</p>
    <p class="nano-metric__value">
      <span class="nano-metric__number">{{ display }}</span>
      <span v-if="unit && hasValue" class="nano-metric__unit">{{ unit }}</span>
    </p>
    <p v-if="spread" class="nano-metric__spread">{{ spread }}</p>
    <p v-if="directionText" class="nano-metric__dir">{{ directionText }}</p>
    <p v-if="hint" class="nano-metric__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.nano-metric {
  background: var(--nano-surface);
  border: 1px solid var(--nano-border);
  border-left: 3px solid var(--nano-border);
  border-radius: var(--nano-radius);
  padding: 1rem 1.1rem;
}

.nano-metric[data-tone='primary'] { border-left-color: var(--nano-primary); }
.nano-metric[data-tone='observed'] { border-left-color: var(--nano-observed); }
.nano-metric[data-tone='uncertain'] { border-left-color: var(--nano-uncertain); }
.nano-metric[data-tone='gap'] { border-left-color: var(--nano-gap); }

.nano-metric__label {
  margin: 0;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--nano-text-dim);
}

.nano-metric__value {
  margin: 0.4rem 0 0;
  font-family: var(--nano-font-mono);
  font-size: 1.5rem;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
  word-break: break-word;
}

.nano-metric[data-empty='true'] .nano-metric__number {
  font-size: 0.95rem;
  color: var(--nano-uncertain);
}

.nano-metric__unit {
  margin-left: 0.35rem;
  font-size: 0.8rem;
  color: var(--nano-text-dim);
}

.nano-metric__spread,
.nano-metric__dir {
  margin: 0.25rem 0 0;
  font-family: var(--nano-font-mono);
  font-size: 0.78rem;
  color: var(--nano-text-dim);
}

.nano-metric__hint {
  margin: 0.5rem 0 0;
  font-size: 0.82rem;
  color: var(--nano-text-dim);
}
</style>
