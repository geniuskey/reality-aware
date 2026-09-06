<script setup lang="ts">
import { computed } from 'vue'
import { useStrings } from '../i18n'

const t = useStrings()

const tones = ['observed', 'primary', 'uncertain', 'gap'] as const

const steps = computed(() =>
  t.value.loop.steps.map((step, i) => ({
    id: tones[i],
    n: String(i + 1).padStart(2, '0'),
    tone: tones[i],
    name: step.name,
    text: step.text
  }))
)
</script>

<template>
  <div class="nano-loop">
    <ol class="nano-loop__list">
      <li v-for="step in steps" :key="step.id" class="nano-loop__step" :data-tone="step.tone">
        <span class="nano-loop__n">{{ step.n }}</span>
        <h3 class="nano-loop__name">{{ step.name }}</h3>
        <p class="nano-loop__text">{{ step.text }}</p>
      </li>
    </ol>
    <p class="nano-loop__cycle">
      <span aria-hidden="true">↻</span>
      {{ t.loop.cycle }}
    </p>
  </div>
</template>

<style scoped>
.nano-loop {
  margin: 1.5rem 0;
}

.nano-loop__list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.nano-loop__step {
  position: relative;
  background: var(--nano-surface);
  border: 1px solid var(--nano-border);
  border-top: 3px solid var(--nano-border);
  border-radius: var(--nano-radius);
  padding: 0.9rem 1rem 1rem;
}

.nano-loop__step[data-tone='observed'] { border-top-color: var(--nano-observed); }
.nano-loop__step[data-tone='primary'] { border-top-color: var(--nano-primary); }
.nano-loop__step[data-tone='uncertain'] { border-top-color: var(--nano-uncertain); }
.nano-loop__step[data-tone='gap'] { border-top-color: var(--nano-gap); }

.nano-loop__n {
  font-family: var(--nano-font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  color: var(--nano-text-dim);
}

.nano-loop__name {
  margin: 0.2rem 0 0.4rem;
  font-size: 1rem;
  line-height: 1.3;
  border: 0;
  padding: 0;
}

.nano-loop__text {
  margin: 0;
  font-size: 0.86rem;
  line-height: 1.5;
  color: var(--nano-text-dim);
}

.nano-loop__cycle {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin: 0.9rem 0 0;
  font-size: 0.85rem;
  color: var(--nano-text-dim);
}

@media (max-width: 900px) {
  .nano-loop__list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
  .nano-loop__list { grid-template-columns: minmax(0, 1fr); }
}
</style>
