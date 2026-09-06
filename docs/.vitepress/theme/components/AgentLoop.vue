<script setup lang="ts">
const steps = [
  {
    id: 'observe',
    n: '01',
    name: 'Observe',
    tone: 'observed',
    text: 'Read the sparse set of real measurements available so far, plus the simulation prior for every die.'
  },
  {
    id: 'estimate',
    n: '02',
    name: 'Estimate',
    tone: 'primary',
    text: 'Fit a spatial model of reality and produce three maps: prediction, uncertainty, and prior-vs-reality gap.'
  },
  {
    id: 'select',
    n: '03',
    name: 'Select',
    tone: 'uncertain',
    text: 'Score every unmeasured die with the acquisition function and pick the argmax as the next measurement.'
  },
  {
    id: 'measure',
    n: '04',
    name: 'Measure',
    tone: 'gap',
    text: 'Reveal the hidden real value at that die, append it to the observation set, and spend one unit of budget.'
  }
]
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
      Repeat until the measurement budget is exhausted. Every iteration is logged, so the decision
      trace is auditable.
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
